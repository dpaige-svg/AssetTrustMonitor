"""
Debug menu options module
"""
from .base import DebugOption as DebugOption
from .maintenance_section import MaintenanceSection
from .regex_section import RegexSection
from .restart_section import RestartSection
from .trash_section import TrashSection

# List of all available debug sections
DEBUG_SECTIONS = [
    RestartSection,
    TrashSection,
    RegexSection,
    MaintenanceSection,
]
