import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
import logging
from typing import Dict, Any
import aiohttp
import asyncio
import threading

class ThemeManager:
    def __init__(self, config_manager):
        self.dark_theme = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'input_bg': '#2d2d2d',
            'input_fg': '#ffffff',
            'button_bg': '#333333',
            'button_fg': '#ffffff',
            'hover_bg': '#404040'
        }
        
        self.light_theme = {
            'bg': '#ffffff',
            'fg': '#000000',
            'input_bg': '#f8f8f8',
            'input_fg': '#000000',
            'button_bg': '#e0e0e0',
            'button_fg': '#000000',
            'hover_bg': '#d0d0d0'
        }

    def apply_theme(self, root: tk.Tk, style: ttk.Style, is_dark: bool = True):
        theme = self.dark_theme if is_dark else self.light_theme
        
        # Configure root window
        root.configure(bg=theme['bg'])
        
        # Configure basic styles
        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TCheckbutton', background=theme['bg'], foreground=theme['fg'])
        
        # Configure text entry
        style.configure('TEntry',
            fieldbackground=theme['input_bg'],
            foreground=theme['input_fg'])
        
        # Configure combobox
        style.configure('TCombobox',
            fieldbackground=theme['input_bg'],
            foreground=theme['input_fg'],
            selectbackground=theme['button_bg'],
            selectforeground=theme['input_fg'])
        
        style.map('TCombobox',
            fieldbackground=[('readonly', theme['input_bg'])],
            background=[('readonly', theme['input_bg'])],
            foreground=[('readonly', theme['input_fg'])])
        
        # Headers and titles
        style.configure('Header.TLabel',
                       background=theme['bg'],
                       foreground=theme['fg'],
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure('Title.TLabel',
                       background=theme['bg'],
                       foreground=theme['fg'],
                       font=('Segoe UI', 14, 'bold'))

class EnhancedGUI:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.root = tk.Tk()
        self.root.title("SourceStalker Configuration")
        self.root.geometry("800x950")

        self.region_mappings = {
            'BR1': ('americas', 'Brazil'),
            'EUN1': ('europe', 'Europe Nordic & East'),
            'EUW1': ('europe', 'Europe West'),
            'JP1': ('asia', 'Japan'),
            'KR': ('asia', 'Korea'),
            'LA1': ('americas', 'Latin America North'),
            'LA2': ('americas', 'Latin America South'),
            'NA1': ('americas', 'North America'),
            'OC1': ('sea', 'Oceania'),
            'PH2': ('sea', 'Philippines'),
            'RU': ('europe', 'Russia'),
            'SG2': ('sea', 'Singapore'),
            'TH2': ('sea', 'Thailand'),
            'TR1': ('europe', 'Turkey'),
            'TW2': ('sea', 'Taiwan'),
            'VN2': ('sea', 'Vietnam')
        }
        
        # Initialize theme manager and default database path
        self.theme_manager = ThemeManager(config_manager)
        self.style = ttk.Style()
        self.is_dark_mode = True
        self.default_db_path = "/app/rank_tracker.db"
        
        # Initialize state
        self.show_advanced = tk.BooleanVar(value=False)
        self.current_values = {
            'region': 'NA1',
            'db_path': '/app/rank_tracker.db'
        }

        self.nickname = None
        self.message_save_btn = None
        
        self.setup_gui()

    def create_buttons(self, parent_frame):
        """Create all buttons with proper styling"""
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        
        # Theme toggle button
        self.theme_btn = tk.Button(
            self.header_frame,
            text="🌙" if self.is_dark_mode else "☀️",
            command=self.toggle_theme,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            width=3,
            cursor="hand2"
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=5)

        # Action buttons
        self.button_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.button_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.save_btn = tk.Button(
            self.button_frame,
            text="Save Configuration",
            command=self.save_config,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        
        self.test_btn = tk.Button(
            self.button_frame,
            text="Test Connection",
            command=self.test_connection,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.test_btn.pack(side=tk.RIGHT, padx=5)

    def update_button_colors(self):
        """Update all button colors based on current theme"""
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        
        # Update theme button
        self.theme_btn.configure(
            text="🌙" if self.is_dark_mode else "☀️",
            bg=theme['button_bg'],
            fg=theme['button_fg']
        )
        
        # Update action buttons
        for btn in [self.save_btn, self.test_btn]:
            btn.configure(
                bg=theme['button_bg'],
                fg=theme['button_fg']
            )

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.is_dark_mode = not self.is_dark_mode
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        
        # Apply theme
        self.theme_manager.apply_theme(self.root, self.style, self.is_dark_mode)
        
        # Update buttons
        self.theme_btn.configure(
            text="🌙" if self.is_dark_mode else "☀️",
            bg=theme['button_bg'],
            fg=theme['button_fg']
        )
        
        for btn in [self.save_btn, self.test_btn, self.theme_btn, self.main_settings_btn, self.message_settings_btn, self.message_save_btn]:
            btn.configure(
                bg=theme['button_bg'],
                fg=theme['button_fg']
            )

        # Update entries recursively
        def update_widgets(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Entry):
                    child.configure(
                        fg=theme['input_fg'],
                        bg=theme['input_bg'],
                        insertbackground=theme['input_fg']
                    )
                elif isinstance(child, tk.OptionMenu):
                    child.configure(
                        bg=theme['input_bg'],
                        fg=theme['input_fg'],
                        activebackground=theme['button_bg'],
                        activeforeground=theme['input_fg']
                    )
                    child["menu"].configure(
                        bg=theme['input_bg'],
                        fg=theme['input_fg'],
                        activebackground=theme['button_bg'],
                        activeforeground=theme['input_fg']
                    )
                update_widgets(child)
        
        # Start recursive update from main frame
        update_widgets(self.main_frame)

    def create_advanced_section(self, parent_frame):
        """Create advanced settings section"""
        advanced_toggle = ttk.Checkbutton(
            parent_frame,
            text="Show Advanced Settings",
            variable=self.show_advanced,
            style='TCheckbutton',
            command=self.toggle_advanced
        )
        advanced_toggle.pack(anchor=tk.W, pady=(0, 10))
        
        self.advanced_frame = ttk.Frame(parent_frame, style='TFrame')
        self.advanced_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(self.advanced_frame, text="Database Path").pack(anchor=tk.W)
        
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        self.db_path = tk.Entry(
            self.advanced_frame, 
            width=50,
            fg=theme['input_fg'],
            bg=theme['input_bg'],
            insertbackground=theme['input_fg']
        )
        self.db_path.pack(fill=tk.X, pady=(0, 10))
        self.db_path.insert(0, self.default_db_path)
        
        if not self.show_advanced.get():
            self.advanced_frame.pack_forget()

    def load_existing_config(self):
        """Load existing configuration if available"""
        config = self.config_manager.config
        
        # Discord settings
        self.discord_token.insert(0, config.discord.bot_token)
        self.channel_id.insert(0, config.discord.channel_id)
        
        # Riot settings
        self.riot_api_key.insert(0, config.riot.api_key)
        self.summoner_name.insert(0, config.riot.summoner_name)
        self.summoner_tag.insert(0, config.riot.summoner_tag)
        
        # For region, we need to set the StringVar value instead of the OptionMenu directly
        if hasattr(config.riot, 'region'):
            region_display = f"{config.riot.region} - {self.region_mappings[config.riot.region][1]}"
            self.region_var.set(region_display)
        
        # Advanced settings
        self.db_path.delete(0, tk.END)
        self.db_path.insert(0, config.database.path or self.default_db_path)

        # Load message templates
        if hasattr(config, 'messages'):
            self.nickname.delete(0, tk.END)
            self.nickname.insert(0, config.messages.nickname or "")
            
            for key in self.message_entries:
                self.message_entries[key].delete(0, tk.END)
                self.message_entries[key].insert(0, getattr(config.messages, key))

    def setup_main_settings(self):
        """Setup the main settings page - original config page"""
        self.create_discord_section(self.main_settings_frame)
        self.create_riot_section(self.main_settings_frame)
        self.create_advanced_section(self.main_settings_frame)
        self.create_action_buttons(self.main_settings_frame)

    def setup_message_settings(self):
        """Setup the message templates page"""
        # Nickname field
        ttk.Label(self.message_settings_frame, 
                text="Custom Nickname (leave empty to use Summoner Name)", 
                style='TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.nickname = self.create_entry_with_label(self.message_settings_frame, "", add_label=False)
        
        templates = [
            ("Game Start", "game_start", "{summoner_name} is in a game now! Monitoring..."),
            ("Game Win", "game_win", "{summoner_name} got carried!"),
            ("Game Loss", "game_loss", "{summoner_name} threw the game!"),
            ("Death Count", "death_count", "Amount of times {summoner_name} died: {deaths}"),
            ("LP Gain", "lp_gain", "{summoner_name} gained {lp_change} LP in {queue_type}!"),
            ("LP Loss", "lp_loss", "{summoner_name} lost {lp_change} LP in {queue_type}!")
        ]
        
        self.message_entries = {}
        for label, key, default in templates:
            ttk.Label(self.message_settings_frame, text=label, 
                    style='TLabel').pack(anchor=tk.W, pady=(15, 5))
            entry = self.create_entry_with_label(self.message_settings_frame, "", add_label=False)
            entry.insert(0, default)
            self.message_entries[key] = entry
            
            ttk.Label(self.message_settings_frame, 
                    text="Available variables: {summoner_name}, {deaths}, {lp_change}, {queue_type}",
                    style='Small.TLabel').pack(anchor=tk.W, pady=(2, 0))
        
        # Add save button for message templates
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        self.message_save_btn = tk.Button(
            self.message_settings_frame,
            text="Save Message Templates",
            command=self.save_config,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.message_save_btn.pack(side=tk.RIGHT, pady=(20, 10))
        
    def setup_gui(self):
        """Setup the main GUI interface"""
        # Apply initial theme
        self.theme_manager.apply_theme(self.root, self.style, self.is_dark_mode)
        
        # Create main container with padding
        self.main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create header frame for title and theme button
        self.header_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Add title
        ttk.Label(self.header_frame, 
                text="SourceStalker Configuration", 
                style='Title.TLabel').pack(side=tk.LEFT)

        # Create navigation frame for tab buttons
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 20))

        # Create frames for each "page"
        self.main_settings_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.message_settings_frame = ttk.Frame(self.main_frame, style='Main.TFrame')

        # Create tab buttons
        self.main_settings_btn = tk.Button(
            nav_frame,
            text="Main Settings",
            command=self.show_main_settings,
            relief="flat",
            bg="#333333" if self.is_dark_mode else "#e0e0e0",
            fg="#ffffff" if self.is_dark_mode else "#000000",
            cursor="hand2"
        )
        self.main_settings_btn.pack(side=tk.LEFT, padx=5)
        
        self.message_settings_btn = tk.Button(
            nav_frame,
            text="Message Templates",
            command=self.show_message_settings,
            relief="flat",
            bg="#333333" if self.is_dark_mode else "#e0e0e0",
            fg="#ffffff" if self.is_dark_mode else "#000000",
            cursor="hand2"
        )
        self.message_settings_btn.pack(side=tk.LEFT, padx=5)

        # Add theme toggle button to header
        self.theme_btn = tk.Button(
            self.header_frame,
            text="🌙" if self.is_dark_mode else "☀️",
            command=self.toggle_theme,
            relief="flat",
            bg="#333333" if self.is_dark_mode else "#e0e0e0",
            fg="#ffffff" if self.is_dark_mode else "#000000",
            width=3,
            cursor="hand2"
        )
        self.theme_btn.pack(side=tk.RIGHT)

        # Set up both pages
        self.setup_main_settings()
        self.setup_message_settings()
        
        # Show main settings by default
        self.show_main_settings()
        
        # Load existing configuration
        self.load_existing_config()

    def show_main_settings(self):
        """Switch to main settings view"""
        self.message_settings_frame.pack_forget()
        self.main_settings_frame.pack(fill=tk.BOTH, expand=True)
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        self.main_settings_btn.configure(bg="#4a4a4a" if self.is_dark_mode else "#cccccc")
        self.message_settings_btn.configure(bg=theme['button_bg'])

    def show_message_settings(self):
        """Switch to message templates view"""
        self.main_settings_frame.pack_forget()
        self.message_settings_frame.pack(fill=tk.BOTH, expand=True)
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        self.message_settings_btn.configure(bg="#4a4a4a" if self.is_dark_mode else "#cccccc")
        self.main_settings_btn.configure(bg=theme['button_bg'])

    def create_entry_with_label(self, parent_frame, label_text, show=None, add_label=True):
        """Helper function to create a labeled entry with consistent styling"""
        if add_label and label_text:
            ttk.Label(parent_frame, text=label_text).pack(anchor=tk.W, pady=(10, 5))
        
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        entry = tk.Entry(
            parent_frame, 
            width=50, 
            show=show,
            fg=theme['input_fg'],
            bg=theme['input_bg'],
            insertbackground=theme['input_fg']
        )
        entry.pack(fill=tk.X, pady=(0, 5))
        return entry

    def create_discord_section(self, parent_frame):
        """Create Discord configuration section"""
        ttk.Label(parent_frame, text="Discord Settings", 
                style='Header.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        self.discord_token = self.create_entry_with_label(parent_frame, "Bot Token", show="•")
        self.channel_id = self.create_entry_with_label(parent_frame, "Channel ID")
        
    def create_riot_section(self, parent_frame):
        """Create Riot API configuration section"""
        ttk.Label(parent_frame, text="Riot API Settings", 
                style='Header.TLabel').pack(anchor=tk.W, pady=(20, 10))
        
        self.riot_api_key = self.create_entry_with_label(parent_frame, "API Key", show="•")
        self.summoner_name = self.create_entry_with_label(parent_frame, "Summoner Name")
        self.summoner_tag = self.create_entry_with_label(parent_frame, "Summoner Tag")
        
        # Region selection
        ttk.Label(parent_frame, text="Region", style='TLabel').pack(anchor=tk.W, pady=(10, 5))
        region_options = [f"{code} - {self.region_mappings[code][1]}" for code in sorted(self.region_mappings.keys())]
        
        self.region_var = tk.StringVar()
        self.region = tk.OptionMenu(parent_frame, self.region_var, *region_options)
        
        # Style the OptionMenu
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        self.region.configure(
            bg=theme['input_bg'],
            fg=theme['input_fg'],
            activebackground=theme['button_bg'],
            activeforeground=theme['input_fg'],
            highlightthickness=0,
            relief="flat"
        )
        
        self.region["menu"].configure(
            bg=theme['input_bg'],
            fg=theme['input_fg'],
            activebackground=theme['button_bg'],
            activeforeground=theme['input_fg']
        )
        self.region.pack(fill=tk.X)
        
        # Set default value
        default_region = f"NA1 - {self.region_mappings['NA1'][1]}"
        self.region_var.set(default_region)
        self.region_var.trace('w', self.on_region_change)

    def on_region_change(self, *args):
        """Store region value when changed"""
        region_code = self.region_var.get().split(' - ')[0]  # Get just the region code
        self.current_values['region'] = region_code
        self.current_values['region_display'] = self.region_var.get()
            
    def create_action_buttons(self, parent_frame):
        """Create action buttons"""
        button_frame = ttk.Frame(parent_frame, style='Main.TFrame')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        theme = self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
        
        self.save_btn = tk.Button(
            button_frame,
            text="Save Configuration",
            command=self.save_config,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        
        self.test_btn = tk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_connection,
            relief="flat",
            bg=theme['button_bg'],
            fg=theme['button_fg'],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.test_btn.pack(side=tk.RIGHT, padx=5)
        
    def toggle_advanced(self):
        """Toggle advanced settings visibility"""
        if self.show_advanced.get():
            self.advanced_frame.pack(fill=tk.X, pady=(0, 15))
        else:
            self.advanced_frame.pack_forget()
            
    def save_config(self):
        """Update save_config to include message templates"""
        try:
            region_code = self.region_var.get().split(' - ')[0]
            platform = self.region_mappings[region_code][0]
            
            config = {
                'discord': {
                    'bot_token': self.discord_token.get(),
                    'channel_id': self.channel_id.get(),
                    'rate_limit': 10,
                    'time_window': 120
                },
                'riot': {
                    'api_key': self.riot_api_key.get(),
                    'summoner_name': self.summoner_name.get(),
                    'summoner_tag': self.summoner_tag.get(),
                    'region': region_code,
                    'platform': platform,
                    'summoner_id': ""
                },
                'database': {
                    'path': self.db_path.get(),
                    'check_interval': 10
                },
                'messages': {
                    'nickname': self.nickname.get(),
                    'game_start': self.message_entries['game_start'].get(),
                    'game_win': self.message_entries['game_win'].get(),
                    'game_loss': self.message_entries['game_loss'].get(),
                    'death_count': self.message_entries['death_count'].get(),
                    'lp_gain': self.message_entries['lp_gain'].get(),
                    'lp_loss': self.message_entries['lp_loss'].get()
                }
            }
            
            # Validate configuration
            if not config['discord']['bot_token']:
                messagebox.showerror("Error", "Discord bot token is required")
                return
            if not config['discord']['channel_id']:
                messagebox.showerror("Error", "Discord channel ID is required")
                return
            if not config['riot']['api_key']:
                messagebox.showerror("Error", "Riot API key is required")
                return
            if not config['riot']['summoner_name']:
                messagebox.showerror("Error", "Summoner name is required")
                return
                
            # Save configuration
            self.config_manager.save_config_dict(config)
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    async def test_discord_connection(self):
        """Test Discord bot token and channel access"""
        bot_token = self.discord_token.get()
        channel_id = self.channel_id.get()
        
        if not bot_token or not channel_id:
            return False, "Discord bot token and channel ID are required"
        
        try:
            # Test Discord API access
            headers = {'Authorization': f'Bot {bot_token}'}
            async with aiohttp.ClientSession() as session:
                # Test channel access
                url = f'https://discord.com/api/v10/channels/{channel_id}'
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return False, "Could not access Discord channel. Please check token and channel ID."
            return True, "Discord connection successful!"
        except Exception as e:
            return False, f"Discord connection failed: {str(e)}"
        
    async def test_riot_connection(self):
        """Test Riot API access with proper Riot ID support"""
        api_key = self.riot_api_key.get()
        summoner_name = self.summoner_name.get()
        summoner_tag = self.summoner_tag.get()
        region = self.region_var.get().split(' - ')[0]  # Get just the region code
        
        print(f"Debug - Testing Riot API connection with:")
        print(f"- Region: {region}")
        print(f"- Game Name: {summoner_name}")
        print(f"- Tag Line: {summoner_tag}")
        print(f"- API Key: {api_key[:5]}...{api_key[-5:]}") # Print parts of key for security
        
        if not all([api_key, summoner_name, summoner_tag, region]):
            return False, "All Riot API fields are required"
        
        try:
            platform = self.region_mappings[region][0]  # Get platform from mappings
            print(f"- Platform: {platform}")
            
            headers = {'X-Riot-Token': api_key}
            async with aiohttp.ClientSession() as session:
                # Use the current recommended endpoint
                url = f'https://{platform}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{summoner_tag}'
                print(f"- Testing URL: {url}")
                
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    print(f"- Response status: {status}")
                    
                    if response.status == 403:
                        return False, "Invalid API key. Please check your Riot API key."
                    elif response.status == 404:
                        return False, f"Could not find account '{summoner_name}#{summoner_tag}'. Please check the name and tag."
                    elif response.status != 200:
                        text = await response.text()
                        print(f"- Response text: {text}")
                        return False, f"API request failed with status {response.status}. Response: {text}"
                    
                    data = await response.json()
                    print(f"- Response data: {data}")
                    
                    if not data.get('puuid'):
                        return False, "Invalid response from Riot API. Missing PUUID in response."
                    
                    # If successful, optionally test fetching summoner data as well
                    summoner_url = f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{data["puuid"]}'
                    print(f"- Testing summoner URL: {summoner_url}")
                    
                    async with session.get(summoner_url, headers=headers) as summoner_response:
                        if summoner_response.status == 200:
                            summoner_data = await summoner_response.json()
                            print(f"- Summoner data: {summoner_data}")
                            return True, f"Successfully found account '{summoner_name}#{summoner_tag}'!"
                        else:
                            # Even if this fails, the account lookup succeeded
                            return True, f"Found Riot account, but couldn't fetch summoner details."
                        
        except Exception as e:
            print(f"- Exception: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
        
    async def run_connection_tests(self):
        """Run all connection tests"""
        results = []
        
        # Test Discord connection
        discord_success, discord_msg = await self.test_discord_connection()
        results.append(("Discord", discord_success, discord_msg))
        
        # Test Riot API connection
        riot_success, riot_msg = await self.test_riot_connection()
        results.append(("Riot API", riot_success, riot_msg))
        
        return results
    
    def test_connection(self):
        """Handle test connection button click"""
        async def run_tests():
            results = []
            
            # Test Discord connection
            discord_success, discord_msg = await self.test_discord_connection()
            results.append(("Discord", discord_success, discord_msg))
            
            # Test Riot API connection
            riot_success, riot_msg = await self.test_riot_connection()
            results.append(("Riot API", riot_success, riot_msg))
            
            return results

        def show_results(results):
            message = ""
            all_successful = True
            for service, success, msg in results:
                status = "✅" if success else "❌"
                message += f"{status} {service}: {msg}\n\n"
                all_successful = all_successful and success
            
            if all_successful:
                messagebox.showinfo("Connection Test Results", message)
            else:
                messagebox.showerror("Connection Test Results", message)

        async def run_async_tests():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = await run_tests()
                self.root.after(0, lambda: show_results(results))
            finally:
                loop.close()

        # Start async tests in a separate thread
        threading.Thread(target=lambda: asyncio.run(run_async_tests()), daemon=True).start()

    def create_messages_section(self):
        """Create Messages configuration section"""
        messages_frame = ttk.Frame(self.main_frame, style='TFrame')
        messages_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Label(messages_frame, text="Message Templates", 
                style='Header.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # Nickname field
        ttk.Label(messages_frame, text="Custom Nickname (leave empty to use Summoner Name)").pack(anchor=tk.W)
        self.nickname = self.create_entry_with_label(messages_frame, "Nickname")
        
        # Message template fields
        templates = [
            ("Game Start", "game_start", "{summoner_name} is in a game now! Monitoring..."),
            ("Game Win", "game_win", "{summoner_name} got carried!"),
            ("Game Loss", "game_loss", "{summoner_name} threw the game!"),
            ("Death Count", "death_count", "Amount of times {summoner_name} died: {deaths}"),
            ("LP Gain", "lp_gain", "{summoner_name} gained {lp_change} LP in {queue_type}!"),
            ("LP Loss", "lp_loss", "{summoner_name} lost {lp_change} LP in {queue_type}!")
        ]
        
        self.message_entries = {}
        for label, key, default in templates:
            ttk.Label(messages_frame, text=label).pack(anchor=tk.W)
            entry = self.create_entry_with_label(messages_frame, f"Template ({key})")
            entry.insert(0, default)
            self.message_entries[key] = entry
            
            # Add helper text
            ttk.Label(messages_frame, 
                    text="Available variables: {summoner_name}, {deaths}, {lp_change}, {queue_type}",
                    style='Small.TLabel').pack(anchor=tk.W, pady=(0, 10))

def launch_gui(config_manager) -> None:
    """Launch the enhanced GUI"""
    gui = EnhancedGUI(config_manager)
    gui.root.mainloop()