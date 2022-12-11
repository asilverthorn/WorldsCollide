from data.esper import Esper
from data.ability_data import AbilityData
from data.structures import DataArray

import data.espers_asm as espers_asm
import random
from memory.space import Reserve, Write, Bank
import instruction.asm as asm

class Espers():
    ESPER_COUNT = 27

    RAMUH, IFRIT, SHIVA, SIREN, TERRATO, SHOAT, MADUIN, BISMARK, STRAY, PALIDOR, TRITOCH, ODIN, RAIDEN, BAHAMUT, ALEXANDR,\
    CRUSADER, RAGNAROK, KIRIN, ZONESEEK, CARBUNKL, PHANTOM, SRAPHIM, GOLEM, UNICORN, FENRIR, STARLET, PHOENIX = range(ESPER_COUNT)

    esper_names = ["Ramuh", "Ifrit", "Shiva", "Siren", "Terrato", "Shoat", "Maduin", "Bismark", "Stray", "Palidor", "Tritoch",
                   "Odin", "Raiden", "Bahamut", "Alexandr", "Crusader", "Ragnarok", "Kirin", "ZoneSeek", "Carbunkl", "Phantom",
                   "Sraphim", "Golem", "Unicorn", "Fenrir", "Starlet", "Phoenix"]

    # order epsers appear in menu going left to right, top to bottom
    esper_menu_order = [0, 17, 3, 8, 1, 2, 23, 6, 5, 20, 19, 7, 22, 18, 21, 9, 24, 10, 4, 25, 14, 26, 11, 13, 16, 15, 12]

    SPELLS_BONUS_DATA_START = 0x186e00
    SPELLS_BONUS_DATA_END = 0x186fff
    SPELLS_BONUS_DATA_SIZE = 11

    NAMES_START = 0x26f6e1
    NAMES_END = 0x26f7b8
    NAME_SIZE = 8

    ABILITY_DATA_START = 0x046db4
    ABILITY_DATA_END = 0x046fd5

    SRAM_CHARACTER_ID = 0x1600 # Actor index in Save RAM

    def __init__(self, rom, args, spells, characters):
        self.rom = rom
        self.args = args
        self.spells = spells
        self.characters = characters

        self.spells_bonus_data = DataArray(self.rom, self.SPELLS_BONUS_DATA_START, self.SPELLS_BONUS_DATA_END, self.SPELLS_BONUS_DATA_SIZE)
        self.name_data = DataArray(self.rom, self.NAMES_START, self.NAMES_END, self.NAME_SIZE)
        self.ability_data = DataArray(self.rom, self.ABILITY_DATA_START, self.ABILITY_DATA_END, AbilityData.DATA_SIZE)

        self.espers = []
        for esper_index in range(len(self.name_data)):
            esper = Esper(esper_index, self.spells_bonus_data[esper_index], self.name_data[esper_index], self.ability_data[esper_index])
            self.espers.append(esper)

        self.available_espers = set(range(self.ESPER_COUNT))
        self.starting_espers = []

        if args.starting_espers_min > 0:
            count = random.randint(args.starting_espers_min, args.starting_espers_max)
            self.starting_espers = [self.get_random_esper() for _esp in range(count)]

    def receive_dialogs_mod(self, dialogs):
        self.receive_dialogs = [1133, 1380, 1381, 1134, 1535, 1082, 1091, 1092, 1136, 1534, 2618, 1093, 1087,\
                                2975, 2799, 1506, 1095, 1135, 2755, 1097, 1098, 1572, 2756, 1099, 2273, 2733, 1100]

        # replace some dialog with ramuh in zozo with missing received esper dialogs
        dialogs.set_text(self.receive_dialogs[self.SHOAT],      '<line>     Received the Magicite<line>              “Shoat.”<end>')
        dialogs.set_text(self.receive_dialogs[self.MADUIN],     '<line>     Received the Magicite<line>              “Maduin.”<end>')

        dialogs.set_text(self.receive_dialogs[self.BISMARK],    '<line>     Received the Magicite<line>              “Bismark.”<end>')
        dialogs.set_text(self.receive_dialogs[self.ODIN],       '<line>     Received the Magicite<line>              “Odin.”<end>')
        dialogs.set_text(self.receive_dialogs[self.RAIDEN],     '<line>     Received the Magicite<line>              “Raiden.”<end>')
        #dialogs.set_text(self.receive_dialogs[self.RAIDEN],     '<line>   The Magicite "Odin" gains<line>              a level…<page><line>   and becomes the Magicite<line>              "Raiden!"<end>')
        dialogs.set_text(self.receive_dialogs[self.RAGNAROK],   '<line>     Received the Magicite<line>              “Ragnarok.”<end>')
        dialogs.set_text(self.receive_dialogs[self.CARBUNKL],   '<line>     Received the Magicite<line>              “Carbunkl.”<end>')
        dialogs.set_text(self.receive_dialogs[self.PHANTOM],    '<line>     Received the Magicite<line>              “Phantom.”<end>')
        dialogs.set_text(self.receive_dialogs[self.UNICORN],    '<line>     Received the Magicite<line>              “Unicorn.”<end>')
        dialogs.set_text(self.receive_dialogs[self.PHOENIX],    '<line>     Received the Magicite<line>              “Phoenix.”<end>')

        # remove phunbaba part of received fenrir dialog
        dialogs.set_text(self.receive_dialogs[self.FENRIR],     '<line>     Received the Magicite<line>              “Fenrir.”<end>')

    def shuffle_spells(self):
        # to prevent duplicates, get list of spells and sort it by their frequency
        # the sort prevents ending up with more than one of the same spell and only one esper left to give them to
        # randomly pick espers until find one without the spell and add it
        # once the esper has as many spells as it originally did remove it from available pool
        import copy
        spells = []
        for esper in self.espers:
            for spell_index in range(Esper.SPELL_COUNT):
                if esper.spells[spell_index].id != Esper.NO_SPELL:
                    spells.append(copy.deepcopy(esper.spells[spell_index]))

        # sort spells based on their frequency (the key is the spell id), most frequent last so they are popped first
        # NOTE: this does not also sort by spell id as a secondary key so resulting spells will not be in
        #       any order except the frequency of spell ids
        import collections
        frequencies = collections.Counter(spell.id for spell in spells)
        spells = sorted(spells, key = lambda spell: frequencies[spell.id])

        # get spell counts and pool of available espers and clear the spells they have now
        spell_counts = []
        esper_indices = []
        for esper_index, esper in enumerate(self.espers):
            spell_counts.append(esper.spell_count)
            esper.clear_spells()
            esper_indices.append(esper_index)

        random.shuffle(spell_counts)

        while len(spells) > 0:
            esper_index = random.choice(esper_indices)
            esper = self.espers[esper_index]
            if not esper.has_spell(spells[-1].id):
                spell = spells.pop()
                if self.args.esper_spells_shuffle_random_rates:
                    esper.add_spell(spell.id, random.choice(Esper.LEARN_RATES))
                else:
                    esper.add_spell(spell.id, spell.rate)
                if esper.spell_count == spell_counts[esper_index]:
                    esper_indices.remove(esper_index)

    def randomize_spells(self):
        for esper in self.espers:
            esper.clear_spells()
            num_spells = random.randint(self.args.esper_spells_random_min, self.args.esper_spells_random_max)
            spells = self.spells.get_random(count = num_spells)
            for spell_id in spells:
                esper.add_spell(spell_id, random.choice(Esper.LEARN_RATES))

    def randomize_spells_tiered(self):
        def get_spell():
            from data.esper_spell_tiers import tiers, weights, tier_s_distribution
            from utils.weighted_random import weighted_random

            random_tier = weighted_random(weights)
            if random_tier < len(weights) - 1: # not s tier, use equal distribution
                random_tier_index = random.randrange(len(tiers[random_tier]))
                return tiers[random_tier][random_tier_index]

            weights = [entry[1] for entry in tier_s_distribution]
            random_s_index = weighted_random(weights)
            return tier_s_distribution[random_s_index][0]

        for esper in self.espers:
            esper.clear_spells()
            num_spells = random.randint(1, Esper.SPELL_COUNT)
            for spell_index in range(num_spells):
                learn_rate_index = int(random.triangular(0, len(Esper.LEARN_RATES), 0))
                if learn_rate_index == len(Esper.LEARN_RATES):
                    # triangular max is inclusive, very small chance need to round max down
                    learn_rate_index -= 1
                learn_rate = Esper.LEARN_RATES[learn_rate_index]
                esper.add_spell(get_spell(), learn_rate)

    def remove_flagged_learnables(self):
        for a_spell_id in self.args.remove_learnable_spell_ids:
            for esper in self.espers:
                if(esper.has_spell(a_spell_id)):
                    esper.remove_spell(a_spell_id)

    def replace_flagged_learnables(self):
        for esper in self.espers:
            for a_spell_id in self.args.remove_learnable_spell_ids:
                if(esper.has_spell(a_spell_id)):
                    # Also exclude spells this Esper already knows, to avoid duplicates
                    exclude_spell_ids = self.args.remove_learnable_spell_ids.copy()
                    exclude_spell_ids.extend(esper.get_spell_ids())

                    new_spell_id = self.spells.get_replacement(a_spell_id, exclude = exclude_spell_ids)
                    esper.replace_spell(a_spell_id, new_spell_id)


    def clear_spells(self):
        for esper in self.espers:
            esper.clear_spells()

    def randomize_rates(self):
        for esper in self.espers:
            esper.randomize_rates()

    def shuffle_bonuses(self):
        bonuses = []
        for esper in self.espers:
            bonuses.append(esper.bonus)

        random.shuffle(bonuses)
        for esper in self.espers:
            esper.set_bonus(bonuses.pop())

    def randomize_bonuses(self):
        bonus_percent = self.args.esper_bonuses_random_percent / 100.0
        for esper in self.espers:
            if random.random() < bonus_percent:
                esper.randomize_bonus()
            else:
                esper.set_bonus(Esper.NO_BONUS)

    def shuffle_mp(self):
        mp = []
        for esper in self.espers:
            mp.append(esper.mp)

        random.shuffle(mp)
        for esper in self.espers:
            esper.mp = mp.pop()

    def random_mp_value(self):
        for esper in self.espers:
            esper.mp = random.randint(self.args.esper_mp_random_value_min, self.args.esper_mp_random_value_max)

    def random_mp_percent(self):
        for esper in self.espers:
            mp_percent = random.randint(self.args.esper_mp_random_percent_min,
                                        self.args.esper_mp_random_percent_max) / 100.0
            value = int(esper.mp * mp_percent)
            esper.mp = max(min(value, 254), 1)

    def equipable_random(self):
        from data.characters import Characters
        possible_characters = list(range(Characters.CHARACTER_COUNT - 2)) # exclude gogo/umaro

        for esper in self.espers:
            esper.equipable_characters = 0 # set equipable by no characters
            number_characters = random.randint(self.args.esper_equipable_random_min, self.args.esper_equipable_random_max)
            random_characters = random.sample(possible_characters, number_characters)
            for character in random_characters:
                esper.equipable_characters |= (1 << character)

    def equipable_balanced_random(self):
        # assign each esper exactly characters_per_esper unique characters
        # the total number of espers each character can equip should also be balanced
        # e.g. given 27 espers and 3 characters_per_esper:
        #      27 * 3 = 81 total equipable slots to assign, the 3 characters should be unique for each esper
        #      81 // 12 = 6, each character can equip 6 different espers
        #      81 % 12 = 9, 9 characters can equip 1 additional esper (7 total for those 9)

        from data.characters import Characters
        possible_characters = list(range(Characters.CHARACTER_COUNT - 2)) # exclude gogo/umaro
        characters_per_esper = self.args.esper_equipable_balanced_random_value

        for esper in self.espers:
            esper.equipable_characters = 0 # set equipable by no characters
            if len(possible_characters) < characters_per_esper:
                # fewer possibilities left than number of characters needed for each esper
                character_group = possible_characters # add remaining possible characters to current group
                possible_characters = list(range(Characters.CHARACTER_COUNT - 2)) # add characters back into pool

                # select characters at random from possible pool until
                # character_group contains characters_per_esper unique characters
                while len(character_group) < characters_per_esper:
                    candidate = random.choice(possible_characters)
                    if candidate not in character_group:
                        character_group.append(candidate)
                        possible_characters.remove(candidate)

                # assign character group to current esper
                for character in character_group:
                    esper.equipable_characters |= (1 << character)
            else:
                character_group = random.sample(possible_characters, characters_per_esper)
                for character in character_group:
                    possible_characters.remove(character)
                    esper.equipable_characters |= (1 << character)

    def phoenix_life3(self):
        # change phoenix behavior to cast life 3 on party instead of life
        self.espers[self.PHOENIX].flags1 = 0
        self.espers[self.PHOENIX].flags3 = 0x20
        self.espers[self.PHOENIX].power = 0
        self.espers[self.PHOENIX].status1 = 0
        self.espers[self.PHOENIX].status4 = 0x04

    def multi_summon(self):
        space = Reserve(0x24da3, 0x24da5, "espers set used in battle bit", asm.NOP())

    def _get_def_mdef_logic(self, sram_addr, label):
        ''' get common assembly logic for mdef/def bonuses '''
        return [
            # we will do similar to how strength, magic, speed, and stamina get added for defense and magic defense
            asm.LDA(self.SRAM_CHARACTER_ID,asm.ABS_Y),
            asm.ASL(),
            asm.ASL(),  # *4 because each character has four stats to boost here
            asm.TAY(),
            asm.TXA(),
            asm.LSR(),
            asm.LSR(), # if the low bit was set, we're only doing +1
            asm.LDA(sram_addr,asm.ABS_Y),  #load defense bonus
            asm.INC(),
            asm.BCS(f"{label}_plus_1"),
            asm.INC(),
            f"{label}_plus_1",
            asm.STA(sram_addr,asm.ABS_Y),  # at no point can defense ever get to 255 through leveling, so no need to check for wrapping
            asm.RTL(),
        ]
        
    def more_level_up_bonuses(self):
        import data.text as text
# Testing with py wc.py -i ../rom/ff3.sfc -stesp 20 20 -ebr 100 -xpm 99 -sc1 terra -sc2 locke -sc3 edgar -sc4 cyan
#Problem 11/6: display of evade is wrong on Terra
        # Lenophis' additional level up bonus options:
        # Defense +1
        # Defense +2
        # Magic Defense +1
        # Magic Defense +2
        # Evade +1
        # Magic Evade +1

        # Using $1CF8-$1D27 Sword tech names (from FF6j) SRAM space to store the bonus values for each character.
        # Zero out the SwdTech names set in SRAM init.
        space = Reserve(0x0bde2, 0x0bdf0, "swdtech name SRAM init", asm.NOP())

        # New Bonus storage in SRAM
        SRAM_EVADE_BONUS = 0x1cf8
        SRAM_MEVADE_BONUS = 0x1cf9
        SRAM_DEF_BONUS = 0x1cfa
        SRAM_MDEF_BONUS = 0x1cfb
        # Character stat locations in SRAM
        SRAM_CHAR_DEF = 0x11ba
        SRAM_CHAR_MDEF = 0x11bb
        SRAM_CHAR_EVADE = 0x11a8
        SRAM_CHAR_MEVADE = 0x11aa
        # Add logic for applying stat boosts
        # Evade/MEvade
        src = [
            # ; coming in, X is 0x0E or 0x10 due to *2 from indexing
            # ; Y holds current character index from $1600
            # ; X and Y can be trashed as needed, since PLX and PLY follow this routine
            # ; we need to get character ID so we can properly access our evade bonuses
            # ; fortunately, we don't need to worry about a Gogo or Umaro check here, because they've already been accounted for
            asm.LDA(self.SRAM_CHARACTER_ID,asm.ABS_Y),  # get our ID
            asm.ASL(),
            asm.ASL(), # *4 because each character has four stats to boost here
            asm.TAY(),
            asm.CPX(0x0010, asm.IMM16),
            asm.BCC("not_m_evade"),  # if carry is set, X is #$10 so we would do magic evade instead
            asm.INY(),  # add one to Y to point at magic evade instead
            "not_m_evade",
            asm.LDA(SRAM_EVADE_BONUS,asm.ABS_Y),  # now we load up our evade boost from before
            asm.INC(),
            asm.CMP(0x81, asm.IMM8),  # is it at 129? cap if so. evade soft caps at 128 because nothing can touch you at that point anyway
            asm.BCC("evade_max"),
            asm.LDA(0x80, asm.IMM8),
            "evade_max",
            asm.STA(SRAM_EVADE_BONUS,asm.ABS_Y),
            asm.RTL(),
        ]
        space = Write(Bank.F0, src, "Evade/MEvade level up Bonus")
        evade_bonus_address_snes = space.start_address_snes

        src = self._get_def_mdef_logic(SRAM_DEF_BONUS, "def")
        space = Write(Bank.F0, src, "Defense level up bonus")
        def_bonus_address_snes = space.start_address_snes

        src = self._get_def_mdef_logic(SRAM_MDEF_BONUS, "mdef")
        space = Write(Bank.F0, src, "Magic Defense level up bonus")
        magic_def_bonus_address_snes = space.start_address_snes

        # Now, the logic to apply the bonuses...
        # character index is now 5 bytes into the stack at this point
        # coming in, X is our indexed character info block at $ED7CAA
        # Y is "derefenced" at this point. it is pushed to the stack from equipment check, but still holds whatever coming in. it can be used as scratch
        # we hooked the LDA directly, so this should be easy enough
        # coming in, M is clear so accumulator is 16-bit
        src = [
            asm.LDA(0xED7CAB,asm.LNG_X),  # defense and magic defense
            asm.STA(SRAM_CHAR_DEF, asm.ABS),  # save both for now
            asm.LDA(0x04,asm.S),  # load our character index again
            asm.TAY(),
            asm.TDC(),
            asm.A8(),
            asm.LDA(0x15DB,asm.ABS_Y),  # starts at $1600, but equipment check has its indexing set at weird points
            asm.CMP(0x0C, asm.IMM8),  # is it Gogo, Umaro, or someone higher?
            asm.BCS("get_out"),  # branch if so, they can't get boosted
            asm.ASL(),
            asm.ASL(),
            asm.TAY(),
            asm.LDA(SRAM_DEF_BONUS,asm.ABS_Y),  # load our boosted defense
            asm.CLC(),
            asm.ADC(SRAM_CHAR_DEF, asm.ABS),
            asm.BCC("def_no_wrap"),
            asm.LDA(0xFF, asm.IMM8),
            "def_no_wrap",
            asm.STA(SRAM_CHAR_DEF, asm.ABS),
            asm.LDA(SRAM_MDEF_BONUS,asm.ABS_Y),  # load our boosted magic defense
            asm.CLC(),
            asm.ADC(SRAM_CHAR_MDEF, asm.ABS),
            asm.BCC("m_def_no_wrap"),
            asm.LDA(0xFF, asm.IMM8),
            "m_def_no_wrap",
            asm.STA(SRAM_CHAR_MDEF, asm.ABS),
            # Add Evade Bonus
            asm.A16(),
            asm.LDA(0xED7CAD,asm.LNG_X),
            asm.A8(),  # sets M to 8 bit
            asm.STA(SRAM_CHAR_EVADE, asm.ABS),  # save evade for now
            asm.XBA(),
            asm.STA(SRAM_CHAR_MEVADE, asm.ABS),  # save magic evade for now
            asm.LDA(SRAM_EVADE_BONUS,asm.ABS_Y), # load our boosted evade
            asm.CLC(),
            asm.ADC(SRAM_CHAR_EVADE, asm.ABS),  # add in our evade from equipment
            asm.CMP(0x81, asm.IMM8),  # is it at 129? cap if so. evade soft caps at 128 because nothing can touch you at that point anyway
            asm.BCC("evade_good"),
            asm.LDA(0x80, asm.IMM8),
            "evade_good",
            asm.STA(SRAM_CHAR_EVADE, asm.ABS),
            asm.LDA(SRAM_MEVADE_BONUS,asm.ABS_Y),
            asm.CLC(),
            asm.ADC(SRAM_CHAR_MEVADE, asm.ABS),  # add in our magic evade from equipment
            asm.CMP(0x81, asm.IMM8),  # is it at 129? cap if so. magic evade soft caps at 128 because nothing can touch you at that point anyway
            asm.BCC("m_evade_good"),
            asm.LDA(0x80, asm.IMM8),
            "m_evade_good",
            asm.RTL(),
            "get_out",
            # if we're here, our character is Gogo, Umaro, or someone higher. That means they can't get boosted stats.
            asm.A16(),
            asm.LDA(0xED7CAD,asm.LNG_X),  # so let's load our evade and magic evade like we normally would
            asm.A8(),
            asm.STA(SRAM_CHAR_EVADE, asm.ABS),  # save evade
            asm.XBA(),
            asm.RTL(),  # and exit out for magic evade
        ]
        space = Write(Bank.F0, src, "Apply Level Up Bonuses")
        apply_bonus_address_snes = space.start_address_snes

        # Now, add the JSLs to our new code

        # we are in the middle of the "Equipment check" function.
        # at this point, 16-bit A holds evade and magic evade pulled from the character data at $ED7CAD indexed
        # to clarify, the lower 8 bits hold evade, and the upper 8 bits hold magic evade
        # the first two bytes on the stack hold our character index
        # since defense, magic defense, evade, and magic evade are all back-to-back, let's just condense the bonus adding into one call and pad out the rest with NOP's
        # following this is STA $11AA, we'll obviously keep it so we don't need extra code
        space = Reserve(0x20eae, 0x20ebf, "Equipment check function", asm.NOP())
        space.write(
            asm.JSL(apply_bonus_address_snes),
        )

        # original location for the esper bonuses in vanilla
        # now will be used for some JSL calls into C0 to handle the levelup bonuses
        space = Reserve(0x2614e, 0x26153, "Level up bonus jump table - repurposed", asm.NOP())
        space.write(
            asm.JSL(evade_bonus_address_snes),
            asm.RTS(),
        )
        evade_m_evade_addr = space.start_address

        space = Reserve(0x26154, 0x26159, "Level up bonus jump table - repurposed", asm.NOP())
        space.write(
            asm.JSL(def_bonus_address_snes),
            asm.RTS(),
        )
        def_addr = space.start_address

        space = Reserve(0x2615a, 0x2615f, "Level up bonus jump table - repurposed", asm.NOP())
        space.write(
            asm.JSL(magic_def_bonus_address_snes),
            asm.RTS(),
        )
        m_def_addr = space.start_address

        # jump addresses for applying bonuses
        bonus_addresses = [
            0x6170, # vanilla - HP + 10%
            0x6174, # vanilla - HP + 30%
            0x6178, # vanilla - HP + 50%
            0x6170, # vanilla - HP + 10%
            0x6174, # vanilla - MP + 30%
            0x6178, # vanilla - MP + 50%
            0x61B0, # vanilla - HP + 100%
            evade_m_evade_addr, # repurposed - Evade + 1
            evade_m_evade_addr, # repurposed - Magic Evade + 1
            0x619B, # vanilla - Str + 1
            0x619B, # vanilla - Str + 2
            0x619A, # vanilla - Speed + 1
            0x619A, # vanilla - Speed + 2
            0x6199, # vanilla - Stamina + 1
            0x6199, # vanilla - Stamina + 2
            0x6198, # vanilla - Magic + 1
            0x6198, # vanilla - Magic + 2
            # adding 4 new bonuses
            def_addr, # Defense + 1
            def_addr, # Defense + 2
            m_def_addr, # Magic Defense + 1
            m_def_addr, # Magic Defense + 2
        ]

        #Now, flip them to little endian and write them into C2
        src = []
        for addr in bonus_addresses:
            src.append((addr & 0xffff).to_bytes(2, 'little'))
        space = Write(Bank.C2, src, "rage description lines table offsets")
        bonuses_jump_table_addr = space.start_address

        space = Reserve(0x260f1, 0x260f3, "calculate bonus jump", asm.NOP())
        space.write(
            asm.JSR(bonuses_jump_table_addr, asm.ABS_X_16),
        )

        # Add new descriptions for the menu
        bonus_descriptions = [
            "HP gained +10%",
            "HP gained +30%",
            "HP gained +50%",
            "MP gained +10%",
            "MP gained +30%",
            "MP gained +50%",
            "HP gained doubled",
            "Evade increases by 1",
            "Magic Evade increases by 1",
            "Vigor increases by 1",
            "Vigor increases by 2",
            "Speed increases by 1",
            "Speed increases by 2",
            "Stamina increases by 1",
            "Stamina increases by 2",
            "Magic increases by 1",
            "Magic increases by 2",
            "Defense increases by 1",
            "Defense increases by 2",
            "Magic Defense increases by 1",
            "Magic Defense increases by 2",
        ]

        line_offsets = [0]
        running_offset = 0
        # Overwrite the descriptions in ED. Using some free space
        description_bytes = [] # the descriptions
        for line in bonus_descriptions:
            # convert to bytes
            bytes = text.get_bytes(line, text.TEXT3)
            bytes.append(0x00) # Code expects these strings to be null terminated
            running_offset += len(bytes)
            line_offsets.append(running_offset)
            description_bytes.append(bytes)

        # Write the descriptions
        space = Reserve(0x2dfd2c, 0x2dffd0, "esper bonus descriptions")
        space.write(description_bytes)
        desc_table = space.start_address

        # Then, write the offsets
        # Each offset is an absolute, so use the 16-bit location of the descriptions
        desc_table_offset = desc_table & 0xffff
        src = []
        for offset in line_offsets:
            src.append((desc_table_offset + offset).to_bytes(2, 'little'))
        space = Reserve(0x2dfd00, 0x2dfd2b, "esper bonus description pointers")
        space.write(src)
        esper_long_ptr = space.start_address

        space = Reserve(0x35bf6, 0x35c08, "esper level up bonus menu")
        # a little bit of optimization and also makes the pointers absolute instead of relative
        space.write(
            asm.LDX((esper_long_ptr & 0xffff), asm.IMM16),
            asm.STX(0xE7, asm.DIR),
            asm.LDX(0x00, asm.DIR),
            asm.STX(0xEB, asm.DIR),
            asm.LDA(0xED, asm.IMM8),
            asm.STA(0xE9, asm.DIR),
            asm.STA(0xED, asm.DIR),
            asm.RTS(),
        )

        # Esper display
        # org $CFFEED
        # ; there's only two short bonus descriptions to change here
        # ; we have 9 letters to work with per description
        # DB "Evade + 1"
        # DB "M",$C5,"Ev",$C5," + 1"
        space = Reserve(0xffeed + 0, 0xffeed + 8, "Evade desc")
        space.write(text.get_bytes("Evade + 1", text.TEXT3))
        space = Reserve(0xffeed + 9, 0xffeed + 17, "MEv desc")
        space.write(text.get_bytes("M.Ev. + 1", text.TEXT3))

        # org $CFFF47
        # ; now add in the defense and magic defense short bonus descriptors
        # DB "Def",$C5," + 1 "
        # DB "Def",$C5," + 2 "
        # DB "MDef",$C5," + 1"
        # DB "MDef",$C5," + 2"
        # ; and we're done!
        space = Reserve(0xfff47 + 0, 0xfff47 + 8, "def+1 desc")
        space.write(text.get_bytes("Def. + 1", text.TEXT3))
        space = Reserve(0xfff47 + 9, 0xfff47 + 17, "def+2 desc")
        space.write(text.get_bytes("Def. + 2", text.TEXT3))
        space = Reserve(0xfff47 + 18, 0xfff47 + 26, "mdef+1 desc")
        space.write(text.get_bytes("MDef. + 1", text.TEXT3))
        space = Reserve(0xfff47 + 27, 0xfff47 + 35, "mdef+2 desc")
        space.write(text.get_bytes("MDef. + 2", text.TEXT3))


    def mod(self, dialogs):
        self.receive_dialogs_mod(dialogs)

        if self.args.esper_spells_random_rates or self.args.esper_spells_shuffle_random_rates:
            self.randomize_rates()

        if len(self.starting_espers):
            self.randomize_rates()

        if self.args.esper_spells_shuffle or self.args.esper_spells_shuffle_random_rates:
            self.shuffle_spells()
        elif self.args.esper_spells_random:
            self.randomize_spells()
        elif self.args.esper_spells_random_tiered:
            self.randomize_spells_tiered()

        if self.args.esper_bonuses_shuffle:
            self.shuffle_bonuses()
        elif self.args.esper_bonuses_random:
            self.randomize_bonuses()

        if self.args.esper_mp_shuffle:
            self.shuffle_mp()
        elif self.args.esper_mp_random_value:
            self.random_mp_value()
        elif self.args.esper_mp_random_percent:
            self.random_mp_percent()

        if self.args.esper_equipable_random:
            self.equipable_random()
        elif self.args.esper_equipable_balanced_random:
            self.equipable_balanced_random()
        espers_asm.equipable_mod(self)

        if self.args.permadeath:
            self.phoenix_life3()

        if self.args.esper_spells_random or self.args.esper_spells_random_tiered:
            # if random, replace the spells
            self.replace_flagged_learnables()
        else:
            # otherwise (original or shuffled), remove them
            self.remove_flagged_learnables()

        if self.args.esper_multi_summon:
            self.multi_summon()

        self.more_level_up_bonuses()

    def write(self):
        if self.args.spoiler_log:
            self.log()

        for esper_index in range(len(self.espers)):
            self.spells_bonus_data[esper_index] = self.espers[esper_index].spells_bonus_data()
            self.name_data[esper_index] = self.espers[esper_index].name_data()
            self.ability_data[esper_index] = self.espers[esper_index].ability_data()

        self.spells_bonus_data.write()
        self.name_data.write()
        self.ability_data.write()

    def available(self):
        return len(self.available_espers)

    def get_random_esper(self):
        if not self.available_espers:
            return None

        rand_esper = random.sample(self.available_espers, 1)[0]
        self.available_espers.remove(rand_esper)
        return rand_esper

    def get_receive_esper_dialog(self, esper):
        return self.receive_dialogs[esper]

    def get_name(self, esper):
        return self.esper_names[esper]

    def log(self):
        from log import COLUMN_WIDTH, section_entries, format_option
        from textwrap import wrap

        lentries = []
        rentries = []
        for entry_index in range(self.ESPER_COUNT):
            esper_index = self.esper_menu_order[entry_index]
            esper = self.espers[esper_index]
            prefix = "*" if esper.id in self.starting_espers else ""

            entry = [f"{prefix}{esper.get_name():<{self.NAME_SIZE}}  {esper.mp:>3} MP"]

            for spell_index in range(esper.spell_count):
                spell_name = self.spells.get_name(esper.spells[spell_index].id)
                learn_rate = esper.spells[spell_index].rate
                entry.append(format_option("{:<7} x{}".format(spell_name, str(learn_rate)), ""))

            bonus_string = esper.get_bonus_string()
            if bonus_string:
                entry.append(bonus_string)

            no_gogo_umaro_bits = 0xfff # bitmask for all characters except gogo/umaro
            if (esper.equipable_characters & no_gogo_umaro_bits) == no_gogo_umaro_bits:
                entry.append("Equipable: All")
            elif esper.equipable_characters == 0:
                entry.append("Equipable: None")
            else:
                character_names = []
                characters = esper.get_equipable_characters()
                for character in characters:
                    character_names.append(self.characters.get_name(character))

                character_names = "Equipable: " + ' '.join(character_names)
                character_names = wrap(character_names, width = COLUMN_WIDTH - 1)
                entry.append(character_names)

            if entry_index % 2:
                rentries.append(entry)
            else:
                lentries.append(entry)

        lentries.append("")
        lentries.append("* = Starting Esper")

        section_entries("Espers", lentries, rentries)

    def print(self):
        for esper in self.espers:
            esper.print(self.spells)
