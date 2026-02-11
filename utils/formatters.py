"""
Utility functions for formatting and common operations
"""

from __future__ import absolute_import, division, print_function
import os
import time
import stat
from datetime import datetime
from Plugins.Extensions.WGFileManagerPro.core.compatibility import ensure_unicode, NavigationHelper


def format_size(bytes_size):
    """
    Format bytes to human-readable size
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 GB")
    """
    if bytes_size is None:
        return "N/A"
    
    try:
        bytes_size = float(bytes_size)
    except (ValueError, TypeError):
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            if unit == 'B':
                return "%d %s" % (int(bytes_size), unit)
            else:
                return "%.1f %s" % (bytes_size, unit)
        bytes_size /= 1024.0
    
    return "%.1f PB" % bytes_size


def format_speed(bytes_per_sec):
    """
    Format speed to human-readable format
    
    Args:
        bytes_per_sec: Speed in bytes per second
        
    Returns:
        str: Formatted speed (e.g., "5.2 MB/s")
    """
    if bytes_per_sec is None or bytes_per_sec <= 0:
        return "0 B/s"
    
    return format_size(bytes_per_sec) + "/s"


def format_time(seconds):
    """
    Format seconds to human-readable time
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted time (e.g., "1h 23m 45s")
    """
    if seconds is None or seconds < 0:
        return "N/A"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return "%ds" % seconds
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return "%dm %ds" % (minutes, secs)
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours < 24:
            return "%dh %dm %ds" % (hours, minutes, secs)
        else:
            days = hours // 24
            hours = hours % 24
            return "%dd %dh %dm" % (days, hours, minutes)


def format_date(timestamp):
    """
    Format timestamp to readable date
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        str: Formatted date
    """
    if timestamp is None:
        return "N/A"
    
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return "N/A"


def format_permissions(mode):
    """
    Format file permissions to rwx format
    
    Args:
        mode: File mode from os.stat
        
    Returns:
        str: Permission string (e.g., "rwxr-xr--")
    """
    perm_str = ''
    
    # File type
    if stat.S_ISDIR(mode):
        perm_str += 'd'
    elif stat.S_ISLNK(mode):
        perm_str += 'l'
    elif stat.S_ISCHR(mode):
        perm_str += 'c'
    elif stat.S_ISBLK(mode):
        perm_str += 'b'
    elif stat.S_ISFIFO(mode):
        perm_str += 'p'
    elif stat.S_ISSOCK(mode):
        perm_str += 's'
    else:
        perm_str += '-'
    
    # Owner permissions
    perm_str += 'r' if mode & stat.S_IRUSR else '-'
    perm_str += 'w' if mode & stat.S_IWUSR else '-'
    perm_str += 'x' if mode & stat.S_IXUSR else '-'
    
    # Setuid bit
    if mode & stat.S_ISUID:
        perm_str = perm_str[:-1] + ('s' if perm_str[-1] == 'x' else 'S')
    
    # Group permissions
    perm_str += 'r' if mode & stat.S_IRGRP else '-'
    perm_str += 'w' if mode & stat.S_IWGRP else '-'
    perm_str += 'x' if mode & stat.S_IXGRP else '-'
    
    # Setgid bit
    if mode & stat.S_ISGID:
        perm_str = perm_str[:-1] + ('s' if perm_str[-1] == 'x' else 'S')
    
    # Others permissions
    perm_str += 'r' if mode & stat.S_IROTH else '-'
    perm_str += 'w' if mode & stat.S_IWOTH else '-'
    perm_str += 'x' if mode & stat.S_IXOTH else '-'
    
    # Sticky bit
    if mode & stat.S_ISVTX:
        perm_str = perm_str[:-1] + ('t' if perm_str[-1] == 'x' else 'T')
    
    return perm_str


def get_permissions_string(path):
    """
    Get file permissions as rwx string
    
    Args:
        path: File path
        
    Returns:
        str: Permission string (e.g., 'rwxr-xr-x') or '----------'
    """
    try:
        mode = os.stat(path).st_mode
        return format_permissions(mode)
    except:
        return '----------'


def get_permissions_octal(path):
    """
    Get file permissions as octal string
    
    Args:
        path: File path
        
    Returns:
        str: Octal permissions (e.g., '755') or None
    """
    try:
        mode = os.stat(path).st_mode
        return oct(mode)[-3:]
    except:
        return None


def format_permissions_with_octal(path):
    """
    Format permissions as both rwx and octal
    
    Args:
        path: File path
        
    Returns:
        str: Formatted permissions (e.g., "rwxr-xr-x (755)")
    """
    perm_str = get_permissions_string(path)
    perm_octal = get_permissions_octal(path)
    
    if perm_octal:
        return f"{perm_str} ({perm_octal})"
    else:
        return perm_str


def get_file_icon(filename, is_dir=False):
    """
    Get icon for file based on extension
    
    Args:
        filename: File name
        is_dir: Whether it's a directory
        
    Returns:
        str: Icon character/emoji
    """
    if is_dir:
        return u'📁'
    
    # Get extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # Icon mapping
    icons = {
        # Video
        '.mkv': u'🎬', '.mp4': u'🎬', '.avi': u'🎬', '.mov': u'🎬',
        '.wmv': u'🎬', '.flv': u'🎬', '.m4v': u'🎬', '.mpg': u'🎬',
        '.mpeg': u'🎬', '.webm': u'🎬', '.ts': u'🎬', '.m2ts': u'🎬',
        
        # Audio
        '.mp3': u'🎵', '.flac': u'🎵', '.m4a': u'🎵', '.aac': u'🎵',
        '.ogg': u'🎵', '.wav': u'🎵', '.wma': u'🎵', '.opus': u'🎵',
        
        # Images
        '.jpg': u'🖼️', '.jpeg': u'🖼️', '.png': u'🖼️', '.gif': u'🖼️',
        '.bmp': u'🖼️', '.svg': u'🖼️', '.webp': u'🖼️', '.ico': u'🖼️',
        '.tiff': u'🖼️', '.tif': u'🖼️', '.mvi': u'🖼️',
        
        # Archives
        '.zip': u'📦', '.rar': u'📦', '.7z': u'📦', '.tar': u'📦',
        '.gz': u'📦', '.bz2': u'📦', '.xz': u'📦', '.zst': u'📦',
        '.tar.gz': u'📦', '.tgz': u'📦', '.tar.bz2': u'📦',
        
        # Documents
        '.pdf': u'📕', '.doc': u'📘', '.docx': u'📘', '.odt': u'📘',
        '.txt': u'📄', '.rtf': u'📄', '.log': u'📄',
        
        # Spreadsheets
        '.xls': u'📊', '.xlsx': u'📊', '.ods': u'📊', '.csv': u'📊',
        
        # Code
        '.py': u'🐍', '.sh': u'⚙️', '.c': u'©️', '.cpp': u'🔧',
        '.h': u'🔧', '.js': u'📜', '.html': u'🌐', '.css': u'🎨',
        '.xml': u'📋', '.json': u'📋', '.yaml': u'📋', '.yml': u'📋',
        
        # System
        '.deb': u'📦', '.ipk': u'📦', '.rpm': u'📦',
        '.iso': u'💿', '.img': u'💿',
        
        # Playlists
        '.m3u': u'📻', '.m3u8': u'📻', '.pls': u'📻',
        
        # Executables
        '.bin': u'⚙️', '.run': u'⚙️', '.sh': u'⚙️', '.bash': u'⚙️',
        
        # Subtitles
        '.srt': u'📝', '.sub': u'📝', '.ass': u'📝',
        
        # E-books
        '.epub': u'📚', '.mobi': u'📚',
    }
    
    return icons.get(ext, u'📄')


def get_file_type_name(filename, is_dir=False):
    """
    Get file type name
    
    Args:
        filename: File name
        is_dir: Whether it's a directory
        
    Returns:
        str: Type name (e.g., "Video File")
    """
    if is_dir:
        return "Directory"
    
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    types = {
        '.mkv': 'Video File', '.mp4': 'Video File', '.avi': 'Video File',
        '.mp3': 'Audio File', '.flac': 'Audio File',
        '.jpg': 'Image File', '.png': 'Image File', '.gif': 'Image File',
        '.zip': 'Archive', '.rar': 'Archive', '.7z': 'Archive',
        '.pdf': 'PDF Document', '.doc': 'Word Document', '.docx': 'Word Document',
        '.txt': 'Text File', '.log': 'Log File',
        '.py': 'Python Script', '.sh': 'Shell Script',
        '.deb': 'Debian Package', '.ipk': 'IPK Package',
        '.bin': 'Binary Executable', '.run': 'Executable',
        '.srt': 'Subtitle File', '.m3u': 'Playlist File',
        '.epub': 'E-book', '.iso': 'Disk Image',
    }
    
    return types.get(ext, 'File')


def get_disk_usage(path):
    """
    Get disk usage for path
    
    Args:
        path: Path to check
        
    Returns:
        tuple: (total, used, free) in bytes
    """
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        return (total, used, free)
    except:
        return (0, 0, 0)


def format_disk_usage(path):
    """
    Format disk usage as string
    
    Args:
        path: Path to check
        
    Returns:
        str: Formatted usage (e.g., "45.2 GB / 120 GB (38%)")
    """
    total, used, free = get_disk_usage(path)
    
    if total == 0:
        return "N/A"
    
    percent = int(used * 100 / total)
    return "%s / %s (%d%%)" % (format_size(used), format_size(total), percent)


def is_media_file(filename):
    """
    Check if file is a media file
    
    Args:
        filename: File name
        
    Returns:
        bool: True if media file
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    media_exts = {
        '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v',
        '.mpg', '.mpeg', '.webm', '.ts', '.m2ts',
        '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wav', '.wma'
    }
    
    return ext in media_exts


def is_image_file(filename):
    """
    Check if file is an image
    
    Args:
        filename: File name
        
    Returns:
        bool: True if image file
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    image_exts = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.svg', '.webp', '.ico', '.tiff', '.tif', '.mvi'
    }
    
    return ext in image_exts


def is_archive_file(filename):
    """
    Check if file is an archive
    
    Args:
        filename: File name
        
    Returns:
        bool: True if archive file
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    archive_exts = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        '.xz', '.zst', '.tar.gz', '.tgz', '.tar.bz2'
    }
    
    return ext in archive_exts


def is_executable_file(filename, path=None):
    """
    Check if file is executable
    
    Args:
        filename: File name
        path: Full file path (optional, for checking actual permissions)
        
    Returns:
        bool: True if executable file
    """
    # Check by extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    exec_exts = {'.sh', '.bash', '.py', '.pl', '.rb', '.bin', '.run'}
    if ext in exec_exts:
        return True
    
    # Check actual file permissions if path provided
    if path and os.path.exists(path):
        try:
            mode = os.stat(path).st_mode
            return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        except:
            pass
    
    return False


def sanitize_filename(filename):
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', ensure_unicode(filename))
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Ensure not empty
    if not filename:
        filename = 'unnamed'
    return filename


def get_unique_path(path):
    """
    Get unique path by appending number if file exists
    
    Args:
        path: Original path
        
    Returns:
        str: Unique path
    """
    if not os.path.exists(path):
        return path
    
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    name, ext = os.path.splitext(basename)
    
    counter = 1
    while True:
        new_name = "%s (%d)%s" % (name, counter, ext)
        new_path = os.path.join(dirname, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def is_hidden(filepath):
    """
    Check if file/directory is hidden
    
    Args:
        filepath: Path to check
        
    Returns:
        bool: True if hidden
    """
    return os.path.basename(filepath).startswith('.')


def human_sort_key(text):
    """
    Generate sort key for human-friendly sorting (natural sort)
    
    Args:
        text: Text to generate key for
        
    Returns:
        list: Sort key
    """
    import re
    def atoi(text):
        return int(text) if text.isdigit() else text
    
    return [atoi(c) for c in re.split(r'(\d+)', ensure_unicode(text))]


def get_file_owner_info(path):
    """
    Get file owner and group information
    
    Args:
        path: File path
        
    Returns:
        tuple: (user_name, group_name, uid, gid) or (None, None, None, None)
    """
    try:
        import pwd
        import grp
        
        stat_info = os.stat(path)
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        
        try:
            user_name = pwd.getpwuid(uid).pw_name
        except:
            user_name = str(uid)
        
        try:
            group_name = grp.getgrgid(gid).gr_name
        except:
            group_name = str(gid)
        
        return user_name, group_name, uid, gid
    except:
        return None, None, None, None


def format_ownership(path):
    """
    Format file ownership for display
    
    Args:
        path: File path
        
    Returns:
        str: Formatted ownership (e.g., "root:root")
    """
    user, group, _, _ = get_file_owner_info(path)
    if user and group:
        return f"{user}:{group}"
    return "N/A"


def format_navigation_info(current_index, total_items, selected_name=""):
    """
    Format navigation information
    
    Args:
        current_index: Current selection index
        total_items: Total number of items
        selected_name: Name of selected item
        
    Returns:
        str: Formatted navigation info
    """
    if total_items <= 0:
        return "No items"
    
    position = current_index + 1
    info = f"{position}/{total_items}"
    
    if selected_name:
        info += f" - {selected_name}"
    
    return info


def format_selection_info(selected_count, total_count=None):
    """
    Format selection information
    
    Args:
        selected_count: Number of selected items
        total_count: Total number of items (optional)
        
    Returns:
        str: Formatted selection info
    """
    if selected_count == 0:
        return "No items selected"
    
    info = f"{selected_count} selected"
    
    if total_count is not None:
        info += f" of {total_count}"
    
    return info


def format_path_for_display(path, max_length=50):
    """
    Format path for display (shorten if too long)
    
    Args:
        path: Path to format
        max_length: Maximum display length
        
    Returns:
        str: Formatted path
    """
    path_str = ensure_unicode(path)
    
    if len(path_str) <= max_length:
        return path_str
    
    # Shorten path by keeping beginning and end
    start_len = max_length // 3
    end_len = max_length // 3
    middle_len = max_length - start_len - end_len - 3  # 3 for "..."
    
    if middle_len < 5:  # Too short for meaningful middle
        return path_str[:max_length-3] + "..."
    
    start = path_str[:start_len]
    end = path_str[-end_len:] if end_len > 0 else ""
    
    return f"{start}...{end}"


def format_key_help(keys):
    """
    Format keyboard help text
    
    Args:
        keys: Dictionary of key: description
        
    Returns:
        str: Formatted help text
    """
    help_parts = []
    for key, description in keys.items():
        help_parts.append(f"{key}: {description}")
    
    return " | ".join(help_parts)


def format_progress_percentage(done, total):
    """
    Format progress percentage
    
    Args:
        done: Completed items
        total: Total items
        
    Returns:
        str: Formatted percentage
    """
    if total <= 0:
        return "0%"
    
    percentage = int((done * 100) / total)
    return f"{percentage}%"


def get_navigation_help():
    """
    Get standard navigation help text
    
    Returns:
        str: Navigation help text
    """
    return format_key_help({
        "↑↓": "Navigate",
        "←→": "Switch panes",
        "OK": "Open/Play",
        "EXIT": "Back/Exit",
        "GREEN": "Copy",
        "YELLOW": "Move",
        "RED": "Delete",
        "BLUE": "Mark",
        "INFO": "Permissions"
    })