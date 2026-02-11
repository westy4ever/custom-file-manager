"""
WG File Manager Pro - Advanced Dual-Pane File Manager for Enigma2
Python 2.7 and 3.x compatible

Features:
- Visual dual-pane interface
- Arrow navigation
- Visual progress bars
- File operations (copy, move, delete, rename)
- File permission management
- Mark/unmark files for batch operations
- Media file support
- Network/cloud integration ready
- Configurable settings
"""

__version__ = "1.2.0"
__author__ = "WG File Manager Team"

from .core.config import get_config
from .core.file_ops import FileOperations
from .ui.main_screen import create_main_screen, WGFileManagerMain
from .ui.pane import EnhancedFileList, FilePane
from .ui.progress import create_progress_dialog, OperationProgressDialog
from .ui.permission_dialog import PermissionDialog
from .utils.formatters import format_permissions_with_octal, get_permissions_string, get_permissions_octal
from .utils.logger import get_logger, set_debug_mode, log_operation

__all__ = [
    'get_config', 
    'FileOperations', 
    'create_main_screen',
    'WGFileManagerMain',
    'EnhancedFileList',
    'FilePane',
    'create_progress_dialog',
    'OperationProgressDialog',
    'PermissionDialog',
    'format_permissions_with_octal',
    'get_permissions_string',
    'get_permissions_octal',
    'get_logger',
    'set_debug_mode',
    'log_operation'
]