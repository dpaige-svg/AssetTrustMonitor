#!/usr/bin/env python3
"""
Custom Title Bar Component

Reusable title bar for windows with drag functionality, buttons, and version dropdown.
"""

import tkinter as tk
from tkinter import ttk
import threading
import requests
from PIL import Image, ImageTk
import os
import platform
from .system_tray import SystemTray


class TitleBar:
    """Custom title bar with drag, buttons, and optional version dropdown"""
    
    def __init__(self, parent_window, config, 
                 title_text=None,
                 show_icon=True, 
                 show_version_dropdown=False,
                 show_asset_count=False,
                 show_server_status=False,
                 show_debug=False,
                 show_toggle=False,
                 show_minimize=True,
                 show_close=True,
                 on_close=None,
                 on_minimize=None,
                 on_debug=None,
                 on_toggle=None,
                 on_version_change=None,
                 studio_manager=None,
                 rojo_server=None,
                 update_manager=None,
                 file_monitor=None):
        """
        Initialize the title bar
        
        Args:
            parent_window: The tkinter window to attach to
            config: Config instance for styling
            title_text: Optional text to display in title bar
            show_icon: Show the app icon
            show_version_dropdown: Show Rojo version dropdown
            show_asset_count: Show asset count in title bar
            show_server_status: Show server status in title bar
            show_debug: Show debug button
            show_toggle: Show toggle button for main window
            show_minimize: Show minimize button
            show_close: Show close button
            on_close: Callback for close button
            on_minimize: Callback for minimize button
            on_debug: Callback for debug button
            on_toggle: Callback for toggle button
            on_version_change: Callback for version change (receives version string)
            studio_manager: StudioManager instance for version changes
            rojo_server: RojoServer instance for version changes
            update_manager: UpdateManager instance for version changes
            file_monitor: FileMonitor instance for asset count updates
        """
        self.window = parent_window
        self.config = config
        self.title_text = title_text
        self.on_close_callback = on_close
        self.on_minimize_callback = on_minimize
        self.on_debug_callback = on_debug
        self.on_toggle_callback = on_toggle
        self.on_version_change_callback = on_version_change
        
        # Manager dependencies for version changes
        self.studio_manager = studio_manager
        self.rojo_server = rojo_server
        self.update_manager = update_manager
        self.file_monitor = file_monitor
        
        # UI components
        self.title_bar_frame = None
        self.version_combo = None
        self.asset_count_label = None
        self.server_status_label = None
        self.toggle_button = None
        self.toggle_state_visible = False  # Track if main window is visible
        self.current_version = None
        self.rojo_versions = []
        
        # Get the emoji conversion utility
        utils = getattr(self.config, "utils", None)
        if utils is None:
            from src.core.utils import Utils
            utils = Utils()

        self._utils = utils  # Store for use in icon methods

        # Platform-specific font and layout settings
        self.is_macos = platform.system() == "Darwin"
        if self.is_macos:
            self.ui_font = ("SF Pro Display", 12)
            self.badge_font = ("SF Pro Display", 9, "bold")
            self.small_font = ("SF Pro Display", 9)
            self.title_font = ("SF Pro Display", 11, "bold")
        else:
            self.ui_font = ("Segoe UI", 10)
            self.badge_font = ("Segoe UI", 7, "bold")
            self.small_font = ("Segoe UI", 7)
            self.title_font = ("Segoe UI", 9, "bold")

        # Create the title bar
        self._create_title_bar(show_icon, show_version_dropdown, show_asset_count, show_server_status, show_debug, 
                              show_toggle, show_minimize, show_close)
    
    def _create_title_bar(self, show_icon, show_version_dropdown, show_asset_count, show_server_status,
                         show_debug, show_toggle, show_minimize, show_close):
        """Create the title bar with all components"""
        # Make window borderless
        try:
            self.window.overrideredirect(1)
        except Exception:
            pass
        
        # Title bar frame
        self.title_bar_frame = tk.Frame(self.window, bg=self.config.title_bar_bg, 
                                       relief='flat', bd=1)
        self.title_bar_frame.pack(fill='x')
        
        # Setup dragging
        self._setup_drag_functionality()
        
        # Left section: Icon and title
        self._create_left_section(show_icon)
        
        # Center section: Status indicators (asset count, server status)
        self._create_center_section(show_asset_count, show_server_status)
        
        # Right section: Controls (version dropdown, buttons)
        self._create_right_section(show_version_dropdown, show_debug, show_toggle, show_minimize, show_close)

    def _create_left_section(self, show_icon):
        """Create the left section of the title bar (icon + title)"""
        left_frame = tk.Frame(self.title_bar_frame, bg=self.config.title_bar_bg)
        left_frame.pack(side='left', padx=(10, 20), pady=0)  # More space after left section
        
        # Add icon if requested
        if show_icon:
            self._add_icon_to_section(left_frame)
            
        # Add title text if requested
        if self.title_text:
            self._add_title_text_to_section(left_frame)

    def _create_center_section(self, show_asset_count, show_server_status):
        """Create the center section of the title bar (status indicators)"""
        center_frame = tk.Frame(self.title_bar_frame, bg=self.config.title_bar_bg)
        center_frame.pack(side='left', padx=(0, 20), pady=0)  # Space before right section
        
        # Add asset count if requested
        if show_asset_count:
            self._add_asset_count_to_section(center_frame)

        # Add server status if requested
        if show_server_status:
            self._add_server_status_to_section(center_frame)

    def _create_right_section(self, show_version_dropdown, show_debug, show_toggle, show_minimize, show_close):
        """Create the right section of the title bar (controls)"""
        right_frame = tk.Frame(self.title_bar_frame, bg=self.config.title_bar_bg)
        right_frame.pack(side='right', padx=(0, 0), pady=0)
        
        # Add version dropdown if requested
        if show_version_dropdown:
            self._add_version_dropdown_to_section(right_frame)
        
        # Add debug button if requested
        if show_debug:
            self._add_debug_button_to_section(right_frame)
        
        # Add minimize button if requested
        if show_minimize:
            self._add_minimize_button_to_section(right_frame)
        
        # Add close button if requested
        if show_close:
            self._add_close_button_to_section(right_frame)
        
        # Add toggle button if requested
        if show_toggle:
            self._add_toggle_button_to_section(right_frame)
    

    def _start_move(self, event):
        """Start moving the window"""
        self.window.x = event.x
        self.window.y = event.y
    
    def _stop_move(self, event):
        """Stop moving the window"""
        self.window.x = None
        self.window.y = None
    
    def _on_move(self, event):
        """Handle window movement"""
        if hasattr(self.window, 'x') and self.window.x is not None:
            deltax = event.x - self.window.x
            deltay = event.y - self.window.y
            x = self.window.winfo_x() + deltax
            y = self.window.winfo_y() + deltay
            self.window.geometry(f"+{x}+{y}")

    def _setup_drag_functionality(self):
        """Setup window dragging by title bar"""
        # Bind dragging to title bar
        self.title_bar_frame.bind("<ButtonPress-1>", self._start_move)
        self.title_bar_frame.bind("<ButtonRelease-1>", self._stop_move)
        self.title_bar_frame.bind("<B1-Motion>", self._on_move)
    
    def _add_icon_to_section(self, parent_frame):
        """Add app icon to title bar section"""
        try:
            # Create icon image using SystemTray's method
            # We pass self, but the method doesn't use it, so it's safe
            tray_pil_image = SystemTray._create_icon_image(self)
            
            try:
                tray_pil_image = tray_pil_image.resize((20, 20), Image.Resampling.LANCZOS)
            except Exception:
                tray_pil_image = tray_pil_image.resize((20, 20), Image.LANCZOS)
            
            self.title_icon = ImageTk.PhotoImage(tray_pil_image)
            title_label = tk.Label(parent_frame, image=self.title_icon,
                                 bg=self.config.title_bar_bg, fg='white')
            title_label.image = self.title_icon
            title_label.pack(side='left', padx=(0, 8), pady=0)
            
            # Make icon draggable too
            title_label.bind("<ButtonPress-1>", self._start_move)
            title_label.bind("<ButtonRelease-1>", self._stop_move)
            title_label.bind("<B1-Motion>", self._on_move)
            
        except Exception as e:
            print(f"Could not load title bar icon: {e}")

    def _add_title_text_to_section(self, parent_frame):
        """Add title text to title bar section"""
        title_label = tk.Label(parent_frame, text=self.title_text,
                             bg=self.config.title_bar_bg, fg='white', font=self.title_font)
        title_label.pack(side='left', padx=(0, 0), pady=0)
        
        # Make title text draggable too
        title_label.bind("<ButtonPress-1>", self._start_move)
        title_label.bind("<ButtonRelease-1>", self._stop_move)
        title_label.bind("<B1-Motion>", self._on_move)
    
    def _add_version_dropdown_to_section(self, parent_frame):
        """Add Rojo version dropdown to title bar section"""
        # Initialize StyleManager first to ensure styles are defined
        style_manager = None
        try:
            from .styles import StyleManager
            style_manager = StyleManager(self.window, self.config)
        except Exception as e:
            print(f"Could not initialize StyleManager: {e}")

        self.version_combo = ttk.Combobox(parent_frame, 
                                         state="readonly",
                                         width=6,
                                         font=("Segoe UI", 10),
                                         style="Titlebar.TCombobox",
                                         justify='center')
        self.version_combo.set("Loading...")
        self.version_combo.pack(side='left', padx=(0, 8), pady=2)
        
        # Bind version selection event
        self.version_combo.bind('<<ComboboxSelected>>', self._on_version_selected)
        
        # Apply dropdown styling using StyleManager
        if style_manager:
            try:
                style_manager.apply_combobox_dropdown_style(self.version_combo)
            except Exception as e:
                print(f"Could not apply combobox dropdown style: {e}")
        
        # Load versions in background
        threading.Thread(target=self._fetch_rojo_versions, daemon=True).start()

    def _add_asset_count_to_section(self, parent_frame):
        """Add asset count to title bar section with badge overlay"""
        # Container frame for icon + badge
        asset_frame = tk.Frame(parent_frame, bg=self.config.title_bar_bg, bd=0, highlightthickness=0)
        asset_frame.pack(side='left', padx=(0, 8), pady=0)

        # Package emoji (box) - ensure solid white
        white_box = self._utils.convert_emoji_to_solid_white("\U0001F4E6\uFE0E")
        self.asset_icon_label = tk.Label(asset_frame, text=white_box,
                             bg=self.config.title_bar_bg, fg='white', font=self.ui_font)
        self.asset_icon_label.pack(side='left', padx=(0,0))

        # Badge count (smaller, transparent, closer to box)
        self.asset_count_label = tk.Label(asset_frame, text="0",
                             bg=self.config.title_bar_bg, fg='white', font=self.badge_font,
                             padx=2, pady=0, bd=0, highlightthickness=0)
        
        if self.is_macos:
            self.asset_count_label.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=2)
        else:
            self.asset_count_label.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=0)

        # Make labels draggable
        for widget in (asset_frame, self.asset_icon_label, self.asset_count_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<ButtonRelease-1>", self._stop_move)
            widget.bind("<B1-Motion>", self._on_move)

        # Register callback if file monitor is available
        if self.file_monitor:
            self.file_monitor.add_count_callback(self._update_asset_count)
            
    def _update_asset_count(self, count):
        """Update asset count badge"""
        if self.asset_count_label:
            try:
                # Adjust badge position based on digit count (keep close to box)
                if self.is_macos:
                    base_offset = -4
                    char_width = 6
                else:
                    base_offset = -6
                    char_width = 4
                
                x_offset = base_offset - (len(str(count)) - 1) * char_width
                
                self.window.after(0, lambda: [
                    self.asset_count_label.config(text=str(count)),
                    self.asset_count_label.place_configure(x=x_offset)
                ])
            except Exception:
                pass
    
    def _add_server_status_to_section(self, parent_frame):
        """Add server status to title bar section"""
        # Container for icon and dot
        status_frame = tk.Frame(parent_frame, bg=self.config.title_bar_bg, bd=0, highlightthickness=0, relief='flat')
        status_frame.pack(side='left', padx=(0, 0), pady=0)

        # Unicode globe with meridians symbol (U+1F310) - ensure solid white
        white_globe = self._utils.convert_emoji_to_solid_white("\U0001F310\uFE0E")
        icon_label = tk.Label(status_frame, text=white_globe,
                                 bg=self.config.title_bar_bg, fg='white', font=self.ui_font, bd=0, highlightthickness=0, relief='flat')
        icon_label.pack(side='left', padx=(0, 0))

        # Status Dot (top right of wifi icon, overlapping) - keep as is
        self.server_status_label = tk.Label(status_frame, text="\u25CF\uFE0E",
                 bg=self.config.title_bar_bg, fg='#808080', font=self.small_font, bd=0, highlightthickness=0, relief='flat')
        
        if self.is_macos:
            self.server_status_label.place(in_=icon_label, relx=1.0, rely=0.0, anchor="ne", x=0, y=-4)
        else:
            self.server_status_label.place(in_=icon_label, relx=1.0, rely=0.0, anchor="ne", x=2, y=-6)

        # Make draggable
        for widget in (status_frame, icon_label, self.server_status_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<ButtonRelease-1>", self._stop_move)
            widget.bind("<B1-Motion>", self._on_move)

        # Register callback if server is available
        if self.rojo_server:
            self.rojo_server.add_status_callback(self._update_server_status)

    def _update_server_status(self, is_running):
        """Update server status dot"""
        if self.server_status_label:
            try:
                color = "#4CC718" if is_running else "#FF2A2A"
                self.window.after(0, lambda: self.server_status_label.config(fg=color))
            except Exception:
                pass

    def _add_debug_button_to_section(self, parent_frame):
        """Add debug button to section"""
        white_bug = self._utils.convert_emoji_to_solid_white('🐞')
        debug_btn = ttk.Button(parent_frame, text=white_bug, 
                                command=self._on_debug,
                                style="TitleBar.TButton",
                                takefocus=False)
        debug_btn.pack(side='left', padx=(0, 2), pady=2)
    
    def _add_toggle_button_to_section(self, parent_frame):
        """Add menu button with ellipsis for options"""
        # Create the menu first
        self.options_menu = tk.Menu(parent_frame, tearoff=0, bg='#2d2d2d', fg='white', 
                                   activebackground='#d3d3d3', activeforeground='black',
                                   bd=0, relief='flat', font=('Arial', 9))
        
        # Add menu items
        self.options_menu.add_command(label="Toggle Main Window", command=self._on_toggle)
        self.options_menu.add_command(label="Minimize to Tray", command=self._on_minimize)
        self.options_menu.add_command(label="Close Application", command=self._on_close)
        
        # Create menu button with ttk for consistent styling
        self.menu_button = ttk.Button(
            parent_frame,
            text='...',  # Menu indicator
            command=self._show_menu,
            style="TitleBar.TButton",
            takefocus=False,
            width=8
        )
        self.menu_button.pack(side='right', padx=(0, 5), pady=0)
    
    def _show_menu(self):
        """Show the options menu"""
        if self.options_menu and self.menu_button:
            x = self.menu_button.winfo_rootx()
            y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
            self.options_menu.post(x, y)
    
    def _add_minimize_button_to_section(self, parent_frame):
        """Add minimize button to section"""
        # Use eye emoji for minimize
        eye_icon = '\U0001F441'  # Unicode eye symbol
        minimize_btn = ttk.Button(parent_frame, text=eye_icon, 
                     style="TitleBar.TButton",
                     takefocus=False)
        minimize_btn.pack(side='left', padx=(0, 2), pady=2)
    
    def _add_close_button_to_section(self, parent_frame):
        """Add close button to section"""
        close_btn = ttk.Button(parent_frame, text='X', 
                              command=self._on_close, 
                              style="TitleBar.TButton",
                              takefocus=False)
        close_btn.pack(side='left', padx=(2, 0), pady=2)
    
    def _on_close(self):
        """Handle close button click"""
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.window.destroy()
    
    def _on_minimize(self):
        """Handle minimize button click"""
        if self.on_minimize_callback:
            self.on_minimize_callback()
        else:
            self.window.iconify()
    
    def _on_debug(self):
        """Handle debug button click"""
        if self.on_debug_callback:
            self.on_debug_callback()
    
    def _on_toggle(self):
        """Handle toggle button click"""
        # Toggle the state
        self.toggle_state_visible = not self.toggle_state_visible
        # Update button appearance
        self._update_toggle_button()
        # Call the callback
        if self.on_toggle_callback:
            self.on_toggle_callback()
    
    def _update_toggle_button(self):
        """Update the toggle button text based on current state"""
        if self.toggle_button and self.toggle_button.winfo_exists():
            # Use caret (^) - up when hidden, down when shown
            caret = '^' if not self.toggle_state_visible else 'v'
            self.toggle_button.config(text=caret)
    
    def _on_version_selected(self, event):
        """Handle version selection from dropdown"""
        selected_version = self.version_combo.get()
        
        # Check if we have all required dependencies
        if not self.update_manager:
            print("Cannot change version: UpdateManager not available")
            return
        
        if not self.studio_manager or not self.rojo_server:
            print("Warning: Studio/Server managers not available for version change")
        
        # Call the custom callback if provided
        if self.on_version_change_callback:
            self.on_version_change_callback(selected_version)
        
        # Call the update manager to change version
        print(f"Changing Rojo version to {selected_version}...")
        threading.Thread(
            target=self.update_manager.change_rojo_version,
            args=(selected_version, self.studio_manager, self.rojo_server),
            daemon=True
        ).start()

    
    def _fetch_rojo_versions(self):
        """Fetch Rojo release versions from GitHub API"""
        print("Fetching Rojo versions...")
        try:
            # GitHub API endpoint for Rojo releases
            url = "https://api.github.com/repos/rojo-rbx/rojo/releases"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                releases = response.json()
                # Extract version tags (e.g., "v7.4.1")
                self.rojo_versions = [release.get('tag_name', release.get('name', 'Unknown')) 
                                     for release in releases if not release.get('prerelease', False)]
                print(f"Fetched {len(self.rojo_versions)} Rojo versions.")
                
                # Update combobox on main thread
                try:
                    self.window.after(0, self._update_version_dropdown)
                except Exception:
                    pass
            else:
                try:
                    self.window.after(0, lambda: self.version_combo.set("Failed"))
                except Exception:
                    pass
                print(f"GitHub API error: {response.status_code}")
        except Exception as e:
            try:
                self.window.after(0, lambda: self.version_combo.set("Error"))
            except Exception:
                pass
            print(f"Error fetching Rojo versions: {e}")

    def get_current_version(self):
        """Read toml file to get current Rojo version number and match it with dropdown options to set it"""
        try:
            if not os.path.isfile(self.config.rokit_toml_path):
                print(f"rokit.toml not found at: {self.config.rokit_toml_path}")
                return 0
            with open(self.config.rokit_toml_path, 'r') as toml_file:
                for line in toml_file:
                    if line.strip().startswith('rojo ='):
                        # Example line: rojo = "rojo-rbx/rojo@7.4.1"
                        parts = line.split('"')
                        if len(parts) >= 2:
                            version_part = parts[1]
                            version = version_part.split('@')[-1]
                            # Match with dropdown options
                            for v in self.rojo_versions:
                                if version in v:
                                    return v
        except Exception as e:
            print(f"Error reading rokit.toml: {e}")
            return 0
    
    
    def _update_version_dropdown(self):
        """Update the version dropdown with fetched versions"""
        if self.version_combo and self.version_combo.winfo_exists():
            if self.rojo_versions:
                self.version_combo['values'] = self.rojo_versions
                # Set to first version (latest)
                self.version_combo.set(self.get_current_version() if self.rojo_versions else "No versions")
            else:
                self.version_combo.set("No versions")
    
    def get_selected_version(self):
        """Get the currently selected Rojo version"""
        if self.version_combo:
            return self.version_combo.get()
        return None
    
    def set_version(self, version):
        """Set the selected version programmatically"""
        if self.version_combo and version in self.rojo_versions:
            self.version_combo.set(version)
