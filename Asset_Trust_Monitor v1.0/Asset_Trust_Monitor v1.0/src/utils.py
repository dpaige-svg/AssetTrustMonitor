#!/usr/bin/env python3
"""
Utility Functions for Asset Trust Monitor

Common utility functions used across the application.
"""

import random
import string

class Utils:
    """Collection of utility functions"""
    
    @staticmethod
    def generate_random_string(length=12):
        """Generate a random alphanumeric string for unique file names"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))