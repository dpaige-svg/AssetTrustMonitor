#!/usr/bin/env python3
"""
Update Manager for Rokit Tools

Handles tool updates independently from initialization.
"""

import os
import re
import shutil
import platform
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils

from .rokit_manager import RokitManager
from .plugin_manager import PluginManager




class UpdateManager:
    """Manages Rokit tool updates"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
        self.is_windows = platform.system() == "Windows"
        self.rokit_path = os.path.join(os.path.expanduser("~"), ".rokit")
        self.rokit_mgr = RokitManager(self.config)
    
    def update_tools(self):
        """Update all Rokit tools"""
        try:
            print("Updating Rokit tools...")
            result = self.utils.run_command(['rokit', 'update'])
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Tools updated successfully!")
                print("Tools updated successfully")
                return True
            else:
                error_msg = f"Failed to update tools: {result.stderr}"
                messagebox.showerror("Error", error_msg)
                print(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error during update: {str(e)}"
            messagebox.showerror("Error", error_msg)
            print(error_msg)
            return False
    
    def list_tools(self):
        """List installed tools and versions"""
        try:
            result = self.utils.run_command(['rokit', 'list'])
            
            if result.returncode == 0:
                print("Installed tools:")
                print(result.stdout)
                return result.stdout
            else:
                print(f"Failed to list tools: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error listing tools: {str(e)}")
            return None
    
    def clean_rokit_files(self):
        """
        Clean all Rokit files for fresh installation
        Removes auth, tool storage, cache, and binaries
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Cleaning Rokit files...")
            
            # Files and directories to remove
            files_to_remove = [
                os.path.join(self.rokit_path, "auth.toml"),
                os.path.join(self.rokit_path, "tool-storage", "cache.json"),
                os.path.join(self.rokit_path, "bin", "lune.exe" if self.is_windows else "lune"),
                os.path.join(self.rokit_path, "bin", "rojo.exe" if self.is_windows else "rojo"),
                os.path.join(self.rokit_path, "bin", "rokit.exe" if self.is_windows else "rokit")
            ]
            
            dirs_to_remove = [
                os.path.join(self.rokit_path, "tool-storage", "lune-org"),
                os.path.join(self.rokit_path, "tool-storage", "rojo-rbx")
            ]
            
            # Remove files
            for file_path in files_to_remove:
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Removed: {file_path}")
                    except Exception as e:
                        print(f"Warning: Could not remove {file_path}: {e}")
            
            # Remove directories
            for dir_path in dirs_to_remove:
                if os.path.isdir(dir_path):
                    try:
                        shutil.rmtree(dir_path)
                        print(f"Removed directory: {dir_path}")
                    except Exception as e:
                        print(f"Warning: Could not remove {dir_path}: {e}")
            
            print("Rokit files cleaned successfully")
            return True
            
        except Exception as e:
            error_msg = f"Error cleaning Rokit files: {str(e)}"
            print(error_msg)
            return False
        
    def rebuild_rokit_and_plugin(self, studio_manager=None, rojo_server=None, show_success_message=True):
        """
        Remove rokit files and plugin from studio, then rebuild
        
        Args:
            show_success_message (bool): Whether to show success messagebox
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Rebuilding Rokit and Rojo plugin...")

            #Pre-Setup for safe rebuild
            if studio_manager:
                print("Stopping Roblox Studio...")
                studio_manager.stop()

            if rojo_server:
                print("Stopping Rojo server...")
                rojo_server.stop()
            
            # Step 1: Clean Rokit files
            if not self.clean_rokit_files():
                error_msg = "Failed to clean Rokit files"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            # Step 2: Reinstall Rokit
            if not self.rokit_mgr.install_rokit():
                error_msg = "Failed to reinstall Rokit"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            # Step 3: Trust all tools
            self.rokit_mgr.trust_all_tools()
            
            # Step 4: Install tools from rokit.toml
            print("Installing tools from rokit.toml...")
            result = self.utils.run_command(['rokit', 'install'])
            
            if result.returncode != 0:
                error_msg = f"Failed to install tools: {result.stderr}"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            # Step 5: Reinstall Rojo plugin

            plugin_mgr = PluginManager(self.config)
            
            print("Removing old Rojo plugin...")
            plugin_mgr.uninstall_rojo_plugin()
            
            print("Installing Rojo plugin...")
            if not plugin_mgr.install_rojo_plugin():
                error_msg = "Failed to install Rojo plugin"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            if studio_manager:
                print("Restarting Roblox Studio...")
                studio_manager.start()
                
            if rojo_server:
                print("Restarting Rojo server...")
                rojo_server.start()
            
            print("Rokit and Rojo plugin rebuilt successfully")
            if show_success_message:
                messagebox.showinfo("Success", "Rokit and Rojo plugin rebuilt successfully!")
            return True
            
        except Exception as e:
            error_msg = f"Error rebuilding Rokit and plugin: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            return False



    def change_rojo_version(self, version, studio_manager=None, rojo_server=None):
        """
        Change Rojo version and reinstall
        
        Args:
            version (str): Version tag (e.g., "v7.4.1")
            studio_manager (StudioManager, optional): Studio manager instance
            rojo_server (RojoServer, optional): Rojo server instance
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clean version tag (remove 'v' prefix if present)
            clean_version = version.lstrip('v')
            print(f"Changing Rojo version to {clean_version}...")
            
            # Step 1: Stop Studio and Rojo server if provided
            if studio_manager:
                print("Stopping Roblox Studio...")
                studio_manager.stop()
            
            if rojo_server:
                print("Stopping Rojo server...")
                rojo_server.stop()
            
            # Step 2: Update TOML file with new version
            toml_path = os.path.join(self.config.rojo_cwd, 'rokit.toml')
            if not os.path.isfile(toml_path):
                error_msg = f"rokit.toml not found at: {toml_path}"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            print(f"Updating {toml_path} with version {clean_version}...")
            with open(toml_path, 'r') as f:
                toml_content = f.read()
            
            # Update the rojo version line
            # Pattern matches: rojo = "rojo-rbx/rojo@X.X.X"
            new_content = re.sub(
                r'(rojo\s*=\s*"rojo-rbx/rojo@)[^"]+',
                rf'\g<1>{clean_version}',
                toml_content
            )
            
            with open(toml_path, 'w') as f:
                f.write(new_content)
            
            print(f"Updated rokit.toml to version {clean_version}")
            
            # Step 3: Rebuild Rokit and plugin with new version
            print(f"Rebuilding with Rojo {clean_version}...")
            if not self.rebuild_rokit_and_plugin(show_success_message=False):
                return False
            
            print(f"Rojo {clean_version} installed successfully")
            
            # Step 4: Restart Studio and Rojo server
            if studio_manager:
                print("Restarting Roblox Studio...")
                studio_manager.start()
            
            if rojo_server:
                print("Restarting Rojo server...")
                rojo_server.start()
            
            messagebox.showinfo("Success", f"Rojo version changed to {clean_version} successfully!")
            return True
            
        except Exception as e:
            error_msg = f"Error changing Rojo version: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            return False
    
    def get_current_rojo_version(self):
        """
        Read the current Rojo version from rokit.toml
        
        Returns:
            str: Version string (e.g., "v7.4.1") or None if not found
        """
        try:
            toml_path = os.path.join(self.config.rojo_cwd, 'rokit.toml')
            if not os.path.isfile(toml_path):
                print(f"rokit.toml not found at: {toml_path}")
                return None
            
            with open(toml_path, 'r') as f:
                toml_content = f.read()
            
            # Pattern matches: rojo = "rojo-rbx/rojo@X.X.X"
            match = re.search(r'rojo\s*=\s*"rojo-rbx/rojo@([^"]+)"', toml_content)
            if match:
                version = match.group(1)
                # Add 'v' prefix if not present
                return f"v{version}" if not version.startswith('v') else version
            
            print("Could not find Rojo version in rokit.toml")
            return None
            
        except Exception as e:
            print(f"Error reading current Rojo version: {e}")
            return None
