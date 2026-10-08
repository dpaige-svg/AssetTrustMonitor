#!/usr/bin/env python3
"""
Update Manager for Rokit Tools

Handles tool updates independently from initialization.
"""

import os
import platform
import re
import shutil
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils
from .plugin_manager import PluginManager
from .rokit_manager import RokitManager


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
                
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error during update: {e!s}"
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
                
        except Exception as e:  # noqa: BLE001
            print(f"Error listing tools: {e!s}")
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
                    except Exception as e:  # noqa: BLE001
                        print(f"Warning: Could not remove {file_path}: {e}")
            
            # Remove directories
            for dir_path in dirs_to_remove:
                if os.path.isdir(dir_path):
                    try:
                        shutil.rmtree(dir_path)
                        print(f"Removed directory: {dir_path}")
                    except Exception as e:  # noqa: BLE001
                        print(f"Warning: Could not remove {dir_path}: {e}")
            
            print("Rokit files cleaned successfully")
            return True
            
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error cleaning Rokit files: {e!s}"
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
            
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error rebuilding Rokit and plugin: {e!s}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            return False



    def change_rojo_version(self, version, studio_manager=None, rojo_server=None, file_monitor=None):
        """
        Change Rojo version and reinstall
        
        Args:
            version (str): Version tag (e.g., "v7.4.1")
            studio_manager (StudioManager, optional): Studio manager instance
            rojo_server (RojoServer, optional): Rojo server instance
        
        Returns:
            bool: True if successful, False otherwise
        """
        toml_path = None
        toml_content = None
        monitor_was_running = False
        try:
            # Clean and validate the release tag before touching configuration.
            clean_version = version.lstrip('v')
            if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?', clean_version):
                raise ValueError(f"Invalid Rojo version: {version}")
            print(f"Changing Rojo version to {clean_version}...")

            monitor_was_running = bool(file_monitor and file_monitor.is_monitoring())
            if monitor_was_running:
                print("Pausing asset monitoring during Rojo update...")
                file_monitor.stop_monitoring()

            # Stop consumers before replacing the CLI/plugin pair.
            if studio_manager:
                print("Stopping Roblox Studio...")
                studio_manager.stop()
            
            if rojo_server:
                print("Stopping Rojo server...")
                rojo_server.stop()
            
            toml_path = os.path.join(self.config.rojo_cwd, 'rokit.toml')
            if not os.path.isfile(toml_path):
                error_msg = f"rokit.toml not found at: {toml_path}"
                print(error_msg)
                messagebox.showerror("Error", error_msg)
                return False
            
            print(f"Updating {toml_path} with version {clean_version}...")
            with open(toml_path, 'r', encoding='utf-8') as f:
                toml_content = f.read()
            
            # Update the rojo version line
            # Pattern matches: rojo = "rojo-rbx/rojo@X.X.X"
            new_content = re.sub(
                r'(rojo\s*=\s*"rojo-rbx/rojo@)[^"]+',
                rf'\g<1>{clean_version}',
                toml_content
            )
            
            if new_content == toml_content and f"@{clean_version}" not in toml_content:
                raise RuntimeError("Could not locate the Rojo version entry in rokit.toml")

            temporary_toml = toml_path + ".tmp"
            with open(temporary_toml, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new_content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_toml, toml_path)
            
            print(f"Updated rokit.toml to version {clean_version}")
            
            # Install only the pinned tools. A normal version change should not
            # delete Rokit itself or unrelated cached tools.
            if not self.rokit_mgr.is_rokit_installed():
                raise RuntimeError("Rokit is not installed or could not be added to PATH")

            self.rokit_mgr.trust_all_tools()
            install_result = self.utils.run_command(['rokit', 'install'])
            if install_result.returncode != 0:
                raise RuntimeError(install_result.stderr.strip() or "Rokit could not install the selected Rojo version")

            rojo_executable = self.config.get_tool_executable('rojo')
            version_result = self.utils.run_command([rojo_executable, '--version'])
            version_output = (version_result.stdout or "").strip()
            if version_result.returncode != 0 or clean_version not in version_output:
                raise RuntimeError(
                    f"Rojo verification failed: expected {clean_version}, received {version_output or 'no version output'}"
                )

            # Rojo documents a matching plugin install as part of upgrading.
            plugin_mgr = PluginManager(self.config)
            if not plugin_mgr.uninstall_rojo_plugin():
                raise RuntimeError("Could not remove the previous Rojo Studio plugin")
            if not plugin_mgr.install_rojo_plugin():
                raise RuntimeError("Could not install the matching Rojo Studio plugin")
            
            print(f"Rojo {clean_version} installed successfully")
            
            # Start the verified server before Studio so the plugin connects to
            # the correct project and protocol as Studio opens.
            if rojo_server:
                print("Restarting Rojo server...")
                if not rojo_server.start():
                    raise RuntimeError("Rojo installed but rojo serve did not become ready")

            if studio_manager:
                print("Restarting Roblox Studio...")
                if not studio_manager.start():
                    raise RuntimeError("Rojo updated, but Roblox Studio could not be restarted")

            if monitor_was_running:
                print("Resuming asset monitoring...")
                file_monitor.start_monitoring()
            
            messagebox.showinfo("Success", f"Rojo version changed to {clean_version} successfully!")
            return True
            
        except Exception as e:  # noqa: BLE001
            if toml_path and toml_content is not None:
                try:
                    with open(toml_path, 'w', encoding='utf-8', newline='\n') as f:
                        f.write(toml_content)
                    print("Restored the previous rokit.toml after update failure")
                except OSError as rollback_error:
                    print(f"Could not restore rokit.toml: {rollback_error}")

            if monitor_was_running and file_monitor and not file_monitor.is_monitoring():
                try:
                    file_monitor.start_monitoring()
                except Exception as monitor_error:  # noqa: BLE001
                    print(f"Could not resume asset monitoring: {monitor_error}")

            error_msg = f"Error changing Rojo version: {e!s}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            return False

    def rebuild_rokit_and_plugins(self, studio_manager=None, rojo_server=None, show_success_message=True):
        """Compatibility alias retained for older recovery call sites."""
        return self.rebuild_rokit_and_plugin(
            studio_manager=studio_manager,
            rojo_server=rojo_server,
            show_success_message=show_success_message,
        )
    
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
            
        except Exception as e:  # noqa: BLE001
            print(f"Error reading current Rojo version: {e}")
            return None
