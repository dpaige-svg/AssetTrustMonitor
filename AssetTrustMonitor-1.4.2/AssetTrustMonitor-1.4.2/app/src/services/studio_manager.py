#!/usr/bin/env python3
"""
Roblox Studio Management

Handles Studio process lifecycle and monitoring.
"""

import os
import platform
import subprocess

from tkinter import messagebox

from ..core.config import Config
from ..core.process_manager import ProcessManager


class StudioManager:
    """Manages Roblox Studio process"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.process_mgr = ProcessManager()
        self.is_windows = platform.system() == 'Windows'
        self.is_darwin = platform.system() == 'Darwin'
        self._pid = None
    
    @property
    def pid(self):
        """Get current Studio PID"""
        return self._pid
    
    @pid.setter
    def pid(self, value):
        """Set Studio PID"""
        self._pid = value
    
    def start(self):
        """Open Roblox Studio with project file"""
        if not os.path.isfile(self.config.rbxl_file_path):
            messagebox.showerror("Error", f"Project file not found: {self.config.rbxl_file_path}")
            return False
        
        try:
            if self.is_windows:
                process = subprocess.Popen([self.config.rbxl_file_path], shell=True)
                self._pid = process.pid
                
            elif self.is_darwin:
                # macOS Roblox Studio locations
                studio_paths = [
                    '/Applications/Roblox Studio.app/Contents/MacOS/RobloxStudio',
                    '/Applications/RobloxStudio.app/Contents/MacOS/RobloxStudio'
                ]
                
                studio_exec = None
                for path in studio_paths:
                    if os.path.isfile(path):
                        studio_exec = path
                        break
                
                if not studio_exec:
                    messagebox.showerror("Error", "Roblox Studio not found in standard locations")
                    return False
                
                process = subprocess.Popen(
                    [studio_exec, self.config.rbxl_file_path],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._pid = process.pid
            else:
                messagebox.showerror("Error", "Unsupported platform")
                return False
            
            print(f"Roblox Studio opened (PID: {self._pid})")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Roblox Studio: {e}")
            return False
    
    def stop(self):
        """Close Roblox Studio"""
        success = True

        if self._pid:
            print(f"Closing Roblox Studio (PID: {self._pid})")
            if self.is_darwin:
                success = self.process_mgr.graceful_kill_group(self._pid, process_name="RobloxStudio", timeout=5)
            else:
                success = self.process_mgr.graceful_kill(self._pid, timeout=5)
        else:
            print("No Studio PID available, using fallback shutdown")

        # macOS fallback paths for cases where child PID changes after launch.
        if self.is_darwin:
            try:
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        'tell application "Roblox Studio" to quit'
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass

            # Ensure all Studio processes are terminated if app-quit was ignored.
            self.process_mgr.terminate_process_by_name("RobloxStudio")
            self.process_mgr.terminate_process_by_name("Roblox Studio")

        self._pid = None
        print("Roblox Studio close sequence complete")
        return success
    
    def restart(self):
        """Restart Roblox Studio"""
        print("Restarting Roblox Studio...")
        self.stop()
        return self.start()
    
    def is_running(self):
        """Check if Studio is running"""
        if not self._pid:
            return False
        
        return self.process_mgr.is_process_running(self._pid)
