#!/usr/bin/env python3
"""
System Tray Integration for Asset Trust Monitor

Handles system tray icon, menu, and window management.
"""

import threading
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem
import math

class SystemTray:
    """Manages system tray icon and interactions"""
    
    def __init__(self, root_window, cleanup_callback=None):
        self.root = root_window
        self.icon = None
        self.cleanup_callback = cleanup_callback
        self._setup_tray()
    
    def _setup_tray(self):
        """Initialize system tray icon"""
        icon_image = self._create_icon_image()
        self.icon = Icon("Asset Trust Monitor", icon_image, menu=Menu(
            MenuItem("Hide", self._toggle_window),
            MenuItem("Exit", self._exit_app)
        ))
        
        # Start tray icon in background thread
        threading.Thread(target=self.icon.run, daemon=True).start()
    
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
        """Toggle main window visibility"""
        if self.root.winfo_viewable():
            self.root.withdraw()
            self.icon.menu = Menu(
                MenuItem("Show", self._toggle_window),
                MenuItem("Exit", self._exit_app)
            )
        else:
            self.root.deiconify()
            self.icon.menu = Menu(
                MenuItem("Hide", self._toggle_window),
                MenuItem("Exit", self._exit_app)
            )
    
    def _exit_app(self, icon=None, item=None):
        """Exit the application"""
        if self.cleanup_callback:
            self.cleanup_callback()
        else:
            print("No cleanup callback provided, could not perform cleanup.")
            
        self.icon.stop()
        self.root.after(0, self.root.quit)
    
    def stop(self):
        """Stop the system tray icon"""
        if self.icon:
            self.icon.stop()
    