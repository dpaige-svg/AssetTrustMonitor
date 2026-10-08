#!/usr/bin/env python3
"""
Icon Management for Asset Trust Monitor

Handles loading and processing of icon files.
"""



class IconManager:
    """Manages icon loading and processing"""
    
    def __init__(self, config):
        """
        Initialize icon manager
        
        Args:
            config: Config instance with icon path methods
        """
        self.config = config
    
    def get_icons(self):
        """
        Get all loaded icons as a dictionary
        
        Returns:
            Dictionary with keys 'start', 'stop', 'trash'
        """
        return {}
