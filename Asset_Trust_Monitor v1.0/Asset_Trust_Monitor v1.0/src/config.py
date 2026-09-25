#!/usr/bin/env python3
"""
Configuration Management for Asset Trust Monitor

Handles all application configuration, paths, and directory setup.
"""

import os
import sys
from pathlib import Path

class Config:
    """Central configuration management class"""
    
    def __init__(self):
        self.home = os.path.expanduser("~")
        self.downloads_path = os.path.join(self.home, "Downloads")
        
        # Checks if currently running as a script or exe for correct path handling
        if getattr(sys, 'frozen', False):
            # Running as a bundled exe
            self.main_folder = os.path.dirname(sys.executable)
        else:
            # Running as a .py script - go up one directory from src/ to project root
            self.main_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Application Directories
        self.assets_folder = os.path.join(self.main_folder, "Assets")
        self.workspace_folder = os.path.join(self.main_folder, "Rojo_Build", "src", "Workspace")
        self.rbxl_file_path = os.path.join(self.main_folder, "Rojo_Build", "Asset_Trust_Place.rbxl")
        self.processing_folder = os.path.join(self.main_folder, "processing", "Processing_rbxm")
        self.rojo_cwd = os.path.join(self.main_folder, "Rojo_Build")
        self.icons_path = os.path.join(self.main_folder, "Rojo_Build", "icons")
        
        # UI Configuration
        self.window_size = "180x140"
        self.dark_bg = "#1E1E1E"
        self.title_bar_bg = "#363636"
        self.accent_color = "#598484"

        # Button Styles
        self.style_close_btn = "Close.TButton"
        self.style_minimize_btn = "Minimize.TButton"
        self.style_refresh_btn = "Refresh.TButton"
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.assets_folder,
            self.workspace_folder,
            os.path.dirname(self.processing_folder)
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_icon_path(self, icon_name):
        """Get full path to an icon file"""
        return os.path.join(self.icons_path, f"{icon_name}.ico")