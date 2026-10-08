#!/usr/bin/env python3
"""
Rojo Manager

Handles Rojo installation and verification.
"""

import os
import subprocess
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils


class RojoManager:
    """Manages Rojo installation and verification"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
    
    def is_installed(self):
        """Check if Rojo is installed"""
        return self.config.tool_exists('rojo')
    
    def get_version(self):
        """Get installed Rojo version"""
        if not self.is_installed():
            return None
        
        try:
            result = self.utils.run_command(['rojo', '--version'])
            if result.returncode == 0:
                # Output format: "Rojo 7.x.x"
                version = result.stdout.strip()
                return version
            return None
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            print(f"Error getting Rojo version: {e}")
            return None
    
    def trust_rojo(self):
        """Trust Rojo tool in Rokit"""
        result = self.utils.run_command(['rokit', 'trust', 'rojo-rbx/rojo'])
        return result.returncode == 0
    
    def install(self):
        """Install Rojo via Rokit"""
        if self.is_installed():
            print("Rojo already installed")
            return True
        
        print("Installing Rojo...")
        
        # Trust the tool first
        self.trust_rojo()
        
        # Install via rokit
        result = self.utils.run_command(['rokit', 'install', 'rojo-rbx/rojo'])
        
        if result.returncode != 0:
            error_msg = f"Failed to install Rojo: {result.stderr}"
            print(error_msg)
            messagebox.showerror("Rojo Installation Error", error_msg)
            return False
        
        print("Rojo installed successfully")
        return True
    
    def verify_installation(self):
        """Verify Rojo is properly installed and accessible"""
        if not self.is_installed():
            error_msg = "Rojo is not installed or not found in PATH"
            print(error_msg)
            messagebox.showerror("Rojo Error", error_msg)
            return False
        
        version = self.get_version()
        if version:
            print(f"Rojo verified: {version}")
            return True
        else:
            error_msg = "Rojo is installed but cannot get version"
            print(error_msg)
            messagebox.showwarning("Rojo Warning", error_msg)
            return False
        
    def remove_rojo(self):
        """Uninstall Rojo tool"""
        if not self.is_installed():
            print("Rojo is not installed")
            return True
        
        print("Uninstalling Rojo...")
        tool_path = self.config.get_tool_path('rojo')
        try:
            os.remove(tool_path)
            print("Rojo uninstalled successfully")
            return True
        except OSError as e:
            error_msg = f"Failed to uninstall Rojo: {e}"
            print(error_msg)
            messagebox.showerror("Rojo Uninstall Error", error_msg)
            return False
        
