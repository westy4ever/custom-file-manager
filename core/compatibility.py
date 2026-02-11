"""
Python 2.7 and 3.x compatibility layer
Ensures code works seamlessly across both versions
"""

from __future__ import absolute_import, division, print_function
import sys
import os
import re

# Version detection
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

# String types
if PY3:
    string_types = str
    text_type = str
    binary_type = bytes
    from io import StringIO, BytesIO
    import queue as Queue
    from urllib.parse import quote, unquote, urlparse
    import configparser as ConfigParser
else:
    string_types = basestring
    text_type = unicode
    binary_type = str
    from StringIO import StringIO
    from io import BytesIO
    import Queue
    from urllib import quote, unquote
    from urlparse import urlparse
    import ConfigParser

# File handling
if PY3:
    import builtins
    open_file = builtins.open
else:
    import __builtin__
    open_file = __builtin__.open


def ensure_str(s):
    """
    Convert to str (bytes in PY2, unicode in PY3)
    
    Args:
        s: Input string/bytes/unicode
        
    Returns:
        str: Native str type for current Python version
    """
    if s is None:
        return ''
    
    if PY2:
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return str(s)
    else:
        if isinstance(s, bytes):
            return s.decode('utf-8', errors='replace')
        return str(s)


def ensure_unicode(s):
    """
    Convert to unicode string
    
    Args:
        s: Input string/bytes
        
    Returns:
        unicode/str: Unicode string
    """
    if s is None:
        return u''
    
    if PY2:
        if isinstance(s, str):
            return s.decode('utf-8', errors='replace')
        return unicode(s)
    else:
        if isinstance(s, bytes):
            return s.decode('utf-8', errors='replace')
        return str(s)


def ensure_bytes(s):
    """
    Convert to bytes
    
    Args:
        s: Input string/unicode
        
    Returns:
        bytes: Byte string
    """
    if s is None:
        return b''
    
    if PY2:
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return str(s)
    else:
        if isinstance(s, str):
            return s.encode('utf-8')
        return bytes(s)


def safe_listdir(path):
    """
    List directory with proper unicode handling
    
    Args:
        path: Directory path
        
    Returns:
        list: List of filenames (unicode)
    """
    try:
        items = os.listdir(ensure_str(path))
        return [ensure_unicode(item) for item in items]
    except OSError as e:
        return []


def safe_join(*args):
    """
    Join paths with proper encoding
    
    Args:
        *args: Path components
        
    Returns:
        str: Joined path
    """
    return os.path.join(*[ensure_str(arg) for arg in args])


def get_filesystem_encoding():
    """Get filesystem encoding"""
    return sys.getfilesystemencoding() or 'utf-8'


def is_valid_path(path):
    """
    Check if path is valid and accessible
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if valid and accessible
    """
    try:
        path = ensure_str(path)
        return os.path.exists(path)
    except:
        return False


def get_parent_path(path):
    """
    Get parent directory path
    
    Args:
        path: File/directory path
        
    Returns:
        str: Parent directory path
    """
    try:
        return os.path.dirname(ensure_str(path))
    except:
        return '/'


def get_basename(path):
    """
    Get basename of path
    
    Args:
        path: File/directory path
        
    Returns:
        str: Basename
    """
    try:
        return os.path.basename(ensure_str(path))
    except:
        return ''


def normalize_path(path):
    """
    Normalize path (remove . and .., convert to absolute)
    
    Args:
        path: Path to normalize
        
    Returns:
        str: Normalized path
    """
    try:
        return os.path.normpath(ensure_str(path))
    except:
        return path


def path_exists(path):
    """
    Check if path exists (with error handling)
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if exists
    """
    try:
        return os.path.exists(ensure_str(path))
    except:
        return False


def is_directory(path):
    """
    Check if path is a directory
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if directory
    """
    try:
        return os.path.isdir(ensure_str(path))
    except:
        return False


def is_file(path):
    """
    Check if path is a file
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if file
    """
    try:
        return os.path.isfile(ensure_str(path))
    except:
        return False


def is_symlink(path):
    """
    Check if path is a symbolic link
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if symlink
    """
    try:
        return os.path.islink(ensure_str(path))
    except:
        return False


def get_file_size(path):
    """
    Get file size in bytes
    
    Args:
        path: File path
        
    Returns:
        int: File size in bytes, or 0 if error
    """
    try:
        return os.path.getsize(ensure_str(path))
    except:
        return 0


def get_file_mtime(path):
    """
    Get file modification time
    
    Args:
        path: File path
        
    Returns:
        float: Modification timestamp, or 0 if error
    """
    try:
        return os.path.getmtime(ensure_str(path))
    except:
        return 0


def create_directory(path):
    """
    Create directory (including parent directories)
    
    Args:
        path: Directory path to create
        
    Returns:
        bool: True if successful
    """
    try:
        os.makedirs(ensure_str(path), exist_ok=True)
        return True
    except:
        return False


def remove_file(path):
    """
    Remove file
    
    Args:
        path: File path to remove
        
    Returns:
        bool: True if successful
    """
    try:
        os.remove(ensure_str(path))
        return True
    except:
        return False


def remove_directory(path):
    """
    Remove directory
    
    Args:
        path: Directory path to remove
        
    Returns:
        bool: True if successful
    """
    try:
        import shutil
        shutil.rmtree(ensure_str(path))
        return True
    except:
        return False


def copy_file(src, dst):
    """
    Copy file
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        bool: True if successful
    """
    try:
        import shutil
        shutil.copy2(ensure_str(src), ensure_str(dst))
        return True
    except:
        return False


def move_file(src, dst):
    """
    Move/rename file
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        bool: True if successful
    """
    try:
        import shutil
        shutil.move(ensure_str(src), ensure_str(dst))
        return True
    except:
        return False


def compare_paths(path1, path2):
    """
    Compare two paths (normalized)
    
    Args:
        path1: First path
        path2: Second path
        
    Returns:
        bool: True if paths are the same
    """
    try:
        return normalize_path(path1) == normalize_path(path2)
    except:
        return False


def get_common_path(paths):
    """
    Get common parent directory for multiple paths
    
    Args:
        paths: List of paths
        
    Returns:
        str: Common parent directory
    """
    if not paths:
        return '/'
    
    try:
        common = os.path.commonprefix([ensure_str(p) for p in paths])
        # Ensure it ends with directory separator
        if common and not common.endswith(os.sep):
            common = os.path.dirname(common)
        return common or '/'
    except:
        return '/'


# Metaclass compatibility
def add_metaclass(metaclass):
    """
    Class decorator for creating a class with a metaclass.
    Compatible with both Python 2 and 3.
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


# Navigation helpers
class NavigationHelper:
    """Helper class for navigation operations"""
    
    @staticmethod
    def get_navigation_index(current_index, total_items, direction='down', wrap_around=True):
        """
        Calculate new navigation index
        
        Args:
            current_index: Current selection index
            total_items: Total number of items
            direction: 'up', 'down', 'pageup', 'pagedown'
            wrap_around: Enable wrap-around navigation
            
        Returns:
            int: New index
        """
        if total_items <= 0:
            return 0
        
        if direction == 'up':
            new_index = current_index - 1
            if new_index < 0:
                return total_items - 1 if wrap_around else 0
            return new_index
        
        elif direction == 'down':
            new_index = current_index + 1
            if new_index >= total_items:
                return 0 if wrap_around else total_items - 1
            return new_index
        
        elif direction == 'pageup':
            new_index = current_index - 10
            if new_index < 0:
                return 0 if not wrap_around else total_items - 1
            return new_index
        
        elif direction == 'pagedown':
            new_index = current_index + 10
            if new_index >= total_items:
                return total_items - 1 if not wrap_around else 0
            return new_index
        
        return current_index
    
    @staticmethod
    def find_item_by_name(items, name, start_index=0):
        """
        Find item by name (case-insensitive search)
        
        Args:
            items: List of items (each item should have get_name() or be tuple with name at index 2)
            name: Name to search for
            start_index: Index to start search from
            
        Returns:
            int: Index of found item, or -1 if not found
        """
        if not items or not name:
            return -1
        
        name_lower = ensure_unicode(name).lower()
        
        for i in range(len(items)):
            idx = (start_index + i) % len(items)
            item = items[idx]
            
            # Try different ways to get the name
            item_name = None
            if hasattr(item, 'get_name'):
                item_name = item.get_name()
            elif isinstance(item, (list, tuple)) and len(item) > 2:
                item_name = item[2]
            elif isinstance(item, dict) and 'name' in item:
                item_name = item['name']
            
            if item_name and ensure_unicode(item_name).lower().startswith(name_lower):
                return idx
        
        return -1


# Export all compatibility items
__all__ = [
    'PY2', 'PY3',
    'string_types', 'text_type', 'binary_type',
    'StringIO', 'BytesIO', 'Queue',
    'quote', 'unquote', 'urlparse',
    'ConfigParser',
    'ensure_str', 'ensure_unicode', 'ensure_bytes',
    'safe_listdir', 'safe_join',
    'get_filesystem_encoding',
    'add_metaclass',
    'NavigationHelper',
    'is_valid_path', 'get_parent_path', 'get_basename',
    'normalize_path', 'path_exists', 'is_directory',
    'is_file', 'is_symlink', 'get_file_size',
    'get_file_mtime', 'create_directory', 'remove_file',
    'remove_directory', 'copy_file', 'move_file',
    'compare_paths', 'get_common_path',
]