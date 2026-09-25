#!/usr/bin/env python3
"""
Studio Manager for Asset Trust Monitor

Handles Roblox Studio process lifecycle and PID tracking.
"""

import os
import platform
import subprocess
import signal
import time
from tkinter import messagebox


class StudioManager:
    """Manages Roblox Studio process operations"""
    
    def __init__(self, config):
        self.config = config
        self._pid = None
    
    @property
    def pid(self):
        """Get the current Roblox Studio PID"""
        return self._pid
    
    @pid.setter
    def pid(self, value):
        """Set the Roblox Studio PID"""
        self._pid = value
    
    def is_running(self):
        """Check if the tracked Studio process is currently running"""
        if not self._pid:
            return False
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {self._pid}"],
                    capture_output=True, text=True
                )
                # Check if PID exists in output
                return f" {self._pid} " in result.stdout or str(self._pid) in result.stdout.split()
            else:
                # macOS/Linux
                result = subprocess.run(
                    ["ps", "-p", str(self._pid)],
                    capture_output=True, text=True
                )
                return result.returncode == 0
        except Exception as e:
            print(f"Error checking Studio status: {e}")
            return False
    
    def start(self):
        """Open Roblox Studio with the project file"""
        if not os.path.isfile(self.config.rbxl_file_path):
            messagebox.showerror("Error", f"Project file not found: {self.config.rbxl_file_path}")
            return False
        
        try:
            if platform.system() == 'Windows':
                process = subprocess.Popen([self.config.rbxl_file_path], shell=True)
                self._pid = process.pid
            elif platform.system() == 'Darwin':
                # Try both common Roblox Studio locations
                studio_paths = [
                    '/Applications/Roblox Studio.app/Contents/MacOS/RobloxStudio',
                    '/Applications/RobloxStudio.app/Contents/MacOS/RobloxStudio',
                    '/Applications/RobloxStudio.app/Contents/MacOS/RobloxStudio.app/Contents/MacOS/RobloxStudio',
                ]
                studio_exec = None
                for path in studio_paths:
                    if os.path.isfile(path):
                        studio_exec = path
                        break
                if not studio_exec:
                    messagebox.showerror("Error", "Roblox Studio executable not found in standard locations. Please check your installation.")
                    return False
                process = subprocess.Popen(
                    [studio_exec, self.config.rbxl_file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._pid = process.pid
            else:
                messagebox.showerror("Error", "Unsupported platform")
                return False
            print(f"Roblox Studio Opened (PID: {self._pid})")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Roblox Studio: {e}")
            return False
    
    def stop(self):
        """Close the tracked Roblox Studio process"""
        if not self._pid:
            print("No Studio PID to close")
            return True
        
        try:
            print(f"Attempting to close Roblox Studio (PID: {self._pid})")
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(self._pid)],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    print("Roblox Studio closed successfully")
                    self._pid = None
                    return True
                else:
                    print(f"Failed to close Roblox Studio: {result.stderr}")
                    return False
            else:
                try:
                    os.kill(self._pid, signal.SIGTERM)
                    print("Roblox Studio termination signal sent (SIGTERM)")
                    # Wait briefly to see if process exits
                    for _ in range(10):
                        time.sleep(0.2)
                        result = subprocess.run(["ps", "-p", str(self._pid)], capture_output=True, text=True)
                        if result.returncode != 0:
                            print("Roblox Studio closed successfully (SIGTERM)")
                            self._pid = None
                            return True
                    # If still running, escalate to SIGKILL
                    print("SIGTERM did not close Studio, sending SIGKILL")
                    os.kill(self._pid, signal.SIGKILL)
                    for _ in range(10):
                        time.sleep(0.2)
                        result = subprocess.run(["ps", "-p", str(self._pid)], capture_output=True, text=True)
                        if result.returncode != 0:
                            print("Roblox Studio closed successfully (SIGKILL)")
                            self._pid = None
                            return True
                    print("Failed to close Roblox Studio with SIGKILL")
                    return False
                except Exception as e:
                    print(f"Error closing Roblox Studio: {e}")
                    return False
        except Exception as e:
            print(f"Error closing Roblox Studio: {e}")
            return False
    
    def restart(self):
        """Restart Roblox Studio"""
        print("Restarting Roblox Studio...")
        self.stop()
        return self.start()
