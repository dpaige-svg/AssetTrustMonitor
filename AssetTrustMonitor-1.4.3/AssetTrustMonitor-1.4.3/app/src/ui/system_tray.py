#!/usr/bin/env python3
"""
System Tray Integration for Asset Trust Monitor

Handles system tray icon, menu, and window management.
"""

from PIL import Image, ImageDraw
import math

try:
    from pystray import Icon as _PystrayIcon, Menu as _PystrayMenu, MenuItem as _PystrayMenuItem
    PYSTRAY_AVAILABLE = True
except Exception:
    _PystrayIcon = None
    _PystrayMenu = None
    _PystrayMenuItem = None
    PYSTRAY_AVAILABLE = False

class SystemTray:
    """Manages system tray icon and interactions"""
    
    def __init__(self, root_window, cleanup_callback=None):
        self.root = root_window
        self.icon = None
        self.cleanup_callback = cleanup_callback
        self.available = PYSTRAY_AVAILABLE

        if self.available:
            self._setup_tray()
        else:
            print("System tray disabled: pystray is unavailable for this Python version.")
    
    def _setup_tray(self):
        """Initialize system tray icon"""
        if not self.available:
            return

        icon_image = self._create_icon_image()
        self.icon = _PystrayIcon("Asset Trust Monitor", icon_image, menu=_PystrayMenu(
            _PystrayMenuItem("Hide", self._toggle_window),
            _PystrayMenuItem("Exit", self._exit_app)
        ))
        
        # run_detached is non-blocking and handles macOS main-thread requirement.
        self.icon.run_detached()
    
    def _create_icon_image(self):
        """Create the system tray icon image"""
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        center_x, center_y = width // 2, height // 2
        outer_size = int(width * 0.25)
        
        # 15-degree rotation
        angle = math.radians(15)
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        
        def rotate_point(x, y, cx, cy):
            x -= cx
            y -= cy
            new_x = x * cos_angle - y * sin_angle
            new_y = x * sin_angle + y * cos_angle
            return new_x + cx, new_y + cy
        
        # Outer rectangle
        outer_half = outer_size
        outer_corners = [
            (center_x - outer_half, center_y - outer_half),
            (center_x + outer_half, center_y - outer_half),
            (center_x + outer_half, center_y + outer_half),
            (center_x - outer_half, center_y + outer_half) 
        ]
        
        outer_points = [rotate_point(x, y, center_x, center_y) for x, y in outer_corners]
        draw.polygon(outer_points, fill="white")
        
        # Inner rectangle
        inner_size = int(outer_size * 0.4)
        inner_half = inner_size
        inner_corners = [
            (center_x - inner_half, center_y - inner_half),
            (center_x + inner_half, center_y - inner_half),
            (center_x + inner_half, center_y + inner_half), 
            (center_x - inner_half, center_y + inner_half)   
        ]
        
        inner_points = [rotate_point(x, y, center_x, center_y) for x, y in inner_corners]
        draw.polygon(inner_points, fill="black")
        
        return image
    
    def _toggle_window(self, icon=None, item=None):
        """Toggle main window visibility on the Tk main thread."""
        self.root.after(0, self._do_toggle_window)

    def _do_toggle_window(self):
        """Actual tk operations — must run on the tk main thread."""
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()
        # Rebuild menu with a dynamic title so no live reassignment is needed
        self._refresh_menu()

    def _refresh_menu(self):
        """Rebuild tray menu based on current window state."""
        if not self.available or not self.icon:
            return

        visible = self.root.winfo_viewable()
        self.icon.menu = _PystrayMenu(
            _PystrayMenuItem("Hide" if visible else "Show", self._toggle_window),
            _PystrayMenuItem("Exit", self._exit_app)
        )

    def _exit_app(self, icon=None, item=None):
        """Exit the application and stop tray if available."""
        if self.cleanup_callback:
            self.cleanup_callback()
        else:
            print("No cleanup callback provided, could not perform cleanup.")

        if self.icon:
            self.icon.stop()
        self.root.after(0, self.root.quit)
    
    def stop(self):
        """Stop the system tray icon"""
        if self.icon:
            self.icon.stop()
    