"""
Base class for debug menu options
"""


class DebugOption:
    """Base class for debug menu options"""
    
    def __init__(self, parent, config, managers):
        """
        Args:
            parent: Parent widget
            config: Config instance
            managers: Dict of manager instances (studio_manager, rojo_server, etc.)
        """
        self.parent = parent
        self.config = config
        self.managers = managers
        self.frame = None
    
    def create(self):
        """Create the UI for this debug option. Returns the frame."""
        raise NotImplementedError
    
    def get_required_managers(self):
        """Return list of required manager names"""
        return []