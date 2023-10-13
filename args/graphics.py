from data.character_sprites import PORTRAIT_CHARACTERS, SPRITE_CHARACTERS, DEFAULT_CHARACTER_PORTRAITS, DEFAULT_CHARACTER_SPRITES
from data.character_palettes import SPRITE_PALETTE_COUNT, DEFAULT_CHARACTER_PALETTES, DEFAULT_CHARACTER_SPRITE_PALETTES
from data.characters import Characters
from PIL import ImageColor

def parse(parser):
    graphics = parser.add_argument_group("Graphics")
    graphics.add_argument("-name", "--character-names", type = str, help = "Character names")
    graphics.add_argument("-cpal", "--character-palettes", type = str, help = "Character palette indices")
    graphics.add_argument("-cpor", "--character-portraits", type = str, help = "Character portrait indices")
    graphics.add_argument("-cspr", "--character-sprites", type = str, help = "Character sprite indices")
    graphics.add_argument("-cspp", "--character-sprite-palettes", type = str, help = "Character sprite palette indices")

    remove_flashes = graphics.add_mutually_exclusive_group()
    remove_flashes.add_argument("-frw", "--flashes-remove-worst", action = "store_true",
                              help = "Removes only the worst flashes from animations. Ex: Learning Bum Rush, Bum Rush, Quadra Slam/Slice, Flash, etc.")
    remove_flashes.add_argument("-frm", "--flashes-remove-most", action = "store_true",
                              help = "Removes most flashes from animations. Includes Kefka Death.")

    graphics.add_argument("-wmhc", "--world-minimap-high-contrast", action = "store_true",
                              help = "World Minimap made Opaque with Minimap icon changed to higher contrast to improve visibility.")

    graphics.add_argument("-ahtc", "--alternate-healing-text-color", action = "store_true",
                              help = "Makes healing text blue, to be able to distinguish from damage.")
    
    graphics.add_argument("-atma", "--atma-color", type = str,
                            help = "Customize the color of the Atma Weapon.")

def process(args):
    import graphics.palettes.palettes as palettes
    import graphics.portraits.portraits as portraits
    import graphics.sprites.sprites as sprites

    if args.character_names is not None:
        args.names = args.character_names.split('.')
        if len(args.names) != Characters.CHARACTER_COUNT:
            raise ValueError(f"Invalid number of name arguments ({len(args.names)} should be {Characters.CHARACTER_COUNT})")

        for index in range(len(args.names)):
            if args.names[index]:
                args.names[index] = args.names[index][ : Characters.NAME_SIZE]
            else:
                args.names[index] = Characters.DEFAULT_NAME[index]
    else:
        args.names = Characters.DEFAULT_NAME

    args.palettes = []
    if args.character_palettes:
        args.palette_ids = [int(palette_id) for palette_id in args.character_palettes.split('.')]
        if SPRITE_PALETTE_COUNT != len(args.palette_ids):
            raise ValueError(f"Invalid number of palette arguments ({len(args.palette_ids)} should be {SPRITE_PALETTE_COUNT})")
    else:
        args.palette_ids = DEFAULT_CHARACTER_PALETTES

    args.palette_files = []
    for palette_id in args.palette_ids:
        args.palettes.append(palettes.id_palette[palette_id])
        args.palette_files.append(palettes.get_path(palette_id))

    args.portraits = []
    if args.character_portraits:
        import os

        args.portrait_ids = [int(portrait_id) for portrait_id in args.character_portraits.split('.')]
        if len(PORTRAIT_CHARACTERS) != len(args.portrait_ids):
            raise ValueError(f"Invalid number of portrait arguments ({len(args.portrait_ids)} should be {len(PORTRAIT_CHARACTERS)})")

        args.portrait_sprite_files = []
        args.portrait_palette_files = []
        for portrait_id in args.portrait_ids:
            args.portraits.append(portraits.id_portrait[portrait_id])

            portrait_sprite_file = portraits.get_bin_path(portrait_id)  # returns path to portrait sprite bin
            portrait_palette_file = portraits.get_pal_path(portrait_id) # convert to path to portrait palette pal

            args.portrait_sprite_files.append(portrait_sprite_file)
            args.portrait_palette_files.append(portrait_palette_file)
    else:
        for portrait_id in DEFAULT_CHARACTER_PORTRAITS:
            args.portraits.append(portraits.id_portrait[portrait_id])

    args.sprites = []
    if args.character_sprites:
        args.sprite_ids = [int(sprite_id) for sprite_id in args.character_sprites.split('.')]
        if len(SPRITE_CHARACTERS) != len(args.sprite_ids):
            raise ValueError(f"Invalid number of sprite arguments ({len(args.sprite_ids)} should be {len(SPRITE_CHARACTERS)})")

        args.sprite_files = []
        for sprite_id in args.sprite_ids:
            args.sprites.append(sprites.id_sprite[sprite_id])
            args.sprite_files.append(sprites.get_path(sprite_id))
    else:
        for sprite_id in DEFAULT_CHARACTER_SPRITES:
            args.sprites.append(sprites.id_sprite[sprite_id])

    if args.character_sprite_palettes:
        args.sprite_palettes = [int(index) for index in args.character_sprite_palettes.split('.')]
        if len(SPRITE_CHARACTERS) != len(args.sprite_palettes):
            raise ValueError(f"Invalid number of sprite palette arguments ({len(args.sprite_palettes)} should be {len(SPRITE_CHARACTERS)})")
    else:
        args.sprite_palettes = DEFAULT_CHARACTER_SPRITE_PALETTES

    args.atma_colors_rgb = None
    if args.atma_color:
        # Populate the args.atma_colors_rgb with the specified 3 or 4 colors. This argument goes in order from outside into the middle white.
        # first check for presets -- these will override the value for the hex color parsing below
        atma_color = args.atma_color.lower().strip()
        if atma_color == 'blue':
            args.atma_color = None # just put back to default
        elif atma_color == 'purple':
            atma_color = "#29005b.#7903c2.#c269fd"
        elif atma_color == 'red':
            atma_color = "#7a0d07.#fc1b0f.#f96b63"
        elif atma_color == 'orange':
            atma_color = "#9e530e.#e27814.#e2a061"
        elif atma_color == 'yellow':
            atma_color = "#9e8300.#ffd800.#ffe97c"
        elif atma_color == 'green':
            atma_color = "#004406.#007f0e.#39a340"
        elif atma_color == 'dark':
            atma_color = '#cccccc.#707070.#3F3F3F.#000000'
        elif atma_color == 'white':
            atma_color = '#444444.#b7b7b7.#cecece'

    # Now, check for the hex strings (either set above via presets or by the user for a custom color)
    if args.atma_color:
        # Ensure there are 3 or 4, '.' separated
        atma_colors_hex = atma_color.split('.')
        if(len(atma_colors_hex) != 3 and len(atma_colors_hex) != 4):
            raise ValueError(f"Invalid number of atma color arguments ({len(atma_colors_hex)}) should be 3 or 4")
        
        # parse the 3 or 4 colors into args.atma_colors_rgb. By using PIL, we're supporting a variety of color specifications, including hex or words ("red")
        args.atma_colors_rgb = []
        for hex_atma in atma_colors_hex:
            args.atma_colors_rgb.append(ImageColor.getcolor(hex_atma, "RGB"))
        

def flags(args):
    flags = ""

    if args.character_names:
        flags += " -name " + args.character_names
    if args.character_palettes:
        flags += " -cpal " + args.character_palettes
    if args.character_portraits:
        flags += " -cpor " + args.character_portraits
    if args.character_sprites:
        flags += " -cspr " + args.character_sprites
    if args.character_sprite_palettes:
        flags += " -cspp " + args.character_sprite_palettes

    if args.flashes_remove_worst:
        flags += " -frw"
    if args.flashes_remove_most:
        flags += " -frm"
    if args.world_minimap_high_contrast:
        flags += " -wmhc"
    if args.alternate_healing_text_color:
        flags += " -ahtc"
    if args.atma_color:
        flags += " -atma " + args.atma_color

    return flags

def _truncated_name(name):
    MAX_LENGTH = 29 # if name is too long for column, truncate and add ...
    if len(name) > MAX_LENGTH:
        return name[ : (MAX_LENGTH - 3)] + "..."
    return name

def _sprite_palettes_log(args):
    from log import format_option
    log = ["Sprite Palettes"]

    for index, palette, in enumerate(args.palettes):
        log.append(format_option(f"Palette {index}", _truncated_name(palette), f"palette_{index}"))

    return log

def _other_portraits_sprites_log(args):
    from log import format_option
    log = ["Other Portraits & Sprites"]

    sprite_index = Characters.CHARACTER_COUNT
    portrait_index = Characters.CHARACTER_COUNT
    other_names = ["Soldier", "Imp", "General Leo", "Banon", "Esper Terra", "Merchant", "Ghost", "Kefka"]
    for character in range(Characters.CHARACTER_COUNT, Characters.CHARACTER_COUNT + len(other_names)):
        name = other_names[character - Characters.CHARACTER_COUNT]

        if character in PORTRAIT_CHARACTERS:
            log.append(format_option(name, _truncated_name(args.portraits[portrait_index]), f"portraits_{portrait_index}"))
            portrait_index += 1
            name = "" # do not have name show up in front of sprite also
        if character in SPRITE_CHARACTERS:
            log.append(format_option(name, _truncated_name(args.sprites[sprite_index]), f"sprite_{sprite_index}"))
            log.append(format_option("", f"Palette {args.sprite_palettes[sprite_index]}", f"palette_{sprite_index}"))
            sprite_index += 1

    return log

def _character_customization_log(args):
    from log import format_option
    log = ["Character Customization"]

    for index in range(Characters.CHARACTER_COUNT):
        log_name = f"{Characters.DEFAULT_NAME[index]:<6} -> {args.names[index]}"
        log.append(format_option(log_name, _truncated_name(args.portraits[index]), f"char_name_{index}"))
        log.append(format_option("", _truncated_name(args.sprites[index]), f"char_sprite_{index}"))
        log.append(format_option("", f"Palette {args.sprite_palettes[index]}", f"char_palette_{index}"))

    return log

def _other_options_log(args):
    from log import format_option
    log = ["Other Graphics"]

    remove_flashes = "Original"
    if args.flashes_remove_worst:
        remove_flashes = "Worst"
    elif args.flashes_remove_most:
        remove_flashes = "Most"

    world_minimap = "Original"
    if args.world_minimap_high_contrast:
        world_minimap = "High Contrast"

    healing_text = "Original"
    if args.alternate_healing_text_color:
        healing_text = "Blue"

    entries = [
        ("Remove Flashes", remove_flashes, "remove_flashes"),
        ("World Minimap", world_minimap, "world_minimap"),
        ("Healing Text", healing_text, "healing_text"),
    ]

    for entry in entries:
        log.append(format_option(*entry))

    return log

def log(args):
    lcolumn = [""]
    lcolumn.extend(_sprite_palettes_log(args))

    lcolumn.append("")
    lcolumn.extend(_other_portraits_sprites_log(args))

    lcolumn.append("")
    lcolumn.extend(_other_options_log(args))

    rcolumn = [""]
    rcolumn.extend(_character_customization_log(args))

    from log import section
    section("Graphics", lcolumn, rcolumn)
