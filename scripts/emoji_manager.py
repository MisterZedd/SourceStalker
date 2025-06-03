"""
emoji_manager.py
A utility for downloading, uploading, and managing emojis for the Discord bot.
"""
import aiohttp
import asyncio
import os
import logging
import sys
import io
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from PIL import Image

import discord
from discord.ext import commands

from config_manager import ConfigManager
from scripts.emoji_processor import EmojiProcessor
from scripts.download_assets import download_assets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class EmojiCategory:
    """Enum of emoji categories for organization"""
    CHAMPION = "champions"
    RANK = "ranks"
    SPELL = "spells"
    CUSTOM = "custom"

class EmojiManager:
    """
    Class for managing emoji downloading, uploading, and processing.
    Provides tools for synchronizing emojis with Discord servers.
    """
    def __init__(self, config_manager: ConfigManager, client: discord.Client = None):
        """
        Initialize the emoji manager.
        
        Args:
            config_manager: Configuration manager instance
            client: Discord client instance for API calls
        """
        self.config = config_manager.config
        self.client = client
        self.emoji_processor = EmojiProcessor()
        
        # Paths for asset management
        self.assets_dir = Path("emoji_assets")
        self.champ_dir = self.assets_dir / EmojiCategory.CHAMPION
        self.rank_dir = self.assets_dir / EmojiCategory.RANK
        self.spell_dir = self.assets_dir / EmojiCategory.SPELL
        
        # Create directories if they don't exist
        for directory in [self.assets_dir, self.champ_dir, self.rank_dir, self.spell_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Mapping files to track emoji data
        self.mapping_file = self.assets_dir / "emoji_mappings.json"
        self.emoji_mappings: Dict[str, Dict[str, str]] = self._load_emoji_mappings()
        
    def _load_emoji_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Load emoji mappings from file.
        
        Returns:
            Dict[str, Dict[str, str]]: Mapping structure for emojis
        """
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading emoji mappings: {e}")
        
        # Return empty structure if file doesn't exist or is invalid
        return {
            EmojiCategory.CHAMPION: {},
            EmojiCategory.RANK: {},
            EmojiCategory.SPELL: {},
            EmojiCategory.CUSTOM: {}
        }
    
    def _save_emoji_mappings(self) -> None:
        """Save emoji mappings to file."""
        try:
            with open(self.mapping_file, 'w') as f:
                json.dump(self.emoji_mappings, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving emoji mappings: {e}")
    
    async def download_assets(self) -> Tuple[bool, str]:
        """
        Download all emoji assets from Community Dragon.
        
        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            logger.info("Starting emoji asset download process")
            await download_assets()
            return True, "Assets downloaded successfully"
        except Exception as e:
            logger.error(f"Error downloading assets: {e}")
            return False, f"Error downloading assets: {str(e)}"
    
    async def process_image(self, image_path: Path, trim: bool = False, resize: bool = True) -> Optional[io.BytesIO]:
        """
        Process an image for Discord emoji upload (resize, trim transparent edges).
        
        Args:
            image_path: Path to the image file
            trim: Whether to trim transparent edges
            resize: Whether to resize to Discord's size requirements
            
        Returns:
            Optional[io.BytesIO]: Processed image buffer or None on failure
        """
        try:
            # Open image
            img = Image.open(image_path)
            
            if trim and img.mode == 'RGBA':
                # Get the alpha channel
                alpha = img.getchannel('A')
                
                # Get boundaries of non-transparent pixels
                bbox = alpha.getbbox()
                if bbox:
                    # Crop to content
                    img = img.crop(bbox)
                    
                    # Add small padding
                    padding = 10
                    new_size = (img.width + padding*2, img.height + padding*2)
                    padded_img = Image.new('RGBA', new_size, (0, 0, 0, 0))
                    padded_img.paste(img, (padding, padding))
                    img = padded_img
            
            # Resize if needed (maximum 128x128 for Discord)
            if resize and (img.width > 128 or img.height > 128):
                img.thumbnail((128, 128), Image.Resampling.LANCZOS)
            
            # Convert to buffer
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return buffer
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None
    
    async def upload_emoji(self, guild: discord.Guild, name: str, image_path: Path, 
                          category: str, identifier: str = None) -> Optional[discord.Emoji]:
        """
        Upload an emoji to a Discord guild.
        
        Args:
            guild: Discord guild to upload to
            name: Emoji name (must be 2-32 characters, alphanumeric and underscores only)
            image_path: Path to the image file
            category: Emoji category for mapping
            identifier: Optional identifier for the emoji (champion ID, etc.)
            
        Returns:
            Optional[discord.Emoji]: Created emoji or None on failure
        """
        try:
            # Process image for upload
            image_buffer = await self.process_image(
                image_path,
                trim=(category == EmojiCategory.RANK),  # Trim rank emblems
                resize=True
            )
            
            if not image_buffer:
                return None
                
            # Clean name for Discord requirements
            clean_name = ''.join(c for c in name if c.isalnum() or c == '_').lower()
            if len(clean_name) < 2:
                clean_name = f"emoji_{clean_name}"
            if len(clean_name) > 32:
                clean_name = clean_name[:32]
            
            # Check if emoji with this name already exists
            existing_emoji = discord.utils.get(guild.emojis, name=clean_name)
            if existing_emoji:
                # Update mapping with existing emoji
                if identifier:
                    self.emoji_mappings[category][identifier] = str(existing_emoji.id)
                else:
                    self.emoji_mappings[category][clean_name] = str(existing_emoji.id)
                self._save_emoji_mappings()
                return existing_emoji
            
            # Check if guild has room for more emojis
            if len(guild.emojis) >= guild.emoji_limit:
                logger.warning(f"Guild {guild.name} has reached emoji limit ({guild.emoji_limit})")
                return None
            
            # Upload emoji
            emoji = await guild.create_custom_emoji(name=clean_name, image=image_buffer.read())
            
            # Save mapping
            if identifier:
                self.emoji_mappings[category][identifier] = str(emoji.id)
            else:
                self.emoji_mappings[category][clean_name] = str(emoji.id)
            self._save_emoji_mappings()
            
            return emoji
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to create emoji in guild {guild.name}")
            return None
        except Exception as e:
            logger.error(f"Error uploading emoji {name}: {e}")
            return None
            
    async def upload_all_emojis(self, guild: discord.Guild) -> Tuple[int, int, Dict[str, int]]:
        """
        Upload all downloaded emoji assets to a Discord guild.
        
        Args:
            guild: Discord guild to upload to
            
        Returns:
            Tuple[int, int, Dict[str, int]]: (Total uploaded, Failed, Category counts)
        """
        total_uploaded = 0
        total_failed = 0
        category_counts = {
            EmojiCategory.CHAMPION: 0,
            EmojiCategory.RANK: 0,
            EmojiCategory.SPELL: 0
        }
        
        # Upload champion emojis
        logger.info("Uploading champion emojis...")
        champion_files = list(self.champ_dir.glob("*.png"))
        
        # Check if we have room for all emojis
        remaining_slots = guild.emoji_limit - len(guild.emojis)
        if remaining_slots < len(champion_files):
            logger.warning(f"Not enough emoji slots available: {remaining_slots}/{len(champion_files)}")
            
        # First get mapping from champion ID to name
        from utils.getChampionNameByID import champion_mapping
        
        for champ_file in champion_files:
            # Extract champion ID from filename
            champ_id = champ_file.stem
            if not champ_id.isdigit():
                logger.warning(f"Invalid champion filename format: {champ_file.name}")
                continue
                
            # Get champion name
            champ_name = champion_mapping.get(int(champ_id), f"champion_{champ_id}")
            name_clean = champ_name.lower().replace("'", "").replace(" ", "").replace(".", "")
            
            # Upload emoji
            emoji = await self.upload_emoji(
                guild=guild,
                name=name_clean,
                image_path=champ_file,
                category=EmojiCategory.CHAMPION,
                identifier=champ_id
            )
            
            if emoji:
                total_uploaded += 1
                category_counts[EmojiCategory.CHAMPION] += 1
                logger.info(f"Uploaded champion emoji: {emoji.name} ({champ_name})")
            else:
                total_failed += 1
                
            # Avoid rate limiting
            await asyncio.sleep(1)
            
        # Upload rank emojis
        logger.info("Uploading rank emojis...")
        rank_files = list(self.rank_dir.glob("*.png"))
        
        for rank_file in rank_files:
            # Extract rank name from filename
            rank_name = rank_file.stem
            
            # Upload emoji
            emoji = await self.upload_emoji(
                guild=guild,
                name=rank_name.lower(),
                image_path=rank_file,
                category=EmojiCategory.RANK,
                identifier=rank_name.upper()
            )
            
            if emoji:
                total_uploaded += 1
                category_counts[EmojiCategory.RANK] += 1
                logger.info(f"Uploaded rank emoji: {emoji.name}")
            else:
                total_failed += 1
                
            # Avoid rate limiting
            await asyncio.sleep(1)
            
        # Upload summoner spell emojis
        logger.info("Uploading summoner spell emojis...")
        spell_files = list(self.spell_dir.glob("*.png"))
        
        for spell_file in spell_files:
            # Extract spell name from filename
            spell_name = spell_file.stem
            
            # Upload emoji
            emoji = await self.upload_emoji(
                guild=guild,
                name=spell_name.lower(),
                image_path=spell_file,
                category=EmojiCategory.SPELL,
                identifier=spell_name.lower()
            )
            
            if emoji:
                total_uploaded += 1
                category_counts[EmojiCategory.SPELL] += 1
                logger.info(f"Uploaded spell emoji: {emoji.name}")
            else:
                total_failed += 1
                
            # Avoid rate limiting
            await asyncio.sleep(1)
            
        return total_uploaded, total_failed, category_counts
    
    def generate_emoji_code(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate code for the emoji utility modules based on uploaded emojis.
        
        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: 
                (Champion emoji code, Rank emoji code, Spell emoji code)
        """
        try:
            # Generate champion emoji code
            champ_code = None
            if EmojiCategory.CHAMPION in self.emoji_mappings and self.emoji_mappings[EmojiCategory.CHAMPION]:
                champ_code = "emoji_mapping = {\n"
                
                for champ_id, emoji_id in sorted(self.emoji_mappings[EmojiCategory.CHAMPION].items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
                    champ_code += f"    {champ_id}: '<:champion_{champ_id}:{emoji_id}>',\n"
                
                champ_code += "}\n"
            
            # Generate rank emoji code
            rank_code = None
            if EmojiCategory.RANK in self.emoji_mappings and self.emoji_mappings[EmojiCategory.RANK]:
                rank_code = "RANK_EMOJI_MAPPING = {\n"
                
                for rank_name, emoji_id in sorted(self.emoji_mappings[EmojiCategory.RANK].items()):
                    rank_code += f"    '{rank_name}': '<:{rank_name.lower()}:{emoji_id}>',\n"
                
                rank_code += "}\n\n"
                rank_code += "# Function to get the emoji for a specific rank\n"
                rank_code += "def get_rank_emoji(tier):\n"
                rank_code += "    return RANK_EMOJI_MAPPING.get(tier.upper(), '')  # Fallback to an empty string if no match\n"
            
            # Generate spell emoji code
            spell_code = None
            if EmojiCategory.SPELL in self.emoji_mappings and self.emoji_mappings[EmojiCategory.SPELL]:
                spell_code = "def get_summoner_spell_name(spell_id):\n"
                spell_code += "    summoner_spells = {\n"
                
                # First get mapping from spell ID to name (hardcoded for now)
                spell_mapping = {
                    1: "cleanse",
                    3: "exhaust",
                    4: "flash",
                    6: "ghost",
                    7: "heal",
                    11: "smite",
                    12: "teleport",
                    13: "clarity",
                    14: "ignite",
                    21: "barrier"
                }
                
                for spell_id, spell_name in spell_mapping.items():
                    emoji_id = self.emoji_mappings[EmojiCategory.SPELL].get(spell_name)
                    if emoji_id:
                        spell_code += f"        {spell_id}: ('<:{spell_name}:{emoji_id}>', '{spell_name.title()}'),\n"
                
                spell_code += "    }\n"
                spell_code += "    return summoner_spells.get(spell_id, ('<:spellbookplaceholder:0>', 'Unknown Spell'))\n"
            
            return champ_code, rank_code, spell_code
            
        except Exception as e:
            logger.error(f"Error generating emoji code: {e}")
            return None, None, None
    
    def update_utility_files(self, champ_code: str = None, rank_code: str = None, spell_code: str = None) -> bool:
        """
        Update the utility files with generated emoji code.
        
        Args:
            champ_code: Champion emoji code
            rank_code: Rank emoji code
            spell_code: Spell emoji code
            
        Returns:
            bool: Success status
        """
        try:
            # Create utils directory if it doesn't exist
            utils_dir = Path("utils")
            utils_dir.mkdir(exist_ok=True)
            
            # Update champion emoji file
            if champ_code:
                champ_path = utils_dir / "getChampionNameByID.py"
                
                # Read existing content to preserve champion mapping
                champion_mapping = {}
                if champ_path.exists():
                    with open(champ_path, 'r') as f:
                        content = f.read()
                        
                        # Extract champion mapping
                        import re
                        pattern = r"champion_mapping = {(.*?)}"
                        match = re.search(pattern, content, re.DOTALL)
                        if match:
                            mapping_str = match.group(1)
                            # Parse the mapping
                            for line in mapping_str.strip().split('\n'):
                                line = line.strip()
                                if line and ':' in line:
                                    key_value = line.split(':', 1)
                                    key = key_value[0].strip()
                                    value = key_value[1].strip().rstrip(',')
                                    champion_mapping[key] = value
                
                # Write updated content
                with open(champ_path, 'w') as f:
                    # Write champion mapping first
                    f.write("champion_mapping = {\n")
                    for key, value in sorted(champion_mapping.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
                        f.write(f"    {key}: {value},\n")
                    f.write("}\n\n")
                    
                    # Write emoji mapping
                    f.write(champ_code + "\n")
                    
                    # Add function to get champion name
                    f.write("\ndef get_champion_name(champion_id):\n")
                    f.write("    champion_name = champion_mapping.get(champion_id, \"Unknown Champion\")\n")
                    f.write("    emoji_name = emoji_mapping.get(champion_id, \"<:blank:1283824838787596298>\")\n")
                    f.write("\n    return f\"{emoji_name} {champion_name}\"")
            
            # Update rank emoji file
            if rank_code:
                rank_path = utils_dir / "rankEmojis.py"
                with open(rank_path, 'w') as f:
                    f.write(rank_code)
            
            # Update spell emoji file
            if spell_code:
                spell_path = utils_dir / "summonerSpells.py"
                with open(spell_path, 'w') as f:
                    f.write("# Utils/getSummonerSpellNameByID.py\n\n")
                    f.write(spell_code)
            
            logger.info("Utility files updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating utility files: {e}")
            return False
    
    async def setup_emojis(self, guild_id: int) -> Tuple[bool, str]:
        """
        Complete emoji setup process: download assets, upload to Discord, and update utility files.
        
        Args:
            guild_id: Discord guild ID to upload emojis to
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        if not self.client:
            return False, "Discord client is not available"
            
        try:
            # Download assets
            success, message = await self.download_assets()
            if not success:
                return False, message
            
            # Get the guild
            guild = self.client.get_guild(guild_id)
            if not guild:
                return False, f"Guild with ID {guild_id} not found"
            
            # Upload emojis
            total_uploaded, total_failed, category_counts = await self.upload_all_emojis(guild)
            
            # Generate and update utility files
            champ_code, rank_code, spell_code = self.generate_emoji_code()
            self.update_utility_files(champ_code, rank_code, spell_code)
            
            return True, f"Emoji setup complete: {total_uploaded} uploaded, {total_failed} failed"
            
        except Exception as e:
            logger.error(f"Error during emoji setup: {e}")
            return False, f"Error during emoji setup: {str(e)}"

# GUI interface for emoji management
class EmojiManagerGUI:
    """GUI interface for the EmojiManager, integrated with the main application GUI."""
    
    def __init__(self, parent_frame, config_manager, client=None):
        """
        Initialize the emoji manager GUI.
        
        Args:
            parent_frame: Parent tkinter frame
            config_manager: Configuration manager instance
            client: Discord client instance
        """
        import tkinter as tk
        from tkinter import ttk, messagebox
        
        self.parent = parent_frame
        self.config_manager = config_manager
        self.client = client
        self.emoji_manager = EmojiManager(config_manager, client)
        
        # Create main frame
        self.frame = ttk.Frame(parent_frame)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create title
        ttk.Label(self.frame, text="Emoji Manager", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 20))
        
        # Guild ID input
        ttk.Label(self.frame, text="Discord Guild ID for Emoji Upload").pack(anchor=tk.W)
        self.guild_id_var = tk.StringVar()
        self.guild_id_entry = ttk.Entry(self.frame, textvariable=self.guild_id_var)
        self.guild_id_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Initialize with value from config if available
        if hasattr(self.config_manager.config.discord, 'emoji_guild_id'):
            self.guild_id_var.set(self.config_manager.config.discord.emoji_guild_id)
        
        # Action buttons
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.download_btn = ttk.Button(
            self.button_frame,
            text="Download Assets",
            command=self.download_assets,
            style='TButton'
        )
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.upload_btn = ttk.Button(
            self.button_frame,
            text="Upload Emojis",
            command=self.upload_emojis,
            style='TButton'
        )
        self.upload_btn.pack(side=tk.LEFT, padx=5)
        
        self.setup_btn = ttk.Button(
            self.button_frame,
            text="Full Setup",
            command=self.full_setup,
            style='TButton'
        )
        self.setup_btn.pack(side=tk.LEFT, padx=5)
        
        # Status display
        ttk.Label(self.frame, text="Status:").pack(anchor=tk.W, pady=(20, 5))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.frame, textvariable=self.status_var).pack(anchor=tk.W)
        
        # Progress display
        self.progress = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL, length=400, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
    def save_settings(self):
        """Save emoji manager settings to config."""
        guild_id = self.guild_id_var.get().strip()
        if guild_id:
            # Add to config
            self.config_manager.config.discord.emoji_guild_id = guild_id
            
            # Save to config file
            config_dict = self.config_manager.get_config_dict()
            self.config_manager.save_config_dict(config_dict)
    
    def download_assets(self):
        """Handle download assets button click."""
        import tkinter as tk
        from tkinter import messagebox
        import threading
        
        # Save settings
        self.save_settings()
        
        # Start progress bar
        self.progress.start()
        self.status_var.set("Downloading assets...")
        
        # Run in background thread
        def run_download():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.emoji_manager.download_assets())
                success, message = result
                
                # Update UI
                self.parent.after(0, lambda: self.update_status(success, message))
            finally:
                loop.close()
        
        threading.Thread(target=run_download, daemon=True).start()
    
    def upload_emojis(self):
        """Handle upload emojis button click."""
        import tkinter as tk
        from tkinter import messagebox
        import threading
        
        # Save settings
        self.save_settings()
        
        # Check guild ID
        guild_id = self.guild_id_var.get().strip()
        if not guild_id or not guild_id.isdigit():
            messagebox.showerror("Error", "Please enter a valid Discord Guild ID")
            return
        
        # Check client
        if not self.client:
            messagebox.showerror("Error", "Discord client is not available. Please start the bot first.")
            return
        
        # Start progress bar
        self.progress.start()
        self.status_var.set("Uploading emojis...")
        
        # Run in background thread
        def run_upload():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Get the guild
                guild = self.client.get_guild(int(guild_id))
                if not guild:
                    self.parent.after(0, lambda: self.update_status(False, f"Guild with ID {guild_id} not found"))
                    return
                
                # Upload emojis
                result = loop.run_until_complete(self.emoji_manager.upload_all_emojis(guild))
                total_uploaded, total_failed, category_counts = result
                
                # Generate and update utility files
                champ_code, rank_code, spell_code = self.emoji_manager.generate_emoji_code()
                self.emoji_manager.update_utility_files(champ_code, rank_code, spell_code)
                
                # Update UI
                self.parent.after(0, lambda: self.update_status(
                    True, 
                    f"Uploaded {total_uploaded} emojis, {total_failed} failed"
                ))
            except Exception as e:
                self.parent.after(0, lambda: self.update_status(False, f"Error: {str(e)}"))
            finally:
                loop.close()
        
        threading.Thread(target=run_upload, daemon=True).start()
    
    def full_setup(self):
        """Handle full setup button click."""
        import tkinter as tk
        from tkinter import messagebox
        import threading
        
        # Save settings
        self.save_settings()
        
        # Check guild ID
        guild_id = self.guild_id_var.get().strip()
        if not guild_id or not guild_id.isdigit():
            messagebox.showerror("Error", "Please enter a valid Discord Guild ID")
            return
        
        # Check client
        if not self.client:
            messagebox.showerror("Error", "Discord client is not available. Please start the bot first.")
            return
        
        # Start progress bar
        self.progress.start()
        self.status_var.set("Running full emoji setup...")
        
        # Run in background thread
        def run_setup():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.emoji_manager.setup_emojis(int(guild_id)))
                success, message = result
                
                # Update UI
                self.parent.after(0, lambda: self.update_status(success, message))
            except Exception as e:
                self.parent.after(0, lambda: self.update_status(False, f"Error: {str(e)}"))
            finally:
                loop.close()
        
        threading.Thread(target=run_setup, daemon=True).start()
    
    def update_status(self, success: bool, message: str):
        """Update the status display."""
        import tkinter as tk
        from tkinter import messagebox
        
        # Stop progress bar
        self.progress.stop()
        
        # Update status text
        self.status_var.set(message)
        
        # Show message box
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)