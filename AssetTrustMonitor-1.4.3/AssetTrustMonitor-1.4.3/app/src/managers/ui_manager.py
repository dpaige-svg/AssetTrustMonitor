#!/usr/bin/env python3
"""
UI Management for Asset Trust Monitor

Coordinates all UI components and manages the main window.
"""

import tkinter as tk
from pathlib import Path
from tkinter import ttk
import platform

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
                print("OK: Debug menu initialized and ready")
            except Exception as e:
                print(f"Warning: Could not initialize debug menu: {e}")
        else:
            print("Warning: Debug menu disabled by configuration")
        
        self.root = None
        self.title_bar = None
        self.style_manager = None
        self.icon_manager = None
        self.button_manager = None
        self.label_manager = None
        self._is_maximized = False
        self._normal_geometry = None
        self._platform = platform.system()
        self._closing = False
        self._active_toasts = []

        if self.file_monitor:
            self.file_monitor.add_processed_asset_callback(self._on_processed_asset)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the main UI"""
        # On macOS, messagebox calls before this point create a hidden default
        # root. Reuse it instead of creating a second Tk() instance which
        # never appears on macOS Python 3.9 (CommandLineTools).
        if tk._default_root is not None:
            self.root = tk._default_root
            self.root.deiconify()
        else:
            self.root = tk.Tk()
        self.root.title("Asset Trust Monitor")
        icon_path = Path(__file__).resolve().parents[2] / "App_Build" / "assets" / "ApplicationIcon.png"
        if icon_path.is_file():
            try:
                self._window_icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self._window_icon)
            except Exception:
                self._window_icon = None
        self.root.geometry(self.config.window_size)
        self.root.resizable(False, False)
        try:
            self.root.attributes("-topmost", 1)
        except Exception:
            pass
        self.root.configure(bg=self.config.title_bar_bg)
        self.root.bind("<Map>", self._on_window_map, add="+")
        self.root.protocol("WM_DELETE_WINDOW", self._close_application)
        
        # Set parent for debug menu if it exists
        if self.debug_menu:
            self.debug_menu.parent = self.root
        
        # Setup components in order
        self._setup_custom_title_bar()
        self._setup_styles()
        self._create_main_frame()
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
            show_maximize=False,
            show_close=True,
            on_close=self._close_application,
            on_minimize=self._minimize_window,
            on_maximize_restore=self._maximize_restore_window,
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
        self.frame.columnconfigure(3, weight=1, uniform="group1")
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

    def _on_processed_asset(self, asset_display_name, verified):
        """Handle processed asset notifications from FileMonitor."""
        if not verified:
            return

        if self.root and self.root.winfo_exists():
            self.root.after(0, lambda: self._show_asset_inserted_toast(asset_display_name))

    def _show_asset_inserted_toast(self, asset_display_name):
        """Show a right-side slide-in toast for successful asset insertion."""
        try:
            toast_width = 420
            toast_height = 92
            margin_right = 20
            margin_top = 40 + (len(self._active_toasts) * (toast_height + 10))

            screen_w = self.root.winfo_screenwidth()
            target_x = screen_w - toast_width - margin_right
            start_x = screen_w + 8
            y = margin_top

            toast = tk.Toplevel(self.root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg="#141414")
            toast.geometry(f"{toast_width}x{toast_height}+{start_x}+{y}")

            frame = tk.Frame(toast, bg="#141414", highlightthickness=1, highlightbackground="#2d2d2d")
            frame.pack(fill="both", expand=True)

            title = tk.Label(
                frame,
                text="Asset Inserted",
                bg="#141414",
                fg="#7ee787",
                font=("Segoe UI", 10, "bold"),
                anchor="w"
            )
            title.pack(fill="x", padx=12, pady=(10, 2))

            body = tk.Label(
                frame,
                text=asset_display_name,
                bg="#141414",
                fg="#e6edf3",
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
                wraplength=toast_width - 24
            )
            body.pack(fill="x", padx=12, pady=(0, 10))

            self._active_toasts.append(toast)

            def slide_in(current_x):
                if not toast.winfo_exists():
                    return
                next_x = max(target_x, current_x - 28)
                toast.geometry(f"{toast_width}x{toast_height}+{next_x}+{y}")
                if next_x > target_x:
                    toast.after(12, lambda: slide_in(next_x))
                else:
                    toast.after(2200, lambda: slide_out(target_x))

            def slide_out(current_x):
                if not toast.winfo_exists():
                    return
                next_x = min(screen_w + 10, current_x + 34)
                toast.geometry(f"{toast_width}x{toast_height}+{next_x}+{y}")
                if next_x < screen_w + 10:
                    toast.after(10, lambda: slide_out(next_x))
                else:
                    self._destroy_toast(toast)

            slide_in(start_x)
        except Exception as e:
            print(f"Failed to show asset toast: {e}")

    def _destroy_toast(self, toast):
        """Destroy toast and collapse stack positions."""
        try:
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)
            if toast.winfo_exists():
                toast.destroy()
        except Exception:
            pass

    def _open_debug_menu(self):
        """Open the debug menu window"""
        try:
            if self.debug_menu:
                self.debug_menu.open()
        except Exception as e:
            print(f"Could not open debug menu: {e}")

    def _minimize_window(self):
        """Collapse content area to title-bar-only strip."""
        self._toggle_main_window()

    def _on_window_map(self, event=None):
        """Ensure topmost is set whenever the main window is mapped."""
        try:
            self.root.attributes("-topmost", 1)
        except Exception:
            pass

        # On macOS, window manager can reapply decorations on map;
        # re-enforce custom borderless title bar after mapping.
        try:
            if self.title_bar:
                self.root.after(0, lambda: self.title_bar.set_borderless(True))
        except Exception:
            pass

    def _maximize_restore_window(self):
        """Toggle maximize/restore for the main window."""
        if not self._is_maximized:
            self._normal_geometry = self.root.geometry()

            # Prefer native window-manager maximize where supported.
            if self._platform == "Windows":
                try:
                    self.root.state("zoomed")
                    self._is_maximized = True
                    return True
                except Exception:
                    pass

            x, y, width, height = self._get_work_area_bounds()
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self._is_maximized = True
        else:
            if self._platform == "Windows":
                try:
                    self.root.state("normal")
                except Exception:
                    pass
            self.root.geometry(self._normal_geometry or self.config.window_size)
            self._is_maximized = False

        return self._is_maximized

    def _get_work_area_bounds(self):
        """Get usable desktop bounds for borderless window maximize fallback."""
        x = int(self.root.winfo_vrootx())
        y = int(self.root.winfo_vrooty())
        width = int(self.root.winfo_vrootwidth())
        height = int(self.root.winfo_vrootheight())

        if width <= 0 or height <= 0:
            x, y = 0, 0
            width = int(self.root.winfo_screenwidth())
            height = int(self.root.winfo_screenheight())

        return x, y, width, height

    def _toggle_main_window(self):
        """Toggle visibility of main button window"""
        if hasattr(self, 'frame') and self.frame:
            current_width = max(int(self.root.winfo_width()), 1)
            if self.frame.winfo_viewable():
                # Hide the main frame
                self.frame.pack_forget()
                # Shrink window to just title bar height (30px), keep same width
                self.root.geometry(f"{current_width}x30")
                # Update title bar toggle state
                if hasattr(self, 'title_bar') and self.title_bar:
                    self.title_bar.toggle_state_visible = False
                    self.title_bar._update_toggle_button()
            else:
                # Show the main frame
                self.frame.pack(expand=True, fill="both")
                # Restore full window height, keep current width
                default_height = self.config.window_size.split('x')[1]
                self.root.geometry(f"{current_width}x{default_height}")
                # Update title bar toggle state
                if hasattr(self, 'title_bar') and self.title_bar:
                    self.title_bar.toggle_state_visible = True
                    self.title_bar._update_toggle_button()

    def _close_application(self):
        """Begin staged shutdown: stop services then destroy the UI."""
        if self._closing:
            return
        self._closing = True
        print("Close requested - starting full application shutdown...")

        # Run background service teardown off the main thread so the UI
        # stays responsive during cleanup, then destroy on the Tk thread.
        import threading
        def _do_shutdown():
            if self.cleanup_callback:
                try:
                    self.cleanup_callback()
                except Exception as e:
                    print(f"Cleanup error: {e}")
            else:
                # Fallback path if no parent callback was supplied.
                for name, fn in (
                    ("file monitor", lambda: self.file_monitor.stop_monitoring() if self.file_monitor else None),
                    ("rojo server", lambda: self.rojo_server.stop() if self.rojo_server else None),
                    ("studio manager", lambda: self.studio_manager.stop() if self.studio_manager else None),
                ):
                    try:
                        fn()
                        print(f"  OK: {name} stopped")
                    except Exception as e:
                        print(f"  ERROR: {name} stop failed: {e}")
            # Schedule Tk destruction back on the main thread.
            try:
                self.root.after(0, self._destroy_ui)
            except Exception:
                pass

        threading.Thread(target=_do_shutdown, daemon=True).start()

    def _destroy_ui(self):
        """Destroy the Tk window after services have shut down."""
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
    
    def run(self):
        """Start the GUI main loop"""
        print("GUI launched successfully - Asset Trust Monitor is running!")
        # Bring window to front and keep it top-most per user preference.
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.mainloop()
    
    def set_system_tray(self, system_tray):
        """Connect system tray for minimize functionality"""
        self.system_tray = system_tray
