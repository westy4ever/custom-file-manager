"""
Logging system for WG File Manager Pro
"""

from __future__ import absolute_import, print_function
import logging
import os
import sys
from datetime import datetime

# Create main logger
logger = logging.getLogger('wgfilemanager')
logger.setLevel(logging.INFO)

# Create log directory
LOG_DIR = "/tmp/wgfilemanager"
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except:
        LOG_DIR = "/tmp"

# Log file paths
LOG_FILE = os.path.join(LOG_DIR, "wgfilemanager.log")
DEBUG_LOG_FILE = os.path.join(LOG_DIR, "wgfilemanager_debug.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "wgfilemanager_error.log")

# Clear old logs on startup (keep last 3 days)
try:
    import time
    current_time = time.time()
    three_days_ago = current_time - (3 * 24 * 3600)
    
    for log_file in [LOG_FILE, DEBUG_LOG_FILE, ERROR_LOG_FILE]:
        if os.path.exists(log_file):
            file_time = os.path.getmtime(log_file)
            if file_time < three_days_ago:
                os.remove(log_file)
except:
    pass

# File handler for general logs
try:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"[Logger] Error creating file handler: {e}")

# Debug file handler (separate file)
try:
    debug_file_handler = logging.FileHandler(DEBUG_LOG_FILE)
    debug_file_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    debug_file_handler.setFormatter(debug_formatter)
    logger.addHandler(debug_file_handler)
except Exception as e:
    print(f"[Logger] Error creating debug handler: {e}")

# Error file handler (separate file for errors only)
try:
    error_file_handler = logging.FileHandler(ERROR_LOG_FILE)
    error_file_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - ERROR - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_file_handler.setFormatter(error_formatter)
    logger.addHandler(error_file_handler)
except Exception as e:
    print(f"[Logger] Error creating error handler: {e}")

# Console handler (for debugging)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Create startup log entry
logger.info("=" * 60)
logger.info("WG File Manager Pro - Logging Started")
logger.info("Time: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
logger.info("Python: %s", sys.version.split()[0])
logger.info("=" * 60)


def get_logger(name=None):
    """
    Get logger instance
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger('wgfilemanager.%s' % name)
    return logger


def set_debug_mode(enabled):
    """
    Enable/disable debug mode
    
    Args:
        enabled: True to enable debug logging
    """
    if enabled:
        logger.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)
        logger.info("Debug mode ENABLED")
    else:
        logger.setLevel(logging.INFO)
        console_handler.setLevel(logging.INFO)
        logger.info("Debug mode DISABLED")


def log_operation(operation, *args, **kwargs):
    """
    Log file operation
    
    Args:
        operation: Operation name
        *args: Operation arguments
        **kwargs: Operation keyword arguments
    """
    log_msg = f"Operation: {operation}"
    
    if args:
        log_msg += f" - Args: {args}"
    
    if kwargs:
        # Hide passwords in kwargs
        safe_kwargs = {}
        for key, value in kwargs.items():
            if 'password' in key.lower() or 'pass' in key.lower():
                safe_kwargs[key] = '********'
            else:
                safe_kwargs[key] = value
        log_msg += f" - Kwargs: {safe_kwargs}"
    
    logger.info(log_msg)


def log_error(context, error, exc_info=False):
    """
    Log error with context
    
    Args:
        context: Error context
        error: Error object or message
        exc_info: Include exception info
    """
    if isinstance(error, Exception):
        error_msg = str(error)
        if exc_info:
            logger.error("%s: %s", context, error_msg, exc_info=True)
        else:
            logger.error("%s: %s", context, error_msg)
    else:
        logger.error("%s: %s", context, error)


def log_navigation(event, pane=None, selection=None):
    """
    Log navigation event
    
    Args:
        event: Navigation event name
        pane: Active pane (left/right)
        selection: Current selection
    """
    log_msg = f"Navigation: {event}"
    if pane:
        log_msg += f" - Pane: {pane}"
    if selection:
        if isinstance(selection, tuple) and len(selection) > 2:
            log_msg += f" - Selection: {selection[2]}"
        else:
            log_msg += f" - Selection: {selection}"
    
    logger.debug(log_msg)


def log_performance(start_time, operation, details=""):
    """
    Log performance timing
    
    Args:
        start_time: Operation start time
        operation: Operation name
        details: Additional details
    """
    import time
    elapsed = time.time() - start_time
    log_msg = f"Performance: {operation} took {elapsed:.3f}s"
    if details:
        log_msg += f" - {details}"
    
    if elapsed > 1.0:
        logger.warning(log_msg)
    else:
        logger.debug(log_msg)


def get_log_file():
    """Get main log file path"""
    return LOG_FILE


def get_debug_log_file():
    """Get debug log file path"""
    return DEBUG_LOG_FILE


def get_error_log_file():
    """Get error log file path"""
    return ERROR_LOG_FILE


def clear_log(log_type='all'):
    """
    Clear log files
    
    Args:
        log_type: 'all', 'main', 'debug', 'error'
    """
    try:
        files_to_clear = []
        
        if log_type in ['all', 'main']:
            files_to_clear.append(LOG_FILE)
        if log_type in ['all', 'debug']:
            files_to_clear.append(DEBUG_LOG_FILE)
        if log_type in ['all', 'error']:
            files_to_clear.append(ERROR_LOG_FILE)
        
        for filepath in files_to_clear:
            if os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"Log cleared at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        logger.info("Log files cleared: %s", log_type)
        return True
        
    except Exception as e:
        logger.error("Error clearing logs: %s", e)
        return False


def get_log_stats():
    """
    Get log file statistics
    
    Returns:
        dict: Log statistics
    """
    stats = {}
    
    for name, filepath in [
        ('main', LOG_FILE),
        ('debug', DEBUG_LOG_FILE),
        ('error', ERROR_LOG_FILE)
    ]:
        if os.path.exists(filepath):
            try:
                size = os.path.getsize(filepath)
                stats[name] = {
                    'path': filepath,
                    'size': size,
                    'size_human': format_size(size),
                    'exists': True
                }
            except:
                stats[name] = {'exists': False}
        else:
            stats[name] = {'exists': False}
    
    return stats


def format_size(bytes_size):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            if unit == 'B':
                return "%d %s" % (int(bytes_size), unit)
            else:
                return "%.1f %s" % (bytes_size, unit)
        bytes_size /= 1024.0
    return "%.1f %s" % (bytes_size, 'TB')