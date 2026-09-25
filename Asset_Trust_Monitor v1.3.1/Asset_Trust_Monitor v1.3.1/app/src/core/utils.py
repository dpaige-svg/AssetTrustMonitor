import sys
import tkinter as tk

#!/usr/bin/env python3
"""
Utility Functions for Asset Trust Monitor

Common utility functions and helpers.
"""

import random
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
            shell: Whether to use shell (None = auto-detect)
            cwd: Working directory (None = use default_cwd)
            capture_output: Whether to capture output
            text: Whether to return output as text
            
        Returns:
            subprocess.CompletedProcess object
        """
        if shell is None:
            shell = self.is_windows
        
        if cwd is None:
            cwd = self.default_cwd
        
        if self.is_windows and isinstance(command, str):
            return subprocess.run(command, shell=True, cwd=cwd, 
                                capture_output=capture_output, text=text)
        elif isinstance(command, str):
            return subprocess.run(command.split(), cwd=cwd, 
                                capture_output=capture_output, text=text)
        else:
            return subprocess.run(command, cwd=cwd, 
                                capture_output=capture_output, text=text)

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