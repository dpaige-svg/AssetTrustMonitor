#!/usr/bin/env python3
"""
UI Management for Asset Trust Monitor

Coordinates all UI components and manages the main window.
"""

import tkinter as tk
from tkinter import ttk

from ..ui.system_tray import SystemTray
from ..ui.title_bar import TitleBar
from ..ui.styles import StyleManager
from ..ui.icons import IconManager
from ..ui.buttons import ButtonManager
from ..services.studio_manager import StudioManager
from .update_manager import UpdateManager


class UIManager:
    """Manages the main GUI interface"""
    
    def __init__(self, config, file_monitor, rojo_server, cleanup_callback=None, studio_manager=None, enable_debug_menu=True):
        self.config = config
        self.file_monitor = file_monitor
        self.rojo_server = rojo_server
        self.cleanup_callback = cleanup_callback

        self.studio_manager = studio_manager
        # Create update manager instance
        self.update_manager = UpdateManager(config)

        # Always create debug menu if enabled
        self.debug_menu = None
        if enable_debug_menu:
            try:
                from ..ui.debug_menu import DebugMenu
                from ..core.cache_manager import CacheManager
                self.debug_menu = DebugMenu(
                    self.config,
                    self.studio_manager,
                    self.rojo_server,
                    self.update_manager,
                    CacheManager(),
                    self.file_monitor,
                    parent=None
                )
                print("✓ Debug menu initialized and ready")
            except Exception as e:
                print(f"⚠ Could not initialize debug menu: {e}")
        else:
            print("⚠ Debug menu disabled by configuration")
        
        self.root = None
        self.title_bar = None
        self.style_manager = None
        self.icon_manager = None
        self.button_manager = None
        self.label_manager = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the main UI"""
        self.root = tk.Tk()
        self.root.title("Asset Trust Monitor")
        self.root.geometry(self.config.window_size)
        self.root.resizable(False, False)
        try:
            self.root.attributes("-topmost", 1)
        except Exception:
            pass
        self.root.configure(bg=self.config.title_bar_bg)  # Set background to match title bar
        
        # Set parent for debug menu if it exists
        if self.debug_menu:
            self.debug_menu.parent = self.root
        
        # Setup components in order
        self._setup_custom_title_bar()
        self._setup_styles()
        self._create_main_frame()
        # Hide main window by default
        self._toggle_main_window()
        self._load_icons()
        self._create_widgets()
    
    def _setup_custom_title_bar(self):
        """Setup custom title bar using reusable TitleBar component"""
        self.title_bar = TitleBar(
            parent_window=self.root,
            config=self.config,
            show_icon=True,
            show_version_dropdown=False,
            show_asset_count=True,
            show_server_status=True,
            show_debug=False,
            show_toggle=True,
            show_minimize=False,
            show_close=False,
            on_close=self._close_application,
            on_minimize=self._minimize_window,
            on_toggle=self._toggle_main_window,
            on_debug=self._open_debug_menu,
            studio_manager=self.studio_manager,
            rojo_server=self.rojo_server,
            update_manager=self.update_manager,
            file_monitor=self.file_monitor
        )

    def _setup_styles(self):
        """Configure UI styles using StyleManager"""
        self.style_manager = StyleManager(self.root, self.config)

    def _create_main_frame(self):
        """Create the main content frame"""
        self.frame = ttk.Frame(self.root, style="TFrame")
        self.frame.pack(expand=True, fill="both")
        
        # Configure grid weights
        self.frame.columnconfigure(0, weight=1, uniform="group1")
        self.frame.columnconfigure(1, weight=1, uniform="group1")
        self.frame.columnconfigure(2, weight=1, uniform="group1")
        self.frame.rowconfigure(0, weight=1)
    
    def _load_icons(self):
        """Load icons using IconManager"""
        self.icon_manager = IconManager(self.config)
    
    def _create_widgets(self):
        """Create all UI widgets using component managers"""
        # Get loaded icons
        icons = self.icon_manager.get_icons()
        
        # Create buttons
        self.button_manager = ButtonManager(
            parent_frame=self.frame,
            file_monitor=self.file_monitor,
            studio_manager=self.studio_manager,
            update_manager=self.update_manager,
            rojo_server=self.rojo_server,
            config=self.config,
            icons=icons,
            on_debug=self._open_debug_menu,
            style_manager=self.style_manager
        )
    
    def _refresh_status(self):
        """Refresh Rojo server and Roblox Studio manually"""
        self.studio_manager.restart()
        self.rojo_server.restart()

    def _open_debug_menu(self):
        """Open the debug menu window"""
        try:
            if self.debug_menu:
                self.debug_menu.open()
        except Exception as e:
            print(f"Could not open debug menu: {e}")

    def _minimize_window(self):
        """Minimize window to system tray"""
        self.system_tray._toggle_window()

    def _toggle_main_window(self):
        """Toggle visibility of main button window"""
        if hasattr(self, 'frame') and self.frame:
            if self.frame.winfo_viewable():
                # Hide the main frame
                self.frame.pack_forget()
                # Shrink window to just title bar height (30px), keep same width
                width = self.config.window_size.split('x')[0]
                self.root.geometry(f"{width}x30")
                # Update title bar toggle state
                if hasattr(self, 'title_bar') and self.title_bar:
                    self.title_bar.toggle_state_visible = False
                    self.title_bar._update_toggle_button()
            else:
                # Show the main frame
                self.frame.pack(expand=True, fill="both")
                # Restore full window height, keep same width
                self.root.geometry(self.config.window_size)
                # Update title bar toggle state
                if hasattr(self, 'title_bar') and self.title_bar:
                    self.title_bar.toggle_state_visible = True
                    self.title_bar._update_toggle_button()

    def _close_application(self):
        """Close the application properly"""
        # Call main app cleanup if available
        if self.cleanup_callback:
            self.cleanup_callback()
        
        # Cancel any pending tkinter operations
        self.root.after_cancel("all")
        
        # Quit and destroy the window
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop"""
        print("✓ GUI launched successfully - Asset Trust Monitor is running!")
        self.root.mainloop()
    
    def set_system_tray(self, system_tray):
        """Connect system tray for minimize functionality"""
        self.system_tray = system_tray
