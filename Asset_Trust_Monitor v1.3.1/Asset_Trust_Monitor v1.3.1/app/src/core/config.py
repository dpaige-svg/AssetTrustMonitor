#!/usr/bin/env python3
"""
Configuration Management for Asset Trust Monitor

Centralized configuration with environment-aware paths.
"""

import os
import sys
import platform
import json
from pathlib import Path


class Config:
    """Central configuration management class"""
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._setup_paths()
        self._setup_ui_config()
        self._create_directories()
        
        # Settings
        self._auto_clean_trash = "false"
        self._load_debug_options()

    @property
    def auto_clean_trash(self):
        val = getattr(self, '_auto_clean_trash', "false")
        if isinstance(val, str):
            v = val.strip().lower()
            if v == "true":
                return "true"
            return "false"
        elif isinstance(val, bool):
            return "true" if val else "false"
        return "false"

    @auto_clean_trash.setter
    def auto_clean_trash(self, value):
        # Always sanitize to 'true' or 'false' string
        if isinstance(value, str):
            v = value.strip().lower()
            if v == "true":
                self._auto_clean_trash = "true"
            else:
                self._auto_clean_trash = "false"
        elif isinstance(value, bool):
            self._auto_clean_trash = "true" if value else "false"
        else:
            self._auto_clean_trash = "false"
    
    def _load_debug_options(self):
        """Load debug options from JSON, storing as string 'true' or 'false' only"""
        try:
            self.auto_clean_trash = "false"  # Default
            if not os.path.exists(self.debug_options_path):
                # Create the file with default value if missing
                try:
                    with open(self.debug_options_path, 'w', encoding='utf-8', newline='\n') as f:
                        json.dump({"auto_clean_trash": "false"}, f, indent=4)
                except Exception as e:
                    print(f"[Config] Could not create debug_options.json: {e}")
            if os.path.exists(self.debug_options_path):
                with open(self.debug_options_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"[Config] JSON formatting error in debug_options.json: {e}")
                        data = {}
                    raw_value = data.get("auto_clean_trash", "false")
                    # Always use the property setter for sanitization
                    if isinstance(raw_value, str):
                        v = raw_value.strip().lower()
                        if v == "true":
                            self.auto_clean_trash = "true"
                        elif v == "false":
                            self.auto_clean_trash = "false"
                        elif v == "":
                            self.auto_clean_trash = "false"
                        else:
                            self.auto_clean_trash = "false"
                    elif isinstance(raw_value, bool):
                        self.auto_clean_trash = "true" if raw_value else "false"
                    else:
                        self.auto_clean_trash = "false"
            # Final check: if blank or invalid, set to 'false'
            if not isinstance(self.auto_clean_trash, str) or self.auto_clean_trash.strip().lower() not in ("true", "false"):
                self.auto_clean_trash = "false"
        except Exception as e:
            print(f"Error loading debug options: {e}")

    def save_debug_options(self):
        """Save debug options to JSON as string 'true' or 'false'"""
        try:
            value = self.auto_clean_trash
            if not isinstance(value, str) or value.strip().lower() not in ("true", "false"):
                value = "false"
            data = {
                "auto_clean_trash": value
            }
            with open(self.debug_options_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving debug options: {e}")

    def _setup_paths(self):
        """Setup all application paths"""
        self.home = os.path.expanduser("~")
        self.rokit_bin = os.path.join(self.home, ".rokit", "bin")
        self.downloads_path = os.path.join(self.home, "Downloads")
        self.system = platform.system()
        
        # Determine main folder (exe vs script)
        if getattr(sys, 'frozen', False):
            # Running as exe - main folder is where exe is located
            self.main_folder = os.path.dirname(sys.executable)
            self.app_folder = os.path.join(self.main_folder, "app")
        else:
            # Running as script - go up from src/core to app, then to project root
            self.app_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.main_folder = os.path.dirname(self.app_folder)
        
        # Application directories
        self.assets_folder = os.path.join(self.main_folder, "Assets")
        self.processing_folder = os.path.join(self.app_folder, "processing", "Processing_rbxm")
        self.datastore_folder = os.path.join(self.app_folder, "processing", "DataStore")
        self.debug_options_path = os.path.join(self.datastore_folder, "debug_options.json")
        
        # Rojo/Roblox paths
        self.rojo_cwd = os.path.join(self.app_folder, "Rojo_Build")
        self.workspace_folder = os.path.join(self.rojo_cwd, "src", "Workspace")
        self.rbxl_file_path = os.path.join(self.rojo_cwd, "Asset_Trust_Place.rbxl")
        self.rokit_toml_path = os.path.join(self.rojo_cwd, "rokit.toml")
        self.icons_path = os.path.join(self.rojo_cwd, "icons")
        
        # Plugin paths
        if self.system == "Windows":
            self.roblox_plugins = os.path.join(self.home, "AppData", "Local", "Roblox", "Plugins")
        elif self.system == "Darwin":
            self.roblox_plugins = os.path.join(self.home, "Documents", "Roblox", "Plugins")
        else:
            self.roblox_plugins = os.path.join(self.home, "Roblox", "Plugins")

    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.assets_folder,
            self.workspace_folder,
            self.processing_folder,
            self.datastore_folder
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _setup_ui_config(self):
        """Setup UI configuration"""
        self.window_size = "200x65"  # Wider and taller for better button visibility and complete icon display
        self.dark_bg = "#1E1E1E"
        self.title_bar_bg = "#363636"
        self.accent_color = "#598484"
    
    def get_icon_path(self, icon_name):
        """Get full path to an icon file"""
        return os.path.join(self.icons_path, f"{icon_name}.ico")
    
    def get_tool_executable(self, tool_name):
        """Get full path to a rokit tool executable"""
        if self.system == "Windows":
            return os.path.join(self.rokit_bin, f"{tool_name}.exe")
        return os.path.join(self.rokit_bin, tool_name)
    
    def tool_exists(self, tool_name):
        """Check if a rokit tool exists"""
        return os.path.isfile(self.get_tool_executable(tool_name))
