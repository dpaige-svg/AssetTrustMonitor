import sys
import tkinter as tk

#!/usr/bin/env python3
"""
Utility Functions for Asset Trust Monitor

Common utility functions and helpers.
"""

import random
import shlex
import string
import platform
import subprocess


class Utils:
    """Collection of utility functions"""
    
    def __init__(self, default_cwd=None):
        self.is_windows = platform.system() == "Windows"
        self.default_cwd = default_cwd
    
    @staticmethod
    def generate_random_string(length=12):
        """Generate a random alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))
    
    def run_command(self, command, shell=None, cwd=None, capture_output=True, text=True):
        """
        Run commands with platform-specific handling
        
        Args:
            command: Command to run (string or list)
            shell: Whether to invoke a command shell (defaults to False)
            cwd: Working directory (None = use default_cwd)
            capture_output: Whether to capture output
            text: Whether to return output as text
            
        Returns:
            subprocess.CompletedProcess object
        """
        if shell is None:
            shell = False
        
        if cwd is None:
            cwd = self.default_cwd

        startupinfo = None
        creationflags = 0
        if self.is_windows:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            except (AttributeError, OSError):
                startupinfo = None
                creationflags = 0
        
        args = command
        if isinstance(command, str) and not shell:
            args = shlex.split(command, posix=not self.is_windows)

        return subprocess.run(
            args,
            shell=bool(shell),
            cwd=cwd,
            capture_output=capture_output,
            text=text,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

    def retry_function(self, func, retries=3, delay=1, *args, **kwargs):
        """
        Retry a function multiple times with delay
        
        Args:
            func: Function to retry
            retries: Number of retries
            delay: Delay between retries (seconds)
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function if successful, else raises last exception
        """
        import time
        
        last_exception = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                time.sleep(delay)
        
        raise last_exception
    
    def convert_emoji_to_solid_white(self, emoji):
        """
        Convert a Unicode emoji to its text (monochrome) variant for consistent rendering
        
        Args:
            emoji: Unicode emoji string
            
        Returns:
            Modified emoji string with text presentation variation selector
        """
        VARIATION_SELECTOR_15 = "\uFE0E"  # Text presentation (monochrome)
        VARIATION_SELECTOR_16 = "\uFE0F"  # Emoji presentation (colorful)
        
        # Force text presentation for consistent monochrome rendering
        if emoji.endswith(VARIATION_SELECTOR_16):
            return emoji[:-1] + VARIATION_SELECTOR_15
        elif not emoji.endswith(VARIATION_SELECTOR_15):
            return emoji + VARIATION_SELECTOR_15
        return emoji
