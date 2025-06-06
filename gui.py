import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
import logging
from typing import Dict, Any
import aiohttp
import asyncio
import threading
import math
import time

class ModernThemeManager:
    def __init__(self):
        # Enhanced dark theme with modern colors and gradients
        self.dark_theme = {
            'bg': '#0d1117',           # GitHub dark background
            'fg': '#f0f6fc',           # Light text
            'card_bg': '#161b22',      # Card backgrounds
            'input_bg': '#21262d',     # Input backgrounds
            'input_fg': '#f0f6fc',     # Input text
            'button_bg': '#238636',    # Primary button (GitHub green)
            'button_fg': '#ffffff',    # Button text
            'button_hover': '#2ea043', # Button hover
            'secondary_bg': '#373e47', # Secondary buttons
            'secondary_hover': '#424a53',
            'border': '#30363d',       # Borders
            'accent': '#58a6ff',       # Accent color (blue)
            'warning': '#f85149',      # Error/warning
            'success': '#56d364',      # Success
            'muted': '#8b949e',        # Muted text
            'gradient_start': '#0d1117',
            'gradient_end': '#161b22',
            'glow': '#238636',
            'shadow': '#000000'
        }
        
        # Enhanced light theme
        self.light_theme = {
            'bg': '#ffffff',
            'fg': '#24292f', 
            'card_bg': '#f6f8fa',
            'input_bg': '#ffffff',
            'input_fg': '#24292f',
            'button_bg': '#2da44e',
            'button_fg': '#ffffff',
            'button_hover': '#2c974b',
            'secondary_bg': '#f6f8fa',
            'secondary_hover': '#f3f4f6',
            'border': '#d0d7de',
            'accent': '#0969da',
            'warning': '#cf222e',
            'success': '#1a7f37',
            'muted': '#656d76',
            'gradient_start': '#ffffff',
            'gradient_end': '#f6f8fa',
            'glow': '#2da44e',
            'shadow': '#e1e4e8'
        }

    def apply_theme(self, root: tk.Tk, style: ttk.Style, is_dark: bool = True):
        theme = self.dark_theme if is_dark else self.light_theme
        
        # Configure root
        root.configure(bg=theme['bg'])
        
        # Configure ttk styles
        style.theme_use('clam')
        
        # Main frame
        style.configure('Card.TFrame', 
                       background=theme['card_bg'],
                       relief='flat',
                       borderwidth=1)
        
        style.configure('Main.TFrame', background=theme['bg'])
        
        # Labels
        style.configure('TLabel', 
                       background=theme['bg'], 
                       foreground=theme['fg'],
                       font=('Inter', 10))
        
        style.configure('Title.TLabel',
                       background=theme['bg'],
                       foreground=theme['fg'],
                       font=('Inter', 18, 'bold'))
        
        style.configure('Header.TLabel',
                       background=theme['card_bg'],
                       foreground=theme['fg'],
                       font=('Inter', 14, 'bold'))
        
        style.configure('Small.TLabel',
                       background=theme['card_bg'],
                       foreground=theme['muted'],
                       font=('Inter', 9))
        
        # Entry widgets
        style.configure('Modern.TEntry',
                       fieldbackground=theme['input_bg'],
                       foreground=theme['input_fg'],
                       borderwidth=1,
                       relief='solid',
                       insertcolor=theme['fg'])
        
        style.map('Modern.TEntry',
                 focuscolor=[('!focus', theme['border']),
                           ('focus', theme['accent'])])
        
        # Checkbuttons
        style.configure('Modern.TCheckbutton',
                       background=theme['card_bg'],
                       foreground=theme['fg'],
                       focuscolor=theme['accent'])

class AnimatedProgressBar:
    """Custom animated progress bar with glow effect"""
    def __init__(self, parent, width=300, height=8):
        self.parent = parent
        self.width = width
        self.height = height
        
        theme_manager = getattr(parent.master, 'theme_manager', ModernThemeManager())
        is_dark = getattr(parent.master, 'is_dark_mode', True)
        self.theme = theme_manager.dark_theme if is_dark else theme_manager.light_theme
        
        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height + 10,
            bg=self.theme['card_bg'],
            highlightthickness=0
        )
        
        # Background track
        self.track = self.canvas.create_rectangle(
            5, 5, width - 5, height + 5,
            fill=self.theme['border'],
            outline=""
        )
        
        # Progress bar
        self.progress = self.canvas.create_rectangle(
            5, 5, 5, height + 5,
            fill=self.theme['accent'],
            outline=""
        )
        
        # Glow effect
        self.glow = self.canvas.create_rectangle(
            5, 3, 5, height + 7,
            fill=self.theme['glow'],
            outline=""
        )
        
        self.current_progress = 0
        self.target_progress = 0
        self.is_animating = False
    
    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)
    
    def set_progress(self, progress):
        """Set progress with smooth animation"""
        self.target_progress = max(0, min(100, progress))
        if not self.is_animating:
            self.animate_progress()
    
    def animate_progress(self):
        """Animate progress bar smoothly"""
        self.is_animating = True
        
        def step():
            diff = self.target_progress - self.current_progress
            if abs(diff) < 0.5:
                self.current_progress = self.target_progress
                self.is_animating = False
            else:
                self.current_progress += diff * 0.1
            
            # Update visual
            progress_width = (self.current_progress / 100) * (self.width - 10)
            self.canvas.coords(
                self.progress,
                5, 5, 5 + progress_width, self.height + 5
            )
            self.canvas.coords(
                self.glow,
                5, 3, 5 + progress_width, self.height + 7
            )
            
            if self.is_animating:
                self.parent.after(16, step)  # ~60fps
        
        step()

class StatusIndicator:
    """Animated status indicator with pulse effect"""
    def __init__(self, parent):
        self.parent = parent
        
        theme_manager = getattr(parent.master, 'theme_manager', ModernThemeManager())
        is_dark = getattr(parent.master, 'is_dark_mode', True)
        self.theme = theme_manager.dark_theme if is_dark else theme_manager.light_theme
        
        self.canvas = tk.Canvas(
            parent,
            width=20,
            height=20,
            bg=self.theme['card_bg'],
            highlightthickness=0
        )
        
        self.dot = self.canvas.create_oval(
            6, 6, 14, 14,
            fill=self.theme['muted'],
            outline=""
        )
        
        self.pulse_ring = self.canvas.create_oval(
            4, 4, 16, 16,
            fill="",
            outline=self.theme['muted'],
            width=2
        )
        
        self.status = "idle"
        self.animation_id = None
    
    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)
    
    def set_status(self, status):
        """Set status: idle, connecting, success, error"""
        self.status = status
        if self.animation_id:
            self.parent.after_cancel(self.animation_id)
        
        colors = {
            'idle': self.theme['muted'],
            'connecting': self.theme['accent'],
            'success': self.theme['success'],
            'error': self.theme['warning']
        }
        
        color = colors.get(status, self.theme['muted'])
        self.canvas.itemconfig(self.dot, fill=color)
        self.canvas.itemconfig(self.pulse_ring, outline=color)
        
        if status == "connecting":
            self.start_pulse()
        else:
            self.stop_pulse()
    
    def start_pulse(self):
        """Start pulsing animation"""
        def pulse(scale=1.0, direction=1):
            new_scale = scale + (direction * 0.1)
            if new_scale > 1.5:
                new_scale = 1.5
                direction = -1
            elif new_scale < 1.0:
                new_scale = 1.0
                direction = 1
            
            # Update ring size
            center = 10
            radius = 6 * new_scale
            self.canvas.coords(
                self.pulse_ring,
                center - radius, center - radius,
                center + radius, center + radius
            )
            
            if self.status == "connecting":
                self.animation_id = self.parent.after(50, lambda: pulse(new_scale, direction))
        
        pulse()
    
    def stop_pulse(self):
        """Stop pulsing animation"""
        if self.animation_id:
            self.parent.after_cancel(self.animation_id)
            self.animation_id = None
        
        # Reset ring to normal size
        self.canvas.coords(self.pulse_ring, 4, 4, 16, 16)

class FloatingCard:
    """Card with subtle shadow and hover effects"""
    def __init__(self, parent, title=None):
        theme_manager = getattr(parent.master, 'theme_manager', ModernThemeManager())
        is_dark = getattr(parent.master, 'is_dark_mode', True)
        self.theme = theme_manager.dark_theme if is_dark else theme_manager.light_theme
        
        # Shadow frame (offset)
        self.shadow_frame = tk.Frame(
            parent,
            bg=self.theme['shadow'],
            height=2
        )
        
        # Main card frame
        self.frame = tk.Frame(
            parent,
            bg=self.theme['card_bg'],
            relief='flat',
            borderwidth=1,
            highlightbackground=self.theme['border'],
            highlightthickness=1
        )
        
        # Hover effects
        self.frame.bind('<Enter>', self.on_enter)
        self.frame.bind('<Leave>', self.on_leave)
        
        # Title
        if title:
            self.title_label = tk.Label(
                self.frame,
                text=title,
                bg=self.theme['card_bg'],
                fg=self.theme['fg'],
                font=('Inter', 14, 'bold')
            )
            self.title_label.pack(anchor=tk.W, padx=20, pady=(20, 10))
    
    def pack(self, **kwargs):
        self.shadow_frame.pack(**kwargs)
        self.shadow_frame.pack_configure(pady=(kwargs.get('pady', (0, 0))[0] + 2, 0))
        self.frame.pack(**kwargs)
        return self
    
    def on_enter(self, event):
        """Hover effect"""
        self.frame.configure(highlightcolor=self.theme['accent'])
    
    def on_leave(self, event):
        """Remove hover effect"""
        self.frame.configure(highlightcolor=self.theme['border'])
    
    def update_theme(self, new_theme):
        """Update card theme"""
        self.theme = new_theme
        self.shadow_frame.configure(bg=new_theme['shadow'])
        self.frame.configure(
            bg=new_theme['card_bg'],
            highlightbackground=new_theme['border']
        )
        if hasattr(self, 'title_label'):
            self.title_label.configure(
                bg=new_theme['card_bg'],
                fg=new_theme['fg']
            )

class ModernButton:
    """Custom modern button implementation"""
    def __init__(self, parent, text, command, style_type="primary", width=None):
        self.parent = parent
        self.command = command
        self.style_type = style_type
        self.text = text
        
        # Store reference to main GUI for theme access
        self.gui_ref = None
        if hasattr(parent, 'master') and hasattr(parent.master, 'theme_manager'):
            self.gui_ref = parent.master
        elif hasattr(parent, 'theme_manager'):
            self.gui_ref = parent
        
        # Get initial theme
        theme = self.get_current_theme()
        
        # Get colors for current style
        colors = self.get_style_colors(theme)
        bg_color, hover_color, text_color = colors
        
        # Create button
        self.button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=text_color,
            activebackground=hover_color,
            activeforeground=text_color,
            relief='flat',
            borderwidth=0,
            font=('Inter', 10, 'bold' if style_type == "primary" else 'normal'),
            cursor='hand2',
            padx=20,
            pady=8,
            width=width
        )
        
        # Store original colors
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        # Add enhanced hover effects with animation
        self.button.bind('<Enter>', self.on_enter)
        self.button.bind('<Leave>', self.on_leave)
        self.button.bind('<Button-1>', self.on_click)
        
        # Animation state
        self.is_animating = False
    
    def pack(self, **kwargs):
        return self.button.pack(**kwargs)
    
    def configure(self, **kwargs):
        return self.button.configure(**kwargs)
    
    def on_enter(self, event):
        """Enhanced hover effect with smooth transition"""
        if not self.is_animating:
            self.animate_color_transition(self.bg_color, self.hover_color)
    
    def on_leave(self, event):
        """Remove hover effect with smooth transition"""
        if not self.is_animating:
            self.animate_color_transition(self.hover_color, self.bg_color)
    
    def on_click(self, event):
        """Click effect with brief color change"""
        original_color = self.button.cget('bg')
        darker_color = self.darken_color(original_color)
        self.button.configure(bg=darker_color)
        self.parent.after(100, lambda: self.button.configure(bg=original_color))
    
    def darken_color(self, color):
        """Darken a color for click effect"""
        try:
            # Convert hex to RGB, darken, and convert back
            color = color.lstrip('#')
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            darkened = tuple(max(0, int(c * 0.8)) for c in rgb)
            return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"
        except:
            return color
    
    def animate_color_transition(self, start_color, end_color, steps=5):
        """Smooth color transition animation"""
        self.is_animating = True
        
        def step(current_step):
            if current_step >= steps:
                self.button.configure(bg=end_color)
                self.is_animating = False
                return
            
            # Interpolate between colors
            progress = current_step / steps
            interpolated_color = self.interpolate_color(start_color, end_color, progress)
            self.button.configure(bg=interpolated_color)
            
            self.parent.after(16, lambda: step(current_step + 1))
        
        step(0)
    
    def interpolate_color(self, color1, color2, progress):
        """Interpolate between two hex colors"""
        try:
            # Parse hex colors
            c1 = color1.lstrip('#')
            c2 = color2.lstrip('#')
            
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
            
            # Interpolate
            r = int(r1 + (r2 - r1) * progress)
            g = int(g1 + (g2 - g1) * progress)
            b = int(b1 + (b2 - b1) * progress)
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color1
    
    def get_current_theme(self):
        """Get current theme from GUI reference"""
        if self.gui_ref and hasattr(self.gui_ref, 'get_theme'):
            return self.gui_ref.get_theme()
        else:
            # Fallback to dark theme
            return ModernThemeManager().dark_theme
    
    def get_style_colors(self, theme):
        """Get colors for current button style"""
        if self.style_type == "primary":
            return theme['button_bg'], theme['button_hover'], theme['button_fg']
        elif self.style_type == "secondary":
            return theme['secondary_bg'], theme['secondary_hover'], theme['fg']
        elif self.style_type == "tab_active":
            return theme['accent'], theme['accent'], theme['button_fg']
        else:  # tab_inactive
            return theme['secondary_bg'], theme['secondary_hover'], theme['fg']
    
    def update_theme(self):
        """Update button colors based on current theme"""
        theme = self.get_current_theme()
        bg_color, hover_color, text_color = self.get_style_colors(theme)
        
        # Update stored colors
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        # Update button appearance
        self.button.configure(
            bg=bg_color,
            fg=text_color,
            activebackground=hover_color,
            activeforeground=text_color
        )

class ModernGUI:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.theme_manager = ModernThemeManager()
        
        # Initialize window
        self.root = tk.Tk()
        self.root.title("SourceStalker V3 Configuration")
        self.root.geometry("950x1100")
        self.root.minsize(800, 900)  # Set minimum size
        self.root.resizable(True, True)
        
        # Theme state
        self.is_dark_mode = True
        self.style = ttk.Style()
        
        # Region mappings
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
        
        # UI state
        self.show_advanced = tk.BooleanVar(value=False)
        self.current_page = "main"
        
        # Store button references for theme updates
        self.modern_buttons = []
        self.floating_cards = []
        
        # Initialize UI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the main GUI with modern styling"""
        # Apply theme
        self.theme_manager.apply_theme(self.root, self.style, self.is_dark_mode)
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.get_theme()['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header section
        self.create_header(main_container)
        
        # Navigation tabs
        self.create_navigation(main_container)
        
        # Content area
        self.content_frame = tk.Frame(main_container, bg=self.get_theme()['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Create page frames
        self.main_page = self.create_main_page()
        self.messages_page = self.create_messages_page()
        
        # Show default page
        self.show_main_page()
        
        # Load existing config
        self.load_existing_config()
    
    def get_theme(self):
        """Get current theme colors"""
        return self.theme_manager.dark_theme if self.is_dark_mode else self.theme_manager.light_theme
    
    def create_header(self, parent):
        """Create modern header section"""
        theme = self.get_theme()
        
        header_frame = tk.Frame(parent, bg=theme['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Title with logo/icon placeholder
        title_frame = tk.Frame(header_frame, bg=theme['bg'])
        title_frame.pack(side=tk.LEFT)
        
        # Icon placeholder (you could add an actual icon here)
        icon_label = tk.Label(
            title_frame,
            text="🎯",
            bg=theme['bg'],
            fg=theme['accent'],
            font=('Inter', 24)
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Title text
        title_label = tk.Label(
            title_frame,
            text="SourceStalker Configuration",
            bg=theme['bg'],
            fg=theme['fg'],
            font=('Inter', 20, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        # Theme toggle button (modern toggle)
        self.theme_btn = tk.Button(
            header_frame,
            text="🌙" if self.is_dark_mode else "☀️",
            command=self.toggle_theme,
            bg=theme['secondary_bg'],
            fg=theme['fg'],
            relief='flat',
            borderwidth=0,
            font=('Inter', 16),
            cursor='hand2',
            width=3,
            height=1
        )
        self.theme_btn.pack(side=tk.RIGHT)
    
    def create_navigation(self, parent):
        """Create modern tab navigation"""
        theme = self.get_theme()
        
        nav_frame = tk.Frame(parent, bg=theme['bg'])
        nav_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Tab buttons with modern styling
        self.main_tab = ModernButton(
            nav_frame, "Main Settings", self.show_main_page, "tab_active"
        )
        self.main_tab.pack(side=tk.LEFT, padx=(0, 10))
        self.modern_buttons.append(self.main_tab)
        
        self.messages_tab = ModernButton(
            nav_frame, "Message Templates", self.show_messages_page, "tab_inactive"
        )
        self.messages_tab.pack(side=tk.LEFT)
        self.modern_buttons.append(self.messages_tab)
    
    def create_card(self, parent, title=None):
        """Create a modern floating card container"""
        card = FloatingCard(parent, title)
        self.floating_cards.append(card)
        return card
    
    def create_modern_entry(self, parent, placeholder="", show=None):
        """Create a modern styled entry widget"""
        theme = self.get_theme()
        
        entry = tk.Entry(
            parent,
            bg=theme['input_bg'],
            fg=theme['input_fg'],
            insertbackground=theme['fg'],
            relief='flat',
            borderwidth=1,
            highlightbackground=theme['border'],
            highlightcolor=theme['accent'],
            highlightthickness=1,
            font=('Inter', 11),
            show=show
        )
        
        # Add placeholder functionality
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind('<FocusIn>', lambda e: self.on_entry_click(entry, placeholder))
            entry.bind('<FocusOut>', lambda e: self.on_focusout(entry, placeholder))
        
        return entry
    
    def on_entry_click(self, entry, placeholder):
        """Handle entry focus in"""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.configure(fg=self.get_theme()['input_fg'])
    
    def on_focusout(self, entry, placeholder):
        """Handle entry focus out"""
        if not entry.get():
            entry.insert(0, placeholder)
            entry.configure(fg=self.get_theme()['muted'])
    
    def create_main_page(self):
        """Create the main settings page"""
        page_frame = tk.Frame(self.content_frame, bg=self.get_theme()['bg'])
        
        # Discord Settings Card
        discord_card_container = self.create_card(page_frame, "🔷 Discord Configuration")
        discord_card_container.pack(fill=tk.X, pady=(0, 20))
        
        # Discord form
        form_frame = tk.Frame(discord_card_container.frame, bg=self.get_theme()['card_bg'])
        form_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Bot Token
        tk.Label(form_frame, text="Bot Token", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(10, 5))
        self.discord_token = self.create_modern_entry(form_frame, show="•")
        self.discord_token.pack(fill=tk.X, pady=(0, 15))
        
        # Channel ID
        tk.Label(form_frame, text="Channel ID", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.channel_id = self.create_modern_entry(form_frame)
        self.channel_id.pack(fill=tk.X, pady=(0, 10))
        
        # Riot Settings Card
        riot_card_container = self.create_card(page_frame, "⚔️ Riot API Configuration")
        riot_card_container.pack(fill=tk.X, pady=(0, 20))
        
        # Riot form
        riot_form = tk.Frame(riot_card_container.frame, bg=self.get_theme()['card_bg'])
        riot_form.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # API Key
        tk.Label(riot_form, text="API Key", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(10, 5))
        self.riot_api_key = self.create_modern_entry(riot_form, show="•")
        self.riot_api_key.pack(fill=tk.X, pady=(0, 15))
        
        # Summoner Name
        tk.Label(riot_form, text="Summoner Name", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.summoner_name = self.create_modern_entry(riot_form)
        self.summoner_name.pack(fill=tk.X, pady=(0, 15))
        
        # Summoner Tag
        tk.Label(riot_form, text="Summoner Tag", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.summoner_tag = self.create_modern_entry(riot_form)
        self.summoner_tag.pack(fill=tk.X, pady=(0, 15))
        
        # Region
        tk.Label(riot_form, text="Region", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(0, 5))
        
        self.region_var = tk.StringVar()
        region_options = [f"{code} - {data[1]}" for code, data in sorted(self.region_mappings.items())]
        self.region_dropdown = ttk.Combobox(
            riot_form,
            textvariable=self.region_var,
            values=region_options,
            state='readonly',
            font=('Inter', 11)
        )
        self.region_dropdown.pack(fill=tk.X, pady=(0, 10))
        self.region_var.set("NA1 - North America")
        
        # Advanced Settings Card
        self.create_advanced_section(page_frame)
        
        # Action Buttons
        self.create_action_buttons(page_frame)
        
        return page_frame
    
    def create_advanced_section(self, parent):
        """Create advanced settings section"""
        advanced_card_container = self.create_card(parent, "⚙️ Advanced Settings")
        advanced_card_container.pack(fill=tk.X, pady=(0, 20))
        
        # Toggle checkbox
        toggle_frame = tk.Frame(advanced_card_container.frame, bg=self.get_theme()['card_bg'])
        toggle_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        advanced_toggle = tk.Checkbutton(
            toggle_frame,
            text="Show Advanced Settings",
            variable=self.show_advanced,
            command=self.toggle_advanced,
            bg=self.get_theme()['card_bg'],
            fg=self.get_theme()['fg'],
            selectcolor=self.get_theme()['input_bg'],
            activebackground=self.get_theme()['card_bg'],
            activeforeground=self.get_theme()['fg'],
            font=('Inter', 10)
        )
        advanced_toggle.pack(anchor=tk.W, pady=(10, 10))
        
        # Advanced content (initially hidden)
        self.advanced_content = tk.Frame(advanced_card_container.frame, bg=self.get_theme()['card_bg'])
        
        tk.Label(self.advanced_content, text="Database Path", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, padx=20, pady=(0, 5))
        self.db_path = self.create_modern_entry(self.advanced_content)
        self.db_path.pack(fill=tk.X, padx=20, pady=(0, 20))
        self.db_path.insert(0, "/app/rank_tracker.db")
    
    def toggle_advanced(self):
        """Toggle advanced settings visibility"""
        if self.show_advanced.get():
            self.advanced_content.pack(fill=tk.X)
        else:
            self.advanced_content.pack_forget()
    
    def create_action_buttons(self, parent):
        """Create action buttons"""
        button_frame = tk.Frame(parent, bg=self.get_theme()['bg'])
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Test Connection button
        self.test_btn = ModernButton(
            button_frame, "Test Connection", self.test_connection, "secondary"
        )
        self.test_btn.pack(side=tk.RIGHT, padx=(10, 0))
        self.modern_buttons.append(self.test_btn)
        
        # Save button
        self.save_btn = ModernButton(
            button_frame, "Save Configuration", self.save_config, "primary"
        )
        self.save_btn.pack(side=tk.RIGHT)
        self.modern_buttons.append(self.save_btn)
    
    def create_messages_page(self):
        """Create the message templates page"""
        page_frame = tk.Frame(self.content_frame, bg=self.get_theme()['bg'])
        
        # Messages Card
        messages_card_container = self.create_card(page_frame, "💬 Message Templates")
        messages_card_container.pack(fill=tk.X, pady=(0, 20))
        
        form_frame = tk.Frame(messages_card_container.frame, bg=self.get_theme()['card_bg'])
        form_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Nickname
        tk.Label(form_frame, text="Custom Nickname (optional)", bg=self.get_theme()['card_bg'], 
                fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(10, 5))
        self.nickname = self.create_modern_entry(form_frame)
        self.nickname.pack(fill=tk.X, pady=(0, 20))
        
        # Message templates
        templates = [
            ("Game Start Message", "game_start", "{summoner_name} is in a game now! Monitoring..."),
            ("Victory Message", "game_win", "{summoner_name} got carried!"),
            ("Defeat Message", "game_loss", "{summoner_name} threw the game!"),
            ("Death Count Message", "death_count", "Amount of times {summoner_name} died: {deaths}"),
            ("LP Gain Message", "lp_gain", "{summoner_name} gained {lp_change} LP in {queue_type}!"),
            ("LP Loss Message", "lp_loss", "{summoner_name} lost {lp_change} LP in {queue_type}!")
        ]
        
        self.message_entries = {}
        for label, key, default in templates:
            tk.Label(form_frame, text=label, bg=self.get_theme()['card_bg'], 
                    fg=self.get_theme()['fg'], font=('Inter', 11)).pack(anchor=tk.W, pady=(15, 5))
            
            entry = self.create_modern_entry(form_frame)
            entry.insert(0, default)
            entry.pack(fill=tk.X, pady=(0, 5))
            self.message_entries[key] = entry
            
            # Helper text
            helper = tk.Label(
                form_frame,
                text="Variables: {summoner_name}, {deaths}, {lp_change}, {queue_type}",
                bg=self.get_theme()['card_bg'],
                fg=self.get_theme()['muted'],
                font=('Inter', 9)
            )
            helper.pack(anchor=tk.W, pady=(0, 10))
        
        # Save button for messages
        save_frame = tk.Frame(page_frame, bg=self.get_theme()['bg'])
        save_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.message_save_btn = ModernButton(
            save_frame, "Save Message Templates", self.save_config, "primary"
        )
        self.message_save_btn.pack(side=tk.RIGHT)
        self.modern_buttons.append(self.message_save_btn)
        
        return page_frame
    
    def show_main_page(self):
        """Switch to main settings page"""
        self.messages_page.pack_forget()
        self.main_page.pack(fill=tk.BOTH, expand=True)
        self.current_page = "main"
        
        # Update tab styling
        self.main_tab.configure(bg=self.get_theme()['accent'])
        self.messages_tab.configure(bg=self.get_theme()['secondary_bg'])
    
    def show_messages_page(self):
        """Switch to messages page"""
        self.main_page.pack_forget()
        self.messages_page.pack(fill=tk.BOTH, expand=True)
        self.current_page = "messages"
        
        # Update tab styling
        self.messages_tab.configure(bg=self.get_theme()['accent'])
        self.main_tab.configure(bg=self.get_theme()['secondary_bg'])
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.is_dark_mode = not self.is_dark_mode
        
        # Apply new theme
        self.theme_manager.apply_theme(self.root, self.style, self.is_dark_mode)
        
        # Update theme button text
        self.theme_btn.configure(
            text="🌙" if self.is_dark_mode else "☀️",
            bg=self.get_theme()['secondary_bg'],
            fg=self.get_theme()['fg']
        )
        
        # Update all visual elements recursively
        self.update_all_widgets(self.root)
        
        # Update all ModernButton instances
        for button in self.modern_buttons:
            button.update_theme()
        
        # Update all FloatingCard instances
        current_theme = self.get_theme()
        for card in self.floating_cards:
            card.update_theme(current_theme)
    
    def update_all_widgets(self, widget):
        """Recursively update all widgets to match current theme"""
        theme = self.get_theme()
        
        # Update the widget based on its type
        widget_class = widget.winfo_class()
        
        try:
            if widget_class in ['Frame', 'Toplevel']:
                widget.configure(bg=theme['bg'])
            elif widget_class == 'Label':
                # Determine if it's a card label or main label
                current_bg = widget.cget('bg')
                if current_bg in [self.theme_manager.dark_theme['card_bg'], self.theme_manager.light_theme['card_bg']]:
                    widget.configure(bg=theme['card_bg'], fg=theme['fg'])
                else:
                    widget.configure(bg=theme['bg'], fg=theme['fg'])
            elif widget_class == 'Entry':
                widget.configure(
                    bg=theme['input_bg'],
                    fg=theme['input_fg'],
                    insertbackground=theme['fg']
                )
            elif widget_class == 'Button':
                # Skip our custom buttons - they handle their own theme updates
                if not hasattr(widget, 'master') or 'ModernButton' not in str(type(widget.master)):
                    widget.configure(
                        bg=theme['secondary_bg'],
                        fg=theme['fg'],
                        activebackground=theme['secondary_hover'],
                        activeforeground=theme['fg']
                    )
            elif widget_class == 'Checkbutton':
                widget.configure(
                    bg=theme['card_bg'],
                    fg=theme['fg'],
                    selectcolor=theme['input_bg'],
                    activebackground=theme['card_bg'],
                    activeforeground=theme['fg']
                )
            elif widget_class == 'Text':
                widget.configure(
                    bg=theme['input_bg'],
                    fg=theme['input_fg'],
                    insertbackground=theme['fg']
                )
            elif widget_class == 'Canvas':
                widget.configure(bg=theme['card_bg'])
        except tk.TclError:
            # Some widgets might not support certain configurations
            pass
        
        # Update child widgets recursively
        for child in widget.winfo_children():
            self.update_all_widgets(child)
    
    def load_existing_config(self):
        """Load existing configuration"""
        config = self.config_manager.config
        
        # Discord settings
        if config.discord.bot_token:
            self.discord_token.delete(0, tk.END)
            self.discord_token.insert(0, config.discord.bot_token)
        
        if config.discord.channel_id:
            self.channel_id.delete(0, tk.END)
            self.channel_id.insert(0, config.discord.channel_id)
        
        # Riot settings
        if config.riot.api_key:
            self.riot_api_key.delete(0, tk.END)
            self.riot_api_key.insert(0, config.riot.api_key)
        
        if config.riot.summoner_name:
            self.summoner_name.delete(0, tk.END)
            self.summoner_name.insert(0, config.riot.summoner_name)
        
        if config.riot.summoner_tag:
            self.summoner_tag.delete(0, tk.END)
            self.summoner_tag.insert(0, config.riot.summoner_tag)
        
        # Region
        if hasattr(config.riot, 'region') and config.riot.region in self.region_mappings:
            region_display = f"{config.riot.region} - {self.region_mappings[config.riot.region][1]}"
            self.region_var.set(region_display)
        
        # Advanced settings
        if config.database.path:
            self.db_path.delete(0, tk.END)
            self.db_path.insert(0, config.database.path)
        
        # Message templates
        if hasattr(config, 'messages') and config.messages:
            if config.messages.nickname:
                self.nickname.delete(0, tk.END)
                self.nickname.insert(0, config.messages.nickname)
            
            for key in self.message_entries:
                if hasattr(config.messages, key):
                    self.message_entries[key].delete(0, tk.END)
                    self.message_entries[key].insert(0, getattr(config.messages, key))
    
    def save_config(self):
        """Save configuration with validation"""
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
                    'summoner_id': "",
                    'puuid': ""
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
            
            # Validation
            if not config['discord']['bot_token']:
                messagebox.showerror("Validation Error", "Discord bot token is required")
                return
            if not config['discord']['channel_id']:
                messagebox.showerror("Validation Error", "Discord channel ID is required")
                return
            if not config['riot']['api_key']:
                messagebox.showerror("Validation Error", "Riot API key is required")
                return
            if not config['riot']['summoner_name']:
                messagebox.showerror("Validation Error", "Summoner name is required")
                return
            
            # Save configuration
            self.config_manager.save_config_dict(config)
            messagebox.showinfo("Success", "Configuration saved successfully! ✅")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
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
        
        if not all([api_key, summoner_name, summoner_tag, region]):
            return False, "All Riot API fields are required"
        
        try:
            platform = self.region_mappings[region][0]  # Get platform from mappings
            
            headers = {'X-Riot-Token': api_key}
            async with aiohttp.ClientSession() as session:
                # Use the current recommended endpoint
                url = f'https://{platform}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{summoner_tag}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 403:
                        return False, "Invalid API key. Please check your Riot API key."
                    elif response.status == 404:
                        return False, f"Could not find account '{summoner_name}#{summoner_tag}'. Please check the name and tag."
                    elif response.status != 200:
                        text = await response.text()
                        return False, f"API request failed with status {response.status}. Response: {text}"
                    
                    data = await response.json()
                    
                    if not data.get('puuid'):
                        return False, "Invalid response from Riot API. Missing PUUID in response."
                    
                    # If successful, optionally test fetching summoner data as well
                    summoner_url = f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{data["puuid"]}'
                    
                    async with session.get(summoner_url, headers=headers) as summoner_response:
                        if summoner_response.status == 200:
                            return True, f"Successfully found account '{summoner_name}#{summoner_tag}'!"
                        else:
                            # Even if this fails, the account lookup succeeded
                            return True, f"Found Riot account, but couldn't fetch summoner details."
                        
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def test_connection(self):
        """Enhanced connection test with animated progress and status indicators"""
        # Create test dialog
        test_dialog = tk.Toplevel(self.root)
        test_dialog.title("Connection Test")
        test_dialog.geometry("450x400")
        test_dialog.configure(bg=self.get_theme()['bg'])
        test_dialog.transient(self.root)
        test_dialog.grab_set()
        
        # Center the dialog
        test_dialog.update_idletasks()
        x = (test_dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (test_dialog.winfo_screenheight() // 2) - (400 // 2)
        test_dialog.geometry(f"450x400+{x}+{y}")
        
        # Title
        title_label = tk.Label(
            test_dialog,
            text="🔍 Connection Test",
            bg=self.get_theme()['bg'],
            fg=self.get_theme()['fg'],
            font=('Inter', 16, 'bold')
        )
        title_label.pack(pady=(20, 30))
        
        # Progress bar
        progress_bar = AnimatedProgressBar(test_dialog, width=300)
        progress_bar.pack(pady=(0, 20))
        
        # Status indicators frame
        status_frame = tk.Frame(test_dialog, bg=self.get_theme()['bg'])
        status_frame.pack(fill=tk.X, padx=40, pady=(0, 20))
        
        # Discord status
        discord_frame = tk.Frame(status_frame, bg=self.get_theme()['bg'])
        discord_frame.pack(fill=tk.X, pady=(0, 10))
        
        discord_indicator = StatusIndicator(discord_frame)
        discord_indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        discord_label = tk.Label(
            discord_frame,
            text="Discord Connection",
            bg=self.get_theme()['bg'],
            fg=self.get_theme()['fg'],
            font=('Inter', 11)
        )
        discord_label.pack(side=tk.LEFT)
        
        discord_result = tk.Label(
            discord_frame,
            text="Waiting...",
            bg=self.get_theme()['bg'],
            fg=self.get_theme()['muted'],
            font=('Inter', 10)
        )
        discord_result.pack(side=tk.RIGHT)
        
        # Riot status
        riot_frame = tk.Frame(status_frame, bg=self.get_theme()['bg'])
        riot_frame.pack(fill=tk.X, pady=(0, 10))
        
        riot_indicator = StatusIndicator(riot_frame)
        riot_indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        riot_label = tk.Label(
            riot_frame,
            text="Riot API Connection",
            bg=self.get_theme()['bg'],
            fg=self.get_theme()['fg'],
            font=('Inter', 11)
        )
        riot_label.pack(side=tk.LEFT)
        
        riot_result = tk.Label(
            riot_frame,
            text="Waiting...",
            bg=self.get_theme()['bg'],
            fg=self.get_theme()['muted'],
            font=('Inter', 10)
        )
        riot_result.pack(side=tk.RIGHT)
        
        # Close button (initially hidden)
        close_btn = ModernButton(
            test_dialog, "Close", test_dialog.destroy, "primary"
        )
        
        async def run_tests():
            """Run connection tests with animated feedback"""
            try:
                # Start progress
                progress_bar.set_progress(10)
                
                # Test Discord
                discord_indicator.set_status("connecting")
                discord_result.configure(text="Testing...", fg=self.get_theme()['accent'])
                progress_bar.set_progress(30)
                
                discord_success, discord_msg = await self.test_discord_connection()
                progress_bar.set_progress(50)
                
                if discord_success:
                    discord_indicator.set_status("success")
                    discord_result.configure(text="✅ Connected", fg=self.get_theme()['success'])
                else:
                    discord_indicator.set_status("error")
                    discord_result.configure(text="❌ Failed", fg=self.get_theme()['warning'])
                
                # Small delay for visual effect
                await asyncio.sleep(0.5)
                
                # Test Riot API
                riot_indicator.set_status("connecting")
                riot_result.configure(text="Testing...", fg=self.get_theme()['accent'])
                progress_bar.set_progress(70)
                
                riot_success, riot_msg = await self.test_riot_connection()
                progress_bar.set_progress(100)
                
                if riot_success:
                    riot_indicator.set_status("success")
                    riot_result.configure(text="✅ Connected", fg=self.get_theme()['success'])
                else:
                    riot_indicator.set_status("error")
                    riot_result.configure(text="❌ Failed", fg=self.get_theme()['warning'])
                
                # Show detailed results
                detailed_message = f"Discord: {discord_msg}\n\nRiot API: {riot_msg}"
                
                # Add results text area
                results_frame = tk.Frame(test_dialog, bg=self.get_theme()['bg'])
                results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 0))
                
                results_text = tk.Text(
                    results_frame,
                    bg=self.get_theme()['input_bg'],
                    fg=self.get_theme()['input_fg'],
                    font=('Inter', 9),
                    height=4,
                    wrap=tk.WORD,
                    relief='flat',
                    borderwidth=1,
                    highlightbackground=self.get_theme()['border'],
                    highlightthickness=1
                )
                results_text.pack(fill=tk.BOTH, expand=True)
                results_text.insert(tk.END, detailed_message)
                results_text.configure(state=tk.DISABLED)
                
                # Show close button
                close_btn.pack(pady=(15, 20))
                
            except Exception as e:
                # Handle any errors
                discord_indicator.set_status("error")
                riot_indicator.set_status("error")
                discord_result.configure(text="❌ Error", fg=self.get_theme()['warning'])
                riot_result.configure(text="❌ Error", fg=self.get_theme()['warning'])
                progress_bar.set_progress(100)
                close_btn.pack(pady=(15, 20))
                
                messagebox.showerror("Error", f"Connection test failed: {str(e)}")
        
        def run_async_tests():
            """Run async tests in thread"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_tests())
            finally:
                loop.close()
        
        # Start tests in background thread
        threading.Thread(target=run_async_tests, daemon=True).start()


def launch_gui(config_manager):
    """Launch the enhanced GUI"""
    gui = ModernGUI(config_manager)
    gui.root.mainloop()