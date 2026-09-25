#!/usr/bin/env python3
"""
Rojo Server Management for Asset Trust Monitor

Handles Rojo server lifecycle, status monitoring, and plugin management.
"""

import os
import platform
import subprocess
import threading
import time
from tkinter import messagebox

class RojoServer:
    """Manages Rojo server operations and status monitoring"""
    
    def __init__(self, config):
        self.config = config
        self.process = None
        self.pid = None
        self._running = False
        self._status_callbacks = []
    
    def start(self):
        """Start the Rojo server"""
        if self._running:
            return True
        
        try:
            if platform.system() == 'Windows':
                self.process = subprocess.Popen(['rojo', 'serve'], 
                                              cwd=self.config.rojo_cwd, 
                                              creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif platform.system() == 'Darwin':
                self.process = subprocess.Popen(['rojo', 'serve'], 
                                              cwd=self.config.rojo_cwd, 
                                              shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.pid = self.process.pid
            self._running = True
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Rojo server: {e}")
            return False
    
    def stop(self):
        """Stop the Rojo server"""
        if not self.pid:
            return
        
        try:
            if platform.system() == "Windows":
                subprocess.run(['taskkill', '/F', '/PID', str(self.pid)], 
                             capture_output=True, check=False)
            else:
                import signal
                os.kill(self.pid, signal.SIGTERM)
            
            self._running = False
            self.pid = None
            return True
        except Exception as e:
            print(f"Error stopping Rojo server: {e}")
            return False

    def is_running(self):
        """Check if server is currently running"""
        if not self.pid:
            return False
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rojo.exe'], 
                                      capture_output=True, text=True)
                server_running = "rojo.exe" in result.stdout and "No tasks are running" not in result.stdout
            elif platform.system() == "Darwin":
                result = subprocess.run(['ps', '-p', str(self.pid)], 
                                      capture_output=True, text=True)
                server_running = result.returncode == 0 and 'rojo' in result.stdout
                
                if not server_running:
                    print(f"Rojo server PID {self.pid} is no longer running")
                    self.pid = None
                    self._running = False
            
            return server_running
        except Exception as e:
            print(f"Error checking server status: {e}")
            return False
    
    def add_status_callback(self, callback):
        """Add a callback function to be called when status changes"""
        self._status_callbacks.append(callback)
    
    def start_status_monitoring(self):
        """Start background thread to monitor server status"""
        def monitor_loop():
            while True:
                time.sleep(5)
                try:
                    is_running = self.is_running()
                    for callback in self._status_callbacks:
                        callback(is_running)
                except Exception as e:
                    print(f"Error in status monitoring: {e}")
                    time.sleep(1)
        
        threading.Thread(target=monitor_loop, daemon=True).start()
    
    def check_plugin_installed(self):
        """Check if Rojo plugin is installed"""
        def get_roblox_plugins_dir():
            home = os.path.expanduser("~")
            system = platform.system()
            if system == "Windows":
                return os.path.join(home, "AppData", "Local", "Roblox", "Plugins")
            elif system == "Darwin":
                return os.path.join(home, "Documents", "Roblox", "Plugins")
            else:
                return os.path.join(home, "Roblox", "Plugins")

        plugins_dir = get_roblox_plugins_dir()
        plugin_file = "RojoManagedPlugin.rbxm"
        plugin_path = os.path.join(plugins_dir, plugin_file)

        if os.path.isfile(plugin_path):
            return True
        else:
            return self._install_plugin()
    
    def _install_plugin(self):
        """Install Rojo plugin"""
        try:
            system = platform.system()
            if system == "Windows":
                run_process = subprocess.run("rojo plugin install", 
                                           cwd=self.config.rojo_cwd, 
                                           shell=True, capture_output=True, text=True)
            else:
                run_process = subprocess.run(['rojo', 'plugin', 'install'], 
                                           cwd=self.config.rojo_cwd, 
                                           shell=False, capture_output=True, text=True)
            
            if run_process.returncode == 0:
                return True
            else:
                messagebox.showerror("Error", f"Error running 'rojo plugin install': {run_process.stderr}")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Error running 'rojo plugin install': {e}")
            return False
    
    def run_lune_script(self):
        """Execute Lune script for processing"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run('lune run lune/init.luau', 
                                      shell=True, cwd=self.config.rojo_cwd, 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(['lune', 'run', 'lune/init.luau'], 
                                      cwd=self.config.rojo_cwd, 
                                      capture_output=True, text=True)

            if result.returncode == 0:
                return True
            else:
                messagebox.showerror("Error", f"Error running lune script:\n\nStderr: {result.stderr}\nStdout: {result.stdout}")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Error running lune script: {e}")
            return False
        
    def restart(self):
        """Refresh Rojo server"""
        # Restart Rojo server
        self.stop()
        if self.start():
            print("Rojo Server Restarted")
            return True
        else:
            print("Failed to restart Rojo server")
            return False
