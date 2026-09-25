#!/usr/bin/env python3
"""
Rokit and Tool Management for Asset Trust Monitor

Handles installation, configuration, and management of Rokit, Lune, and Rojo tools.
"""

import os
import platform
import subprocess
import shutil
from tkinter import messagebox

class RokitManager:
    """Manages Rokit toolchain installation and configuration"""
    
    def __init__(self, config):
        self.config = config
    
    def refresh_paths(self):
        """Refresh PATH to include rokit binaries"""
        system = platform.system()

        if system == 'Windows':
            # Update Python's PATH
            rokit_path = os.path.expanduser("~\\.rokit\\bin")
            os.environ["PATH"] = rokit_path + ";" + os.environ.get("PATH", "")

            # Run PowerShell command to refresh shell PATH from registry
            powershell_command = (
                '$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + '
                '[System.Environment]::GetEnvironmentVariable("Path", "Machine")'
            )
            subprocess.run(["powershell", "-Command", powershell_command], shell=True)

        elif system == 'Darwin':
            # Update Python's PATH
            rokit_path = os.path.expanduser("~/.rokit/bin")
            os.environ["PATH"] = rokit_path + os.pathsep + os.environ.get("PATH", "")

        # Confirm Rokit is now discoverable
        return shutil.which("rokit") is not None
    
    def check_and_install_rokit(self):
        """Check if rokit is installed, if not install it"""
        windows_command = 'Invoke-RestMethod https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.ps1 | Invoke-Expression'
        mac_command = 'curl -sSf https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.sh | bash'

        system = platform.system()
        
        def update_rokit():
            if platform.system() == "Windows":
                ran = subprocess.run("rokit update", cwd=self.config.rojo_cwd, shell=True, capture_output=True, text=True)
            else:
                ran = subprocess.run(['rokit', 'update'], cwd=self.config.rojo_cwd, shell=False, capture_output=True, text=True)
            return ran.returncode == 0
        
        if not self.refresh_paths():
            if system == 'Windows':
                process = subprocess.run(["powershell", "-Command", windows_command], shell=True)
                if process.returncode == 0:
                    if self.refresh_paths():
                        return update_rokit()
                    else:
                        messagebox.showwarning("Warning", "Rokit installed but PATH refresh failed. Please restart your terminal or computer.")
                        return False
                else:
                    messagebox.showerror("Error", f"Error installing Rokit. Return code: {process.returncode}")
                    return False
            elif system == 'Darwin':
                process = subprocess.run(mac_command, shell=True)
                if process.returncode == 0:
                    if self.refresh_paths():
                        return update_rokit()
                    else:
                        messagebox.showwarning("Warning", "Rokit installed but PATH refresh failed. Please restart your terminal or computer.")
                        return False
                else:
                    messagebox.showerror("Error", f"Error installing Rokit. Return code: {process.returncode}")
                    return False
        else:
            return update_rokit()
    
    def _add_lune(self):
        """Add lune extension to rokit"""
        if platform.system() == "Windows":
            result = subprocess.run('rokit add lune-org/lune', capture_output=True, text=True, shell=True, cwd=self.config.rojo_cwd)
        else:
            result = subprocess.run(['rokit', 'add', 'lune-org/lune'], capture_output=True, text=True, cwd=self.config.rojo_cwd)
        
        if result.returncode == 0:
            return result
        else:
            return self._trust_lune()
    
    def _trust_lune(self):
        """Trust lune extension in rokit"""
        if platform.system() == "Windows":
            result = subprocess.run('rokit trust lune-org/lune', capture_output=True, text=True, shell=True, cwd=self.config.rojo_cwd)
        else:
            result = subprocess.run(['rokit', 'trust', 'lune-org/lune'], capture_output=True, text=True, cwd=self.config.rojo_cwd)
        
        if result.returncode == 0:
            return True
        else:
            messagebox.showerror("Error", f"Error trusting Lune: {result.stderr}")
            print(result.stderr)
            return False
    
    def _add_rojo(self):
        """Add rojo extension to rokit"""
        if platform.system() == "Windows":
            result = subprocess.run('rokit add rojo-rbx/rojo', capture_output=True, text=True, shell=True, cwd=self.config.rojo_cwd)
        else:
            result = subprocess.run(['rokit', 'add', 'rojo-rbx/rojo'], capture_output=True, text=True, cwd=self.config.rojo_cwd)
        
        if result.returncode == 0:
            return result
        else:
            messagebox.showerror("Error", f"Error adding Rojo: {result.stderr}")
            print(result.stderr)
            return False
    
    def integrate_lune_with_rojo(self):
        """Integrate lune and rojo with rokit using rokit.toml"""
        def check_rokit_tool_executable(tool_name):
            if platform.system() == "Windows":
                rokit_bin = os.path.expanduser("~\\.rokit\\bin")
                tool_path = os.path.join(rokit_bin, f"{tool_name}.exe")
                return os.path.isfile(tool_path)
            else:
                rokit_bin = os.path.expanduser("~/.rokit/bin")
                tool_path = os.path.join(rokit_bin, tool_name)
                return os.path.isfile(tool_path)
        
        lune_executable = check_rokit_tool_executable("lune")
        rojo_executable = check_rokit_tool_executable("rojo")
        
        if lune_executable and rojo_executable:
            return True
        
        try:
            # First, update rokit.toml to latest versions if needed
            if platform.system() == "Windows":
                update_result = subprocess.run('rokit update', shell=True, cwd=self.config.rojo_cwd, capture_output=True, text=True)
            else:
                update_result = subprocess.run(['rokit', 'update'], cwd=self.config.rojo_cwd, capture_output=True, text=True)
            
            if update_result.returncode != 0:
                print(f"Warning: rokit update failed: {update_result.stderr}")
            
            # Trust all tools in rokit.toml
            if platform.system() == "Windows":
                trust_result = subprocess.run('rokit trust --all', shell=True, cwd=self.config.rojo_cwd, capture_output=True, text=True)
            else:
                trust_result = subprocess.run(['rokit', 'trust', '--all'], cwd=self.config.rojo_cwd, capture_output=True, text=True)
            
            if trust_result.returncode != 0:
                # Fallback: trust individual tools
                if platform.system() == "Windows":
                    subprocess.run('rokit trust lune-org/lune', shell=True, cwd=self.config.rojo_cwd, capture_output=True, text=True)
                    subprocess.run('rokit trust rojo-rbx/rojo', shell=True, cwd=self.config.rojo_cwd, capture_output=True, text=True)
                else:
                    subprocess.run(['rokit', 'trust', 'lune-org/lune'], cwd=self.config.rojo_cwd, capture_output=True, text=True)
                    subprocess.run(['rokit', 'trust', 'rojo-rbx/rojo'], cwd=self.config.rojo_cwd, capture_output=True, text=True)
            
            # Install tools from rokit.toml
            if platform.system() == "Windows":
                install_result = subprocess.run('rokit install', shell=True, cwd=self.config.rojo_cwd, capture_output=True, text=True)
            else:
                install_result = subprocess.run(['rokit', 'install'], cwd=self.config.rojo_cwd, capture_output=True, text=True)
            
            if install_result.returncode == 0:
                # Verify tools are now executable
                lune_working = check_rokit_tool_executable("lune")
                rojo_working = check_rokit_tool_executable("rojo")
                
                if lune_working and rojo_working:
                    return True
                else:
                    print("Tools installed successfully. They will be available after PATH refresh.")
                    return True
            else:
                messagebox.showerror("Error", f"Error installing tools from rokit.toml: {install_result.stderr}")
                return False
                
        except Exception as e:
            messagebox.showerror("Error", f"Error during rokit installation: {str(e)}")
            return False