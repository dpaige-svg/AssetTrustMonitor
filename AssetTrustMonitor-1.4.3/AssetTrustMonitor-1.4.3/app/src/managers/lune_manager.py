#!/usr/bin/env python3
"""
Lune Manager

Handles Lune installation, verification, and script execution.
"""

from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils


class LuneManager:
    """Manages Lune installation and script execution"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
    
    def is_installed(self):
        """Check if Lune is installed"""
        return self.config.tool_exists('lune')
    
    def get_version(self):
        """Get installed Lune version"""
        if not self.is_installed():
            return None
        
        try:
            result = self.utils.run_command(['lune', '--version'])
            if result.returncode == 0:
                version = result.stdout.strip()
                return version
            return None
        except Exception as e:
            print(f"Error getting Lune version: {e}")
            return None
    
    def trust_lune(self):
        """Trust Lune tool in Rokit"""
        result = self.utils.run_command(['rokit', 'trust', 'lune-org/lune'])
        return result.returncode == 0
    
    def install(self):
        """Install Lune via Rokit"""
        if self.is_installed():
            print("Lune already installed")
            return True
        
        print("Installing Lune...")
        
        # Trust the tool first
        self.trust_lune()
        
        # Install via rokit
        result = self.utils.run_command(['rokit', 'install', 'lune-org/lune'])
        
        if result.returncode != 0:
            error_msg = f"Failed to install Lune: {result.stderr}"
            print(error_msg)
            messagebox.showerror("Lune Installation Error", error_msg)
            return False
        
        print("Lune installed successfully")
        return True
    
    def verify_installation(self):
        """Verify Lune is properly installed and accessible"""
        if not self.is_installed():
            error_msg = "Lune is not installed or not found in PATH"
            print(error_msg)
            messagebox.showerror("Lune Error", error_msg)
            return False
        
        version = self.get_version()
        if version:
            print(f"Lune verified: {version}")
            return True
        else:
            error_msg = "Lune is installed but cannot get version"
            print(error_msg)
            messagebox.showwarning("Lune Warning", error_msg)
            return False
    
    def run_script(self, script_path, args=None, *, show_error=True):
        """
        Execute a Lune script
        
        Args:
            script_path: Path to the .luau script file (relative to rojo_cwd)
        
        Returns:
            bool: True if script executed successfully
        """
        try:
            print(f"Running Lune script: {script_path}")
            command = ['lune', 'run', script_path]
            if args:
                command.extend(str(value) for value in args)
            result = self.utils.run_command(command)
            
            if result.returncode == 0:
                print(f"Lune script completed successfully")
                if result.stdout:
                    print(f"Output: {result.stdout}")
                return True
            else:
                error_msg = f"Lune script failed:\nStderr: {result.stderr}\nStdout: {result.stdout}"
                print(error_msg)
                if show_error:
                    messagebox.showerror("Lune Script Error", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Failed to run Lune script: {e}"
            print(error_msg)
            if show_error:
                messagebox.showerror("Lune Script Error", error_msg)
            return False
    
    def run_init_script(self, asset_filename=None):
        """Process one model in isolation so a bad asset cannot stop the batch."""
        args = [asset_filename] if asset_filename else None
        return self.run_script('lune/init.luau', args, show_error=False)
