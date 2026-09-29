#!/usr/bin/env python3
"""
Rokit Tool Management

Handles Rokit installation, tool management, and coordination with other managers.
"""

import os
import platform
import subprocess
import shutil
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils


class RokitManager:
    """Manages Rokit toolchain and coordinates tool installation"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
        self.is_windows = platform.system() == "Windows"
        
        # Lazy import to avoid circular dependencies
        self._rojo_mgr = None
        self._lune_mgr = None
        self._plugin_mgr = None
    
    @property
    def rojo_mgr(self):
        """Lazy load RojoManager"""
        if self._rojo_mgr is None:
            from .rojo_manager import RojoManager
            self._rojo_mgr = RojoManager(self.config)
        return self._rojo_mgr
    
    @property
    def lune_mgr(self):
        """Lazy load LuneManager"""
        if self._lune_mgr is None:
            from .lune_manager import LuneManager
            self._lune_mgr = LuneManager(self.config)
        return self._lune_mgr
    
    @property
    def plugin_mgr(self):
        """Lazy load PluginManager"""
        if self._plugin_mgr is None:
            from .plugin_manager import PluginManager
            self._plugin_mgr = PluginManager(self.config)
        return self._plugin_mgr
    
    def refresh_path(self):
        """Add Rokit to system PATH"""
        os.environ["PATH"] = self.config.rokit_bin + os.pathsep + os.environ.get("PATH", "")
        
        if self.is_windows:
            powershell_cmd = (
                '$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + '
                '[System.Environment]::GetEnvironmentVariable("Path", "Machine")'
            )
            subprocess.run(["powershell", "-Command", powershell_cmd], shell=True)
        
        return shutil.which("rokit") is not None
    
    def is_rokit_installed(self):
        """Check if Rokit is installed"""
        return self.refresh_path()
    
    def install_rokit(self):
        """Install Rokit if not present"""
        if self.is_rokit_installed():
            return True
        
        print("Installing Rokit...")
        
        if self.is_windows:
            cmd = 'Invoke-RestMethod https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.ps1 | Invoke-Expression'
            process = subprocess.run(["powershell", "-Command", cmd], shell=True)
        else:
            cmd = 'curl -sSf https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.sh | bash'
            process = subprocess.run(cmd, shell=True)
        
        if process.returncode != 0:
            messagebox.showerror("Error", f"Failed to install Rokit (code: {process.returncode})")
            return False
        
        if not self.refresh_path():
            messagebox.showwarning("Warning", "Rokit installed but PATH refresh failed. Please restart.")
            return False
        
        print("Rokit installed successfully")
        return True
    
    def trust_all_tools(self):
        """Trust all tools in rokit.toml"""
        result = self.utils.run_command('rokit trust --all')
        
        if result.returncode != 0:
            # Fallback: trust individual tools via their managers
            self.rojo_mgr.trust_rojo()
            self.lune_mgr.trust_lune()
        
        return True
    
    def install_tools(self):
        """Install all tools from rokit.toml"""
        if not self.is_rokit_installed():
            if not self.install_rokit():
                return False
        
        # Check if tools already exist
        if self.rojo_mgr.is_installed() and self.lune_mgr.is_installed():
            print("Tools already installed")
            return True
        
        print("Installing tools from rokit.toml...")
        
        # Trust all tools
        self.trust_all_tools()
        
        # Install via rokit.toml
        result = self.utils.run_command('rokit install')
        
        if result.returncode != 0:
            # Fallback: install individually via managers
            print("Bulk install failed, installing individually...")
            rojo_ok = self.rojo_mgr.install()
            lune_ok = self.lune_mgr.install()
            return rojo_ok and lune_ok
        
        print("Tools installed successfully")
        return True
    
    # Delegation methods for convenient access
    
    def install_rojo(self):
        """Delegate to RojoManager for Rojo installation"""
        return self.rojo_mgr.install()
    
    def install_lune(self):
        """Delegate to LuneManager for Lune installation"""
        return self.lune_mgr.install()
    
    def install_rojo_plugin(self):
        """Delegate to PluginManager for plugin installation"""
        return self.plugin_mgr.install_rojo_plugin()
