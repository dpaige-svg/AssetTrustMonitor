#!/usr/bin/env python3
"""
Process Management Utilities

Centralized process management for killing, checking, and monitoring processes.
"""

import os
import platform
import subprocess
import signal
import time


class ProcessManager:
    """Handles process lifecycle operations across platforms"""
    
    def __init__(self, utils=None):
        self.is_windows = platform.system() == "Windows"
        self.utils = utils

    def _run(self, command, **kwargs):
        """Run an owned helper without creating a Windows console window."""
        if self.is_windows:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            kwargs.setdefault("startupinfo", startupinfo)
            kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
        kwargs.setdefault("check", False)
        return subprocess.run(command, **kwargs)
    
    def kill_process(self, pid, force=True):
        """
        Kill a process by PID
        
        Args:
            pid: Process ID to kill
            force: Use force kill (SIGKILL on Unix, /F on Windows)
            
        Returns:
            bool: True if successful
        """
        if not pid:
            return False
        
        try:
            if self.is_windows:
                # Windows: Use taskkill
                flags = ['/F', '/T'] if force else ['/T']
                cmd = ['taskkill'] + flags + ['/PID', str(pid)]
                
                result = self.utils.run_command(cmd) if self.utils else \
                         self._run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            else:
                # Unix-like systems: Use os.kill
                sig = signal.SIGKILL if force else signal.SIGTERM
                os.kill(pid, sig)
                return True
        except Exception as e:
            print(f"Error killing process {pid}: {e}")
            return False

    def kill_process_group(self, pid, force=True):
        """
        Kill the process group for a PID (Unix only).

        Args:
            pid: Member PID of the process group
            force: Use SIGKILL when True, SIGTERM when False

        Returns:
            bool: True if signal was delivered
        """
        if not pid or self.is_windows:
            return False

        try:
            pgid = os.getpgid(pid)
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.killpg(pgid, sig)
            return True
        except Exception as e:
            print(f"Error killing process group for {pid}: {e}")
            return False
    
    def is_process_running(self, pid, process_name=None):
        """
        Check if a process is running
        
        Args:
            pid: Process ID to check
            process_name: Optional process name to verify (Windows only)
            
        Returns:
            bool: True if process is running
        """
        if not pid:
            return False
        
        try:
            if self.is_windows:
                # Windows: Use tasklist
                cmd = ['tasklist', '/FI', f'PID eq {pid}']
                result = self.utils.run_command(cmd) if self.utils else \
                         self._run(cmd, capture_output=True, text=True)
                
                is_running = str(pid) in result.stdout
                
                # Verify process name if provided (case-insensitive)
                if process_name and is_running:
                    is_running = process_name.lower() in result.stdout.lower()
                
                return is_running
            else:
                # Unix-like systems: Use ps
                if process_name:
                    # Check name if provided
                    cmd = ['ps', '-p', str(pid), '-o', 'comm=']
                    result = self.utils.run_command(cmd) if self.utils else \
                             self._run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        return False
                        
                    # Check if process name matches
                    current_name = result.stdout.strip()
                    return process_name.lower() in current_name.lower()
                else:
                    # Just check existence
                    cmd = ['ps', '-p', str(pid)]
                    result = self.utils.run_command(cmd) if self.utils else \
                             self._run(cmd, capture_output=True, text=True)
                    return result.returncode == 0
        except Exception as e:
            print(f"Error checking process {pid}: {e}")
            return False
    
    def wait_for_process_exit(self, pid, timeout=10, process_name=None):
        """
        Wait for a process to exit
        
        Args:
            pid: Process ID to wait for
            timeout: Maximum seconds to wait
            process_name: Optional process name (for verification)
            
        Returns:
            bool: True if process exited, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_process_running(pid, process_name):
                return True
            time.sleep(0.2)
        
        return False
    
    def graceful_kill(self, pid, process_name=None, timeout=5):
        """
        Attempt graceful kill, escalate to force if needed
        
        Args:
            pid: Process ID to kill
            process_name: Optional process name
            timeout: Seconds to wait before force kill
            
        Returns:
            bool: True if process was killed
        """
        if not self.is_process_running(pid, process_name):
            return True
        
        # Try graceful termination
        if not self.is_windows:
            try:
                os.kill(pid, signal.SIGTERM)
                if self.wait_for_process_exit(pid, timeout, process_name):
                    print(f"Process {pid} terminated gracefully (SIGTERM)")
                    return True
            except OSError as error:
                print(f"Graceful termination of process {pid} failed: {error}")
        
        # Force kill
        print(f"Forcing termination of process {pid}")
        success = self.kill_process(pid, force=True)
        
        if success:
            self.wait_for_process_exit(pid, 3, process_name)
        
        return success

    def graceful_kill_group(self, pid, process_name=None, timeout=5):
        """
        Attempt graceful group kill (Unix), then force group kill.

        Args:
            pid: Member PID of the process group
            process_name: Optional process name check for exit wait
            timeout: Seconds to wait before force kill

        Returns:
            bool: True if process exited
        """
        if self.is_windows:
            return self.graceful_kill(pid, process_name=process_name, timeout=timeout)

        if not self.is_process_running(pid, process_name):
            return True

        try:
            if self.kill_process_group(pid, force=False) and self.wait_for_process_exit(pid, timeout, process_name):
                print(f"Process group for {pid} terminated gracefully (SIGTERM)")
                return True
        except OSError as error:
            print(f"Graceful termination of process group {pid} failed: {error}")

        print(f"Forcing termination of process group for {pid}")
        success = self.kill_process_group(pid, force=True)
        if success:
            self.wait_for_process_exit(pid, 3, process_name)

        return success
    
    def terminate_process_by_name(self, process_name):
        """
        Terminate all processes matching the given name
        
        Args:
            process_name: Name of the process to terminate
            
        Returns:
            bool: True if successful
        """
        try:
            if self.is_windows:
                # Windows: Use taskkill
                cmd = ['taskkill', '/F', '/IM', process_name]
                result = self.utils.run_command(cmd) if self.utils else \
                         self._run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            else:
                # Unix-like systems: Use pkill
                cmd = ['pkill', '-f', process_name]
                result = self.utils.run_command(cmd) if self.utils else \
                         self._run(cmd, capture_output=True, text=True)
                # pkill returns 1 when no processes matched; treat as "already stopped".
                return result.returncode in (0, 1)
        except Exception as e:
            print(f"Error terminating process {process_name}: {e}")
            return False    
