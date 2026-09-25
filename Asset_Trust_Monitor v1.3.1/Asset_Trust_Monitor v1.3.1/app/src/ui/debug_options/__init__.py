"""
Debug menu options module
"""
from .base import DebugOption
from .restart_section import RestartSection
from .trash_section import TrashSection
from .maintenance_section import MaintenanceSection


# List of all available debug sections
DEBUG_SECTIONS = [
    RestartSection,
    TrashSection,
    MaintenanceSection,
]