import re
from pathlib import Path
from typing import Dict, List, Tuple

class ChampionData:
    def __init__(self):
        # Champion ID to Name mapping
        self.champion_ids = {
            1: 'Annie', 2: 'Olaf', 3: 'Galio', 4: 'Twisted Fate', 5: 'Xin Zhao',
            6: 'Urgot', 7: 'LeBlanc', 8: 'Vladimir', 9: 'Fiddlesticks', 10: 'Kayle',
            11: 'Master Yi', 12: 'Alistar', 13: 'Ryze', 14: 'Sion', 15: 'Sivir',
            16: 'Soraka', 17: 'Teemo', 18: 'Tristana', 19: 'Warwick', 20: 'Nunu & Willump',
            21: 'Miss Fortune', 22: 'Ashe', 23: 'Tryndamere', 24: 'Jax', 25: 'Morgana',
            26: 'Zilean', 27: 'Singed', 28: 'Evelynn', 29: 'Twitch', 30: 'Karthus',
            31: "Cho'Gath", 32: 'Amumu', 33: 'Rammus', 34: 'Anivia', 35: 'Shaco',
            36: 'Dr.Mundo', 37: 'Sona', 38: 'Kassadin', 39: 'Irelia', 40: 'Janna',
            41: 'Gangplank', 42: 'Corki', 43: 'Karma', 44: 'Taric', 45: 'Veigar',
            48: 'Trundle', 50: 'Swain', 51: 'Caitlyn', 53: 'Blitzcrank', 54: 'Malphite',
            55: 'Katarina', 56: 'Nocturne', 57: 'Maokai', 58: 'Renekton', 59: 'Jarvan IV',
            60: 'Elise', 61: 'Orianna', 62: 'Wukong', 63: 'Brand', 64: 'Lee Sin',
            67: 'Vayne', 68: 'Rumble', 69: 'Cassiopeia', 72: 'Skarner', 74: 'Heimerdinger',
            75: 'Nasus', 76: 'Nidalee', 77: 'Udyr', 78: 'Poppy', 79: 'Gragas',
            80: 'Pantheon', 81: 'Ezreal', 82: 'Mordekaiser', 83: 'Yorick', 84: 'Akali',
            85: 'Kennen', 86: 'Garen', 89: 'Leona', 90: 'Malzahar', 91: 'Talon',
            92: 'Riven', 96: "Kog'Maw", 98: 'Shen', 99: 'Lux', 101: 'Xerath',
            102: 'Shyvana', 103: 'Ahri', 104: 'Graves', 105: 'Fizz', 106: 'Volibear',
            107: 'Rengar', 110: 'Varus', 111: 'Nautilus', 112: 'Viktor', 113: 'Sejuani',
            114: 'Fiora', 115: 'Ziggs', 117: 'Lulu', 119: 'Draven', 120: 'Hecarim',
            121: "Kha'Zix", 122: 'Darius', 126: 'Jayce', 127: 'Lissandra', 131: 'Diana',
            133: 'Quinn', 134: 'Syndra', 136: 'Aurelion Sol', 141: 'Kayn', 142: 'Zoe',
            143: 'Zyra', 145: "Kai'sa", 147: 'Seraphine', 150: 'Gnar', 154: 'Zac',
            157: 'Yasuo', 161: "Vel'Koz", 163: 'Taliyah', 166: 'Akshan', 164: 'Camille',
            201: 'Braum', 202: 'Jhin', 203: 'Kindred', 222: 'Jinx', 223: 'Tahm Kench',
            234: 'Viego', 235: 'Senna', 236: 'Lucian', 238: 'Zed', 240: 'Kled',
            245: 'Ekko', 246: 'Qiyana', 254: 'Vi', 266: 'Aatrox', 267: 'Nami',
            268: 'Azir', 350: 'Yuumi', 360: 'Samira', 412: 'Thresh', 420: 'Illaoi',
            421: "Rek'Sai", 427: 'Ivern', 429: 'Kalista', 432: 'Bard', 497: 'Rakan',
            498: 'Xayah', 516: 'Ornn', 517: 'Sylas', 526: 'Rell', 518: 'Neeko',
            523: 'Aphelios', 555: 'Pyke', 875: 'Sett', 711: 'Vex', 777: 'Yone',
            887: 'Gwen', 876: 'Lillia', 888: 'Renata Glasc', 200: "Bel'Veth",
            895: 'Nilah', 897: "K'Sante", 902: 'Milio', 950: 'Naafiri', 233: 'Briar',
            910: 'Hwei', 901: 'Smolder', 893: 'Aurora', 221: 'Zeri', 799: 'Ambessa',
            800 : 'Mel'
        }

        # Create reverse mapping (name to ID) for emoji processing
        self.champion_names = {name.lower().replace("'", "").replace(" ", ""): id 
                             for id, name in self.champion_ids.items()}

    def get_emoji_id_map(self, emoji_name: str, emoji_id: str) -> tuple[int, str]:
        """Convert emoji name to champion ID and format"""
        name = emoji_name.lower()
        if name in self.champion_names:
            champ_id = self.champion_names[name]
            return champ_id, f'<:{emoji_name}:{emoji_id}>'
        return None, None

class EmojiProcessor:
    def __init__(self):
        # Known mappings for different categories
        self.champion_data = ChampionData()

        self.rank_names = {
            'iron', 'bronze', 'silver', 'gold', 'platinum', 'emerald', 
            'diamond', 'master', 'grandmaster', 'challenger'
        }

        self.spell_names = {
            'cleanse', 'exhaust', 'flash', 'ghost', 'heal', 'ignite', 'smite',
            'teleport', 'clarity', 'barrier', 'mark', 'flee', 'spellbooksmite',
            'spellbookplaceholder', 'porotoss', 'totheking', 'arenaflash'
        }

        # Initialize storage for processed emojis
        self.champion_emojis = {}
        self.rank_emojis = {}
        self.spell_emojis = {}
        self.custom_emojis = {}

    def process_emoji_list(self, emoji_text: str):
        """Process a list of emoji IDs"""
        for line in emoji_text.splitlines():
            if line.strip():
                match = re.match(r'<:([^:]+):(\d+)>', line.strip())
                if match:
                    name, emoji_id = match.groups()
                    name_lower = name.lower()

                    # Try to map to champion ID first
                    champ_id, emoji_str = self.champion_data.get_emoji_id_map(name, emoji_id)
                    if champ_id is not None:
                        self.champion_emojis[champ_id] = emoji_str
                    elif name_lower in self.rank_names:
                        self.rank_emojis[name_lower] = emoji_id
                    elif name_lower in self.spell_names:
                        self.spell_emojis[name_lower] = emoji_id
                    else:
                        self.custom_emojis[name] = emoji_id

    def generate_champion_mapping(self) -> str:
        """Generate champion mapping code"""
        # First generate the champion_mapping dictionary
        code = ["champion_mapping = {"]
        for champ_id, name in sorted(self.champion_data.champion_ids.items()):
            code.append(f"    {champ_id}: '{name}',")
        code.append("}\n")  # Extra newline for separation

        # Then generate the emoji_mapping dictionary
        code.append("emoji_mapping = {")
        for champ_id, emoji_str in sorted(self.champion_emojis.items()):
            code.append(f"    {champ_id}: '{emoji_str}',")
        code.append("}")

        # Add the get_champion_name function
        code.append("""
def get_champion_name(champion_id):
    champion_name = champion_mapping.get(champion_id, "Unknown Champion")
    emoji_name = emoji_mapping.get(champion_id, "<:blank:1283824838787596298>")
    return f"{emoji_name} {champion_name}"
""")

        return "\n".join(code)

    def update_file_content(self, filepath: str, new_mapping: str, variable_name: str) -> None:
        """Update file content while preserving other code"""
        try:
            # Read existing content
            existing_content = ""
            if Path(filepath).exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            # Find and replace the mapping
            pattern = f"{variable_name} = {{[^}}]*}}"
            if re.search(pattern, existing_content):
                updated_content = re.sub(pattern, new_mapping, existing_content)
            else:
                # If mapping doesn't exist, add it at the start
                updated_content = new_mapping + "\n\n" + existing_content

            # Write updated content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(updated_content)

        except Exception as e:
            print(f"Error updating {filepath}: {str(e)}")

    def parse_emoji_list(self, text: str) -> None:
        """Parse a list of emoji IDs"""
        lines = text.strip().split('\n')
        for line in lines:
            if line.strip():
                match = re.match(r'<:([^:]+):(\d+)>', line.strip())
                if match:
                    name, emoji_id = match.groups()
                    name_lower = name.lower()
                    
                    if name_lower in self.champion_names:
                        self.champion_emojis[name_lower] = emoji_id
                    elif name_lower in self.rank_names:
                        self.rank_emojis[name_lower] = emoji_id
                    elif name_lower in self.spell_names:
                        self.spell_emojis[name_lower] = emoji_id
                    else:
                        self.custom_emojis[name] = emoji_id

    def save_mappings(self, output_dir: str = 'Utils'):
        """Save all mappings to their respective files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Update champion mappings
        if self.champion_emojis:
            mapping = "emoji_mapping = {\n"
            mapping += "\n".join(f"    '{name}': '<:{name}:{id}>'," 
                               for name, id in sorted(self.champion_emojis.items()))
            mapping += "\n}"
            self.update_file_content(f'{output_dir}/getChampionNameByID.py', mapping, 'emoji_mapping')
            print(f"Updated champion mappings with {len(self.champion_emojis)} emojis")

        # Update rank mappings
        if self.rank_emojis:
            mapping = "RANK_EMOJI_MAPPING = {\n"
            mapping += "\n".join(f"    '{name.upper()}': '<:{name}:{id}>'," 
                               for name, id in sorted(self.rank_emojis.items()))
            mapping += "\n}"
            self.update_file_content(f'{output_dir}/rankEmojis.py', mapping, 'RANK_EMOJI_MAPPING')
            print(f"Updated rank mappings with {len(self.rank_emojis)} emojis")

        # Update spell mappings
        if self.spell_emojis:
            mapping = "summoner_spells = {\n"
            mapping += "\n".join(f"    '{name}': ('<:{name}:{id}>', '{name.title()}')," 
                               for name, id in sorted(self.spell_emojis.items()))
            mapping += "\n}"
            self.update_file_content(f'{output_dir}/summonerSpells.py', mapping, 'summoner_spells')
            print(f"Updated spell mappings with {len(self.spell_emojis)} emojis")

        # Update custom emojis
        if self.custom_emojis:
            mapping = "CUSTOM_EMOJIS = {\n"
            mapping += "\n".join(f"    '{name}': '<:{name}:{id}>'," 
                               for name, id in sorted(self.custom_emojis.items()))
            mapping += "\n}"
            self.update_file_content(f'{output_dir}/customEmojis.py', mapping, 'CUSTOM_EMOJIS')
            print(f"Updated custom emojis with {len(self.custom_emojis)} emojis")

    def generate_report(self) -> str:
        """Generate a report of processed emojis"""
        report = []
        report.append("\nEmoji Processing Report")
        report.append("=====================")
        report.append(f"\nChampion Emojis: {len(self.champion_emojis)}")
        report.append(f"Rank Emojis: {len(self.rank_emojis)}")
        report.append(f"Spell Emojis: {len(self.spell_emojis)}")
        report.append(f"Custom Emojis: {len(self.custom_emojis)}")
        
        if self.custom_emojis:
            report.append("\nCustom Emojis Found:")
            for name in sorted(self.custom_emojis.keys()):
                report.append(f"- {name}")
        
        return "\n".join(report)


if __name__ == "__main__":
    processor = EmojiProcessor()
    
    print("Paste your emoji list and press Enter twice when done:")
    emoji_list = []
    try:
        while True:
            line = input()
            if line.strip() == "":  # Empty line detected
                break
            emoji_list.append(line)
    except KeyboardInterrupt:
        print("\nInput cancelled.")
        exit()

    if emoji_list:
        emoji_text = "\n".join(emoji_list)
        processor.parse_emoji_list(emoji_text)
        processor.save_mappings()
        print(processor.generate_report())
    else:
        print("No emoji data provided.")