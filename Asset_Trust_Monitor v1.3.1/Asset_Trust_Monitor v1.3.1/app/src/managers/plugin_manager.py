#!/usr/bin/env python3
"""
Plugin Manager

Handles Roblox plugin detection, installation, and management.
"""

import os
import shutil
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils


class PluginManager:
    """Manages Roblox plugins"""
    
    ROJO_PLUGINS = [
        "RojoManagedPlugin.rbxm",
        "Rojo.rbxm"
    ]
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
    
    def get_installed_plugins(self, plugin_names=None):
        """
        Get list of installed plugins
        
        Args:
            plugin_names: Optional list of specific plugin names to check.
                         If None, returns all .rbxm plugins in the folder.
        
        Returns:
            List of dicts with plugin info (name, path, size)
        """
        try:
            if not os.path.exists(self.config.roblox_plugins):
                print("Cannot find Roblox plugins directory")
                return []
            
            installed = []
            
            # Check specific plugins if provided
            if plugin_names:
                for plugin in plugin_names:
                    path = os.path.join(self.config.roblox_plugins, plugin)
                    if os.path.isfile(path):
                        installed.append({
                            'name': plugin,
                            'path': path,
                            'size': os.path.getsize(path)
                        })
            # Otherwise, list all .rbxm files
            else:
                for file in os.listdir(self.config.roblox_plugins):
                    if file.endswith('.rbxm'):
                        path = os.path.join(self.config.roblox_plugins, file)
                        installed.append({
                            'name': file,
                            'path': path,
                            'size': os.path.getsize(path)
                        })
            
            return installed
            
        except Exception as e:
            print(f"Error listing plugins: {e}")
            return []
    
    def get_installed_rojo_plugins(self):
        """Get list of installed Rojo plugins specifically"""
        return self.get_installed_plugins(self.ROJO_PLUGINS)
    
    def is_rojo_installed(self):
        """Check if any Rojo plugin is installed"""
        return len(self.get_installed_rojo_plugins()) > 0
    
    def install_rojo_plugin(self):
        """Install Rojo plugin using rojo command"""
        if self.is_rojo_installed():
            print("Rojo plugin already installed")
            return True
        
        try:
            print("Installing Rojo plugin...")
            result = self.utils.run_command('rojo plugin install')
            
            if result.returncode == 0:
                print("Rojo plugin installed successfully")
                return True
            else:
                error_msg = f"Failed to install Rojo plugin: {result.stderr}"
                print(error_msg)
                messagebox.showerror("Plugin Installation Error", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Failed to install Rojo plugin: {e}"
            print(error_msg)
            messagebox.showerror("Plugin Installation Error", error_msg)
            return False
    
    def uninstall_rojo_plugin(self):
        """Uninstall all Rojo plugins"""
        try:
            installed = self.get_installed_rojo_plugins()
            if not installed:
                print("No Rojo plugins found to uninstall")
                return True
            
            for plugin in installed:
                print(f"Removing {plugin['name']}...")
                os.remove(plugin['path'])
            
            print("Rojo plugin(s) uninstalled successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to uninstall Rojo plugin: {e}"
            print(error_msg)
            messagebox.showerror("Plugin Uninstall Error", error_msg)
            return False
    
    def install_custom_plugin(self, plugin_source_path, plugin_name=None):
        """
        Install a custom plugin from a source path
        
        Args:
            plugin_source_path: Path to the .rbxm plugin file
            plugin_name: Optional custom name for the plugin (defaults to source filename)
        """
        if not os.path.isfile(plugin_source_path):
            error_msg = f"Plugin file not found: {plugin_source_path}"
            print(error_msg)
            messagebox.showerror("Plugin Error", error_msg)
            return False
        
        try:
            # Use source filename if no custom name provided
            if plugin_name is None:
                plugin_name = os.path.basename(plugin_source_path)
            
            # Ensure .rbxm extension
            if not plugin_name.endswith('.rbxm'):
                plugin_name += '.rbxm'
            
            destination = os.path.join(self.config.roblox_plugins, plugin_name)
            
            print(f"Installing plugin {plugin_name}...")
            shutil.copy2(plugin_source_path, destination)
            print(f"Plugin installed: {destination}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to install custom plugin: {e}"
            print(error_msg)
            messagebox.showerror("Plugin Installation Error", error_msg)
            return False
    
    def verify_plugin(self, plugin_name):
        """Verify a plugin exists and is valid"""
        plugin_path = os.path.join(self.config.roblox_plugins, plugin_name)
        
        if not os.path.isfile(plugin_path):
            return False, "Plugin file not found"
        
        if os.path.getsize(plugin_path) == 0:
            return False, "Plugin file is empty"
        
        return True, "Plugin is valid"
    
    def reinstall_plugin(self):
        """Reinstall Rojo plugin"""
        success = self.uninstall_rojo_plugin()
        if not success:
            print("Failed to uninstall existing Rojo plugin")
            messagebox.showerror("Plugin Reinstall Error", "Failed to uninstall existing Rojo plugin")
            return False
        
        return self.install_rojo_plugin()
