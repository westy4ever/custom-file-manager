"""
File operations with progress tracking and advanced features
Handles copy, move, delete, rename with visual feedback
"""

from __future__ import absolute_import, division, print_function
import os
import shutil
import time
import threading
import hashlib
import stat
import pwd
import grp
from Plugins.Extensions.WGFileManagerPro.core.compatibility import ensure_str, ensure_unicode, safe_listdir, safe_join

# Try to import config, but don't fail if not available
try:
    from Plugins.Extensions.WGFileManagerPro.core.config import get_config
except ImportError:
    get_config = None

from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger
from Plugins.Extensions.WGFileManagerPro.utils.formatters import format_size

logger = get_logger(__name__)


class OperationProgress:
    """Progress tracking for file operations"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset progress"""
        self.current_file = ""
        self.current_percent = 0
        self.current_bytes = 0
        self.current_total = 0
        self.overall_percent = 0
        self.overall_bytes = 0
        self.overall_total = 0
        self.files_done = 0
        self.files_total = 0
        self.speed = 0
        self.eta = 0
        self.start_time = time.time()
        self.errors = []
        self.warnings = []
    
    def to_dict(self):
        """Convert to dictionary"""
        elapsed = time.time() - self.start_time
        return {
            'file': self.current_file,
            'percent': self.current_percent,
            'copied': self.current_bytes,
            'total': self.current_total,
            'speed': self.speed,
            'eta': self.eta,
            'overall_percent': self.overall_percent,
            'completed': self.files_done,
            'files_total': self.files_total,
            'elapsed': elapsed,
            'errors': len(self.errors),
            'warnings': len(self.warnings)
        }


class FileOperations:
    """Advanced file operations with progress tracking"""
    
    def __init__(self, progress_callback=None):
        """
        Initialize file operations
        
        Args:
            progress_callback: Function to call with progress updates
        """
        self.progress_callback = progress_callback
        self.cancel_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.progress = OperationProgress()
        self.progress_lock = threading.RLock()
        
        # Get buffer size from config
        if get_config:
            try:
                config = get_config()
                self.buffer_size = config.get('buffer_size', 64) * 1024
                self.preserve_permissions = config.get('preserve_permissions', True)
                self.use_trash = config.get('use_trash', True)
                self.verify_copy = config.get('verify_copy', False)
                logger.debug("[FileOps] Config loaded: buffer=%dKB, preserve_perms=%s, use_trash=%s, verify=%s",
                           self.buffer_size // 1024, self.preserve_permissions, self.use_trash, self.verify_copy)
            except Exception as e:
                logger.error("[FileOps] Config error: %s", e)
                self.buffer_size = 64 * 1024
                self.preserve_permissions = True
                self.use_trash = True
                self.verify_copy = False
        else:
            self.buffer_size = 64 * 1024
            self.preserve_permissions = True
            self.use_trash = True
            self.verify_copy = False
        
        logger.info("[FileOps] Initialized with buffer size: %d KB", self.buffer_size // 1024)
    
    def cancel(self):
        """Cancel current operation"""
        logger.info("[FileOps] Cancelling operation")
        self.cancel_flag.set()
    
    def pause(self):
        """Pause current operation"""
        logger.info("[FileOps] Pausing operation")
        self.pause_flag.set()
    
    def resume(self):
        """Resume paused operation"""
        logger.info("[FileOps] Resuming operation")
        self.pause_flag.clear()
    
    def is_cancelled(self):
        """Check if operation is cancelled"""
        return self.cancel_flag.is_set()
    
    def is_paused(self):
        """Check if operation is paused"""
        return self.pause_flag.is_set()
    
    def wait_if_paused(self):
        """Wait while paused"""
        while self.pause_flag.is_set() and not self.cancel_flag.is_set():
            time.sleep(0.1)
    
    def report_progress(self):
        """Report progress to callback"""
        if self.progress_callback:
            try:
                with self.progress_lock:
                    progress_data = self.progress.to_dict()
                self.progress_callback(progress_data)
            except Exception as e:
                logger.error("[FileOps] Progress callback error: %s", e)
    
    def calculate_total_size(self, items):
        """
        Calculate total size of items
        
        Args:
            items: List of paths
            
        Returns:
            tuple: (total_size, file_count)
        """
        total_size = 0
        file_count = 0
        
        logger.debug("[FileOps] Calculating total size for %d items", len(items))
        
        for item in items:
            if self.is_cancelled():
                logger.debug("[FileOps] Calculation cancelled")
                break
                
            item = ensure_str(item)
            if os.path.isfile(item):
                try:
                    size = os.path.getsize(item)
                    total_size += size
                    file_count += 1
                    logger.debug("[FileOps] File: %s (%s)", os.path.basename(item), format_size(size))
                except (OSError, PermissionError) as e:
                    logger.error("[FileOps] Error getting size for %s: %s", item, e)
                    with self.progress_lock:
                        self.progress.warnings.append(f"Cannot read size: {os.path.basename(item)}")
            elif os.path.isdir(item):
                logger.debug("[FileOps] Directory: %s", item)
                try:
                    for root, dirs, files in os.walk(item):
                        if self.is_cancelled():
                            break
                        # Filter out directories we can't access
                        dirs[:] = [d for d in dirs if os.access(os.path.join(root, d), os.R_OK | os.X_OK)]
                        
                        for f in files:
                            try:
                                filepath = safe_join(root, f)
                                if os.path.exists(filepath) and not os.path.islink(filepath):
                                    size = os.path.getsize(filepath)
                                    total_size += size
                                    file_count += 1
                            except (OSError, PermissionError) as e:
                                logger.debug("[FileOps] Cannot access %s: %s", f, e)
                except Exception as e:
                    logger.error("[FileOps] Error walking directory %s: %s", item, e)
                    with self.progress_lock:
                        self.progress.warnings.append(f"Cannot scan directory: {os.path.basename(item)}")
        
        logger.info("[FileOps] Total size: %s (%d files)", format_size(total_size), file_count)
        return total_size, file_count
    
    def copy_file(self, src, dst, verify=None, preserve_permissions=None):
        """
        Copy single file with progress
        
        Args:
            src: Source file path
            dst: Destination file path
            verify: Verify copy with hash (default: from config)
            preserve_permissions: Whether to preserve permissions (default: from config)
            
        Returns:
            bool: True if successful
        """
        src = ensure_str(src)
        dst = ensure_str(dst)
        
        if verify is None:
            verify = self.verify_copy
        if preserve_permissions is None:
            preserve_permissions = self.preserve_permissions
        
        logger.info("[FileOps] Copying: %s -> %s", src, dst)
        logger.debug("[FileOps] Options: verify=%s, preserve_perms=%s", verify, preserve_permissions)
        
        try:
            # Get source file info
            src_stat = None
            if preserve_permissions:
                try:
                    src_stat = os.stat(src)
                except Exception as e:
                    logger.warning("[FileOps] Cannot stat source file: %s", e)
                    with self.progress_lock:
                        self.progress.warnings.append(f"Cannot read source permissions: {os.path.basename(src)}")
            
            # Check if destination exists
            if os.path.exists(dst):
                logger.warning("[FileOps] Destination exists: %s", dst)
                with self.progress_lock:
                    self.progress.warnings.append(f"Overwriting: {os.path.basename(dst)}")
            
            # Get file size
            file_size = os.path.getsize(src)
            with self.progress_lock:
                self.progress.current_file = ensure_unicode(os.path.basename(src))
                self.progress.current_total = file_size
                self.progress.current_bytes = 0
                self.progress.current_percent = 0
            
            logger.debug("[FileOps] File size: %s", format_size(file_size))
            
            # Calculate speed and ETA
            start_time = time.time()
            last_update = start_time
            last_bytes = 0
            
            # Ensure destination directory exists
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                try:
                    os.makedirs(dst_dir, exist_ok=True)
                    logger.debug("[FileOps] Created directory: %s", dst_dir)
                except Exception as e:
                    logger.error("[FileOps] Cannot create directory %s: %s", dst_dir, e)
                    with self.progress_lock:
                        self.progress.errors.append(f"Cannot create directory: {dst_dir}")
                    return False
            
            # Copy with progress tracking
            try:
                with open(src, 'rb') as fsrc:
                    with open(dst, 'wb') as fdst:
                        while True:
                            # Check cancellation and pause
                            if self.is_cancelled():
                                logger.info("[FileOps] Copy cancelled by user")
                                return False
                            self.wait_if_paused()
                            
                            # Read chunk
                            chunk = fsrc.read(self.buffer_size)
                            if not chunk:
                                break
                            
                            # Write chunk
                            fdst.write(chunk)
                            bytes_copied = len(chunk)
                            
                            with self.progress_lock:
                                self.progress.current_bytes += bytes_copied
                                self.progress.overall_bytes += bytes_copied
                            
                            # Update progress periodically
                            now = time.time()
                            if now - last_update >= 0.1:  # Update every 100ms
                                with self.progress_lock:
                                    # Calculate speed
                                    elapsed = now - start_time
                                    if elapsed > 0:
                                        self.progress.speed = self.progress.current_bytes / elapsed
                                    
                                    # Calculate ETA
                                    if self.progress.speed > 0:
                                        remaining = file_size - self.progress.current_bytes
                                        self.progress.eta = remaining / self.progress.speed
                                    
                                    # Calculate percentages
                                    if file_size > 0:
                                        self.progress.current_percent = int(
                                            (self.progress.current_bytes * 100) / file_size
                                        )
                                    
                                    if self.progress.overall_total > 0:
                                        self.progress.overall_percent = int(
                                            (self.progress.overall_bytes * 100) / self.progress.overall_total
                                        )
                                
                                self.report_progress()
                                last_update = now
                
                logger.debug("[FileOps] File copy completed")
                
                # Preserve metadata
                try:
                    shutil.copystat(src, dst)
                    logger.debug("[FileOps] Metadata copied")
                    
                    # Preserve permissions if requested
                    if preserve_permissions and src_stat:
                        try:
                            os.chmod(dst, src_stat.st_mode)
                            logger.debug("[FileOps] Permissions preserved: %s", oct(src_stat.st_mode)[-3:])
                            
                            # Copy ownership if running as root
                            if os.geteuid() == 0:  # root
                                try:
                                    os.chown(dst, src_stat.st_uid, src_stat.st_gid)
                                    logger.debug("[FileOps] Ownership preserved: %s:%s", 
                                               src_stat.st_uid, src_stat.st_gid)
                                except Exception as e:
                                    logger.warning("[FileOps] Cannot preserve ownership: %s", e)
                        except Exception as e:
                            logger.warning("[FileOps] Cannot preserve permissions: %s", e)
                            with self.progress_lock:
                                self.progress.warnings.append(f"Cannot preserve permissions: {os.path.basename(src)}")
                except Exception as e:
                    logger.warning("[FileOps] Cannot copy metadata: %s", e)
                    with self.progress_lock:
                        self.progress.warnings.append(f"Cannot copy metadata: {os.path.basename(src)}")
                
                # Verify if requested
                if verify:
                    logger.debug("[FileOps] Verifying copy...")
                    if not self.verify_file(src, dst):
                        error_msg = f"Verification failed: {os.path.basename(src)}"
                        logger.error("[FileOps] %s", error_msg)
                        with self.progress_lock:
                            self.progress.errors.append(error_msg)
                        
                        # Remove failed copy
                        try:
                            os.remove(dst)
                            logger.debug("[FileOps] Removed failed copy")
                        except:
                            pass
                        
                        return False
                    else:
                        logger.debug("[FileOps] Verification passed")
                
                logger.info("[FileOps] Successfully copied: %s", os.path.basename(src))
                return True
                
            except (IOError, OSError, PermissionError) as e:
                error_msg = f"I/O error copying {os.path.basename(src)}: {str(e)}"
                logger.error("[FileOps] %s", error_msg)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                return False
            except Exception as e:
                error_msg = f"Error copying {os.path.basename(src)}: {str(e)}"
                logger.error("[FileOps] %s", error_msg)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Failed to copy {os.path.basename(src)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def copy(self, items, dest_dir, verify=None, preserve_permissions=None):
        """
        Copy files/directories with progress
        
        Args:
            items: List of source paths
            dest_dir: Destination directory
            verify: Verify copies (default: from config)
            preserve_permissions: Whether to preserve permissions (default: from config)
            
        Returns:
            bool: True if all successful
        """
        dest_dir = ensure_str(dest_dir)
        
        if verify is None:
            verify = self.verify_copy
        if preserve_permissions is None:
            preserve_permissions = self.preserve_permissions
        
        logger.info("[FileOps] Starting copy operation")
        logger.info("[FileOps] Destination: %s", dest_dir)
        logger.info("[FileOps] Items to copy: %d", len(items))
        logger.info("[FileOps] Options: verify=%s, preserve_perms=%s", verify, preserve_permissions)
        
        # Reset progress
        with self.progress_lock:
            self.progress.reset()
        self.cancel_flag.clear()
        self.pause_flag.clear()
        
        # Calculate total size
        total_size, total_files = self.calculate_total_size(items)
        with self.progress_lock:
            self.progress.overall_total = total_size
            self.progress.files_total = total_files
        
        if self.is_cancelled():
            logger.info("[FileOps] Operation cancelled before starting")
            return False
        
        # Ensure destination exists
        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
                logger.info("[FileOps] Created destination directory: %s", dest_dir)
            except Exception as e:
                error_msg = f"Cannot create destination directory: {dest_dir}"
                logger.error("[FileOps] %s: %s", error_msg, e)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                return False
        
        # Copy each item
        success = True
        for item in items:
            if self.is_cancelled():
                logger.info("[FileOps] Copy operation cancelled")
                success = False
                break
            
            item = ensure_str(item)
            item_name = os.path.basename(item)
            dest_path = safe_join(dest_dir, item_name)
            
            logger.debug("[FileOps] Processing: %s", item_name)
            
            if os.path.isfile(item):
                # Copy file
                if not self.copy_file(item, dest_path, verify, preserve_permissions):
                    success = False
                    if self.is_cancelled():
                        break
                with self.progress_lock:
                    self.progress.files_done += 1
                
            elif os.path.isdir(item):
                # Copy directory recursively
                if not self.copy_directory(item, dest_path, verify, preserve_permissions):
                    success = False
                    if self.is_cancelled():
                        break
        
        # Final progress update
        if not self.is_cancelled():
            with self.progress_lock:
                self.progress.overall_percent = 100
                self.progress.current_percent = 100
            self.report_progress()
        
        # Log completion
        if success and not self.is_cancelled():
            logger.info("[FileOps] Copy operation completed successfully")
            logger.info("[FileOps] Files copied: %d/%d", 
                       self.progress.files_done, self.progress.files_total)
        else:
            if self.is_cancelled():
                logger.info("[FileOps] Copy operation cancelled by user")
            else:
                logger.error("[FileOps] Copy operation failed with %d errors", 
                           len(self.progress.errors))
        
        return success and not self.is_cancelled()
    
    def copy_directory(self, src_dir, dst_dir, verify=None, preserve_permissions=None):
        """
        Copy directory recursively
        
        Args:
            src_dir: Source directory
            dst_dir: Destination directory
            verify: Verify copies (default: from config)
            preserve_permissions: Whether to preserve permissions (default: from config)
            
        Returns:
            bool: True if successful
        """
        src_dir = ensure_str(src_dir)
        dst_dir = ensure_str(dst_dir)
        
        if verify is None:
            verify = self.verify_copy
        if preserve_permissions is None:
            preserve_permissions = self.preserve_permissions
        
        logger.debug("[FileOps] Copying directory: %s -> %s", src_dir, dst_dir)
        
        try:
            # Get source directory info for permissions
            src_stat = None
            if preserve_permissions:
                try:
                    src_stat = os.stat(src_dir)
                except:
                    pass
            
            # Create destination directory
            if not os.path.exists(dst_dir):
                try:
                    os.makedirs(dst_dir, exist_ok=True)
                    logger.debug("[FileOps] Created directory: %s", dst_dir)
                except Exception as e:
                    error_msg = f"Cannot create directory {dst_dir}: {str(e)}"
                    logger.error("[FileOps] %s", error_msg)
                    with self.progress_lock:
                        self.progress.errors.append(error_msg)
                    return False
            
            # Apply directory permissions if preserving
            if preserve_permissions and src_stat:
                try:
                    os.chmod(dst_dir, src_stat.st_mode)
                    if os.geteuid() == 0:  # root
                        os.chown(dst_dir, src_stat.st_uid, src_stat.st_gid)
                    logger.debug("[FileOps] Directory permissions preserved")
                except Exception as e:
                    logger.warning("[FileOps] Cannot set directory permissions: %s", e)
                    with self.progress_lock:
                        self.progress.warnings.append(f"Cannot set permissions for {os.path.basename(dst_dir)}")
            
            # Copy contents
            for item in safe_listdir(src_dir):
                if self.is_cancelled():
                    return False
                
                src_path = safe_join(src_dir, item)
                dst_path = safe_join(dst_dir, item)
                
                if os.path.isfile(src_path):
                    if not self.copy_file(src_path, dst_path, verify, preserve_permissions):
                        return False
                    with self.progress_lock:
                        self.progress.files_done += 1
                    
                elif os.path.isdir(src_path):
                    if not self.copy_directory(src_path, dst_path, verify, preserve_permissions):
                        return False
            
            return True
            
        except Exception as e:
            error_msg = f"Error copying directory {src_dir}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def move(self, items, dest_dir, preserve_permissions=None):
        """
        Move files/directories
        
        Args:
            items: List of source paths
            dest_dir: Destination directory
            preserve_permissions: Whether to preserve permissions (default: from config)
            
        Returns:
            bool: True if successful
        """
        dest_dir = ensure_str(dest_dir)
        
        if preserve_permissions is None:
            preserve_permissions = self.preserve_permissions
        
        logger.info("[FileOps] Starting move operation")
        logger.info("[FileOps] Destination: %s", dest_dir)
        logger.info("[FileOps] Items to move: %d", len(items))
        logger.info("[FileOps] Preserve permissions: %s", preserve_permissions)
        
        # First try rename (fast, same filesystem)
        logger.debug("[FileOps] Trying rename move (same filesystem)")
        if self._try_rename_move(items, dest_dir):
            logger.info("[FileOps] Move completed using rename")
            return True
        
        # Fall back to copy + delete
        logger.debug("[FileOps] Rename failed, using copy+delete")
        if self.copy(items, dest_dir, verify=False, preserve_permissions=preserve_permissions):
            logger.debug("[FileOps] Copy successful, now deleting originals")
            return self.delete(items, use_trash=False)
        
        logger.error("[FileOps] Move operation failed")
        return False
    
    def _try_rename_move(self, items, dest_dir):
        """Try to move using rename (faster, same filesystem)"""
        try:
            for item in items:
                if self.is_cancelled():
                    return False
                
                item = ensure_str(item)
                dest_path = safe_join(dest_dir, os.path.basename(item))
                
                # Check if destination exists
                if os.path.exists(dest_path):
                    logger.warning("[FileOps] Destination exists, cannot rename: %s", dest_path)
                    return False
                
                logger.debug("[FileOps] Renaming: %s -> %s", item, dest_path)
                os.rename(item, dest_path)
            
            logger.info("[FileOps] Rename move successful")
            return True
        except OSError as e:
            logger.debug("[FileOps] Rename failed (different filesystem): %s", e)
            return False
        except Exception as e:
            logger.error("[FileOps] Rename error: %s", e)
            return False
    
    def delete(self, items, use_trash=None):
        """
        Delete files/directories
        
        Args:
            items: List of paths to delete
            use_trash: Move to trash instead of permanent delete (default: from config)
            
        Returns:
            bool: True if successful
        """
        if use_trash is None:
            use_trash = self.use_trash
        
        logger.info("[FileOps] Starting delete operation")
        logger.info("[FileOps] Items to delete: %d", len(items))
        logger.info("[FileOps] Use trash: %s", use_trash)
        
        # Reset progress for delete operation
        with self.progress_lock:
            self.progress.reset()
        self.cancel_flag.clear()
        self.pause_flag.clear()
        
        with self.progress_lock:
            self.progress.files_total = len(items)
        
        # Setup trash if needed
        trash_dir = None
        if use_trash:
            trash_dir = "/tmp/.wg_trash"
            if not os.path.exists(trash_dir):
                try:
                    os.makedirs(trash_dir, mode=0o755, exist_ok=True)
                    logger.info("[FileOps] Created trash directory: %s", trash_dir)
                except Exception as e:
                    logger.error("[FileOps] Cannot create trash directory: %s", e)
                    use_trash = False
        
        success = True
        for i, item in enumerate(items):
            if self.is_cancelled():
                logger.info("[FileOps] Delete operation cancelled")
                success = False
                break
            
            item = ensure_str(item)
            with self.progress_lock:
                self.progress.current_file = ensure_unicode(os.path.basename(item))
                self.progress.files_done = i + 1
                self.progress.overall_percent = int((i + 1) * 100 / len(items))
            self.report_progress()
            
            logger.debug("[FileOps] Deleting: %s", item)
            
            try:
                if use_trash and trash_dir:
                    # Move to trash
                    trash_path = safe_join(trash_dir, os.path.basename(item))
                    
                    # Handle duplicate names in trash
                    counter = 1
                    while os.path.exists(trash_path):
                        name, ext = os.path.splitext(os.path.basename(item))
                        trash_path = safe_join(trash_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    logger.debug("[FileOps] Moving to trash: %s", trash_path)
                    shutil.move(item, trash_path)
                    logger.info("[FileOps] Moved to trash: %s", os.path.basename(item))
                    
                else:
                    # Permanent delete
                    if os.path.isfile(item) or os.path.islink(item):
                        os.remove(item)
                        logger.info("[FileOps] Deleted file: %s", os.path.basename(item))
                    elif os.path.isdir(item):
                        shutil.rmtree(item, ignore_errors=True)
                        logger.info("[FileOps] Deleted directory: %s", os.path.basename(item))
                        
            except Exception as e:
                error_msg = f"Cannot delete {os.path.basename(item)}: {str(e)}"
                logger.error("[FileOps] %s", error_msg)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                success = False
        
        # Final progress update
        if not self.is_cancelled():
            with self.progress_lock:
                self.progress.overall_percent = 100
            self.report_progress()
        
        if success and not self.is_cancelled():
            logger.info("[FileOps] Delete operation completed successfully")
        else:
            if self.is_cancelled():
                logger.info("[FileOps] Delete operation cancelled by user")
            else:
                logger.error("[FileOps] Delete operation failed with %d errors", 
                           len(self.progress.errors))
        
        return success and not self.is_cancelled()
    
    def rename(self, old_path, new_name):
        """
        Rename file/directory (preserves permissions automatically)
        
        Args:
            old_path: Current path
            new_name: New name (not full path)
            
        Returns:
            bool: True if successful
        """
        old_path = ensure_str(old_path)
        new_name = ensure_str(new_name)
        
        logger.info("[FileOps] Renaming: %s -> %s", old_path, new_name)
        
        try:
            new_path = safe_join(os.path.dirname(old_path), new_name)
            
            # Check if new name already exists
            if os.path.exists(new_path):
                error_msg = f"Cannot rename: {os.path.basename(new_path)} already exists"
                logger.error("[FileOps] %s", error_msg)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                return False
            
            os.rename(old_path, new_path)
            logger.info("[FileOps] Rename successful")
            return True
            
        except Exception as e:
            error_msg = f"Cannot rename {os.path.basename(old_path)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def create_directory(self, path, permissions=0o755):
        """
        Create directory with specific permissions
        
        Args:
            path: Directory path to create
            permissions: Directory permissions (default: 755)
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Creating directory: %s", path)
        logger.debug("[FileOps] Permissions: %s", oct(permissions)[-3:])
        
        try:
            os.makedirs(ensure_str(path), mode=permissions, exist_ok=True)
            logger.info("[FileOps] Directory created successfully")
            return True
        except Exception as e:
            error_msg = f"Cannot create directory {path}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def create_file(self, path, content="", permissions=0o644):
        """
        Create file with specific permissions
        
        Args:
            path: File path to create
            content: Initial content
            permissions: File permissions (default: 644)
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Creating file: %s", path)
        logger.debug("[FileOps] Permissions: %s, Content length: %d", 
                   oct(permissions)[-3:], len(content))
        
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.debug("[FileOps] Created parent directory: %s", dir_path)
            
            with open(ensure_str(path), 'w') as f:
                f.write(ensure_str(content))
            
            # Set permissions
            os.chmod(path, permissions)
            
            logger.info("[FileOps] File created successfully")
            return True
            
        except Exception as e:
            error_msg = f"Cannot create file {path}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def verify_file(self, file1, file2):
        """
        Verify two files are identical using MD5
        
        Args:
            file1: First file path
            file2: Second file path
            
        Returns:
            bool: True if files match
        """
        logger.debug("[FileOps] Verifying files: %s vs %s", file1, file2)
        
        try:
            hash1 = self._calculate_md5(file1)
            hash2 = self._calculate_md5(file2)
            
            match = hash1 == hash2
            logger.debug("[FileOps] Verification %s: %s == %s", 
                       "PASSED" if match else "FAILED", hash1[:8], hash2[:8])
            
            return match
        except Exception as e:
            logger.error("[FileOps] Verification error: %s", e)
            return False
    
    def _calculate_md5(self, filepath):
        """Calculate MD5 hash of file"""
        md5 = hashlib.md5()
        with open(ensure_str(filepath), 'rb') as f:
            while True:
                chunk = f.read(self.buffer_size)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()
    
    # ==================== PERMISSION METHODS ====================
    
    def get_permissions(self, path):
        """
        Get file permissions as octal number
        
        Args:
            path: File path
            
        Returns:
            str: Octal permissions string (e.g., '755') or None
        """
        try:
            mode = os.stat(path).st_mode
            perm_str = oct(mode)[-3:]
            logger.debug("[FileOps] Permissions for %s: %s", os.path.basename(path), perm_str)
            return perm_str
        except Exception as e:
            logger.error("[FileOps] Cannot get permissions for %s: %s", path, e)
            return None
    
    def get_permissions_string(self, path):
        """
        Get file permissions as rwx string
        
        Args:
            path: File path
            
        Returns:
            str: Permission string (e.g., 'rwxr-xr-x') or '----------'
        """
        try:
            mode = os.stat(path).st_mode
            
            perm_str = ''
            # File type
            if os.path.isdir(path):
                perm_str += 'd'
            elif os.path.islink(path):
                perm_str += 'l'
            else:
                perm_str += '-'
            
            # Owner permissions
            perm_str += 'r' if mode & stat.S_IRUSR else '-'
            perm_str += 'w' if mode & stat.S_IWUSR else '-'
            perm_str += 'x' if mode & stat.S_IXUSR else '-'
            
            # Group permissions
            perm_str += 'r' if mode & stat.S_IRGRP else '-'
            perm_str += 'w' if mode & stat.S_IWGRP else '-'
            perm_str += 'x' if mode & stat.S_IXGRP else '-'
            
            # Others permissions
            perm_str += 'r' if mode & stat.S_IROTH else '-'
            perm_str += 'w' if mode & stat.S_IWOTH else '-'
            perm_str += 'x' if mode & stat.S_IXOTH else '-'
            
            logger.debug("[FileOps] Permission string for %s: %s", os.path.basename(path), perm_str)
            return perm_str
        except Exception as e:
            logger.error("[FileOps] Cannot get permission string for %s: %s", path, e)
            return '----------'
    
    def set_permissions(self, path, permissions):
        """
        Set file permissions
        
        Args:
            path: File path
            permissions: Can be:
                - Octal string: '755'
                - Symbolic: 'rwxr-xr-x'
                - Integer: 0o755
                
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Setting permissions for: %s", path)
        
        try:
            if isinstance(permissions, str):
                if permissions.isdigit():
                    # Octal string
                    mode = int(permissions, 8)
                    logger.debug("[FileOps] Octal mode: %s -> %o", permissions, mode)
                elif len(permissions) == 9 or len(permissions) == 10:
                    # Symbolic notation
                    mode = 0
                    perm_str = permissions[-9:]  # Get last 9 chars
                    logger.debug("[FileOps] Symbolic: %s", perm_str)
                    
                    # Owner
                    if perm_str[0] == 'r':
                        mode |= stat.S_IRUSR
                    if perm_str[1] == 'w':
                        mode |= stat.S_IWUSR
                    if perm_str[2] == 'x':
                        mode |= stat.S_IXUSR
                    
                    # Group
                    if perm_str[3] == 'r':
                        mode |= stat.S_IRGRP
                    if perm_str[4] == 'w':
                        mode |= stat.S_IWGRP
                    if perm_str[5] == 'x':
                        mode |= stat.S_IXGRP
                    
                    # Others
                    if perm_str[6] == 'r':
                        mode |= stat.S_IROTH
                    if perm_str[7] == 'w':
                        mode |= stat.S_IWOTH
                    if perm_str[8] == 'x':
                        mode |= stat.S_IXOTH
                else:
                    logger.error("[FileOps] Invalid permission format: %s", permissions)
                    return False
            else:
                # Integer mode
                mode = permissions
                logger.debug("[FileOps] Integer mode: %o", mode)
            
            os.chmod(path, mode)
            logger.info("[FileOps] Permissions set successfully: %s", oct(mode)[-3:])
            return True
            
        except Exception as e:
            error_msg = f"Cannot set permissions for {os.path.basename(path)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def get_ownership(self, path):
        """
        Get file owner and group names
        
        Args:
            path: File path
            
        Returns:
            tuple: (user_name, group_name) or (None, None)
        """
        try:
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
            
            logger.debug("[FileOps] Ownership for %s: %s:%s", os.path.basename(path), user_name, group_name)
            return user_name, group_name
        except Exception as e:
            logger.error("[FileOps] Cannot get ownership for %s: %s", path, e)
            return None, None
    
    def set_ownership(self, path, user=None, group=None):
        """
        Change file owner/group (requires root)
        
        Args:
            path: File path
            user: Username or UID
            group: Groupname or GID
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Setting ownership for: %s", path)
        logger.debug("[FileOps] User: %s, Group: %s", user, group)
        
        try:
            uid = -1  # Don't change
            gid = -1  # Don't change
            
            if user is not None:
                if isinstance(user, int):
                    uid = user
                else:
                    try:
                        uid = pwd.getpwnam(user).pw_uid
                    except KeyError:
                        error_msg = f"User not found: {user}"
                        logger.error("[FileOps] %s", error_msg)
                        with self.progress_lock:
                            self.progress.errors.append(error_msg)
                        return False
            
            if group is not None:
                if isinstance(group, int):
                    gid = group
                else:
                    try:
                        gid = grp.getgrnam(group).gr_gid
                    except KeyError:
                        error_msg = f"Group not found: {group}"
                        logger.error("[FileOps] %s", error_msg)
                        with self.progress_lock:
                            self.progress.errors.append(error_msg)
                        return False
            
            # Check if we have root privileges
            if os.geteuid() != 0:
                error_msg = "Root privileges required to change ownership"
                logger.error("[FileOps] %s", error_msg)
                with self.progress_lock:
                    self.progress.errors.append(error_msg)
                return False
            
            os.chown(path, uid, gid)
            logger.info("[FileOps] Ownership set successfully")
            return True
            
        except Exception as e:
            error_msg = f"Cannot set ownership for {os.path.basename(path)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def copy_permissions(self, src, dst):
        """
        Copy permissions from source to destination
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Copying permissions: %s -> %s", src, dst)
        
        try:
            # Get source permissions
            src_stat = os.stat(src)
            
            # Apply to destination
            os.chmod(dst, src_stat.st_mode)
            logger.debug("[FileOps] Permissions copied: %s", oct(src_stat.st_mode)[-3:])
            
            # Copy ownership if root
            if os.geteuid() == 0:  # root
                os.chown(dst, src_stat.st_uid, src_stat.st_gid)
                logger.debug("[FileOps] Ownership copied: %s:%s", src_stat.st_uid, src_stat.st_gid)
            
            logger.info("[FileOps] Permissions copied successfully")
            return True
            
        except Exception as e:
            error_msg = f"Cannot copy permissions from {os.path.basename(src)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def change_file_mode(self, path, add_bits=None, remove_bits=None):
        """
        Add or remove specific permission bits
        
        Args:
            path: File path
            add_bits: Permission bits to add (e.g., stat.S_IWUSR)
            remove_bits: Permission bits to remove
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Changing file mode for: %s", path)
        logger.debug("[FileOps] Add bits: %s, Remove bits: %s", add_bits, remove_bits)
        
        try:
            current_mode = os.stat(path).st_mode
            
            if add_bits:
                current_mode |= add_bits
                logger.debug("[FileOps] Added bits: %o", add_bits)
            
            if remove_bits:
                current_mode &= ~remove_bits
                logger.debug("[FileOps] Removed bits: %o", remove_bits)
            
            os.chmod(path, current_mode)
            logger.info("[FileOps] File mode changed successfully: %s", oct(current_mode)[-3:])
            return True
            
        except Exception as e:
            error_msg = f"Cannot change file mode for {os.path.basename(path)}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def make_executable(self, path):
        """
        Make file executable for all users
        
        Args:
            path: File path
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Making executable: %s", path)
        return self.set_permissions(path, '755')
    
    def make_readonly(self, path):
        """
        Make file read-only for all users
        
        Args:
            path: File path
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Making read-only: %s", path)
        return self.set_permissions(path, '444')
    
    def make_writable(self, path):
        """
        Make file writable for owner
        
        Args:
            path: File path
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Making writable: %s", path)
        return self.set_permissions(path, '644')
    
    # ==================== UTILITY METHODS ====================
    
    def get_errors(self):
        """Get list of errors"""
        with self.progress_lock:
            return self.progress.errors.copy()
    
    def get_warnings(self):
        """Get list of warnings"""
        with self.progress_lock:
            return self.progress.warnings.copy()
    
    def clear_errors(self):
        """Clear all errors and warnings"""
        with self.progress_lock:
            self.progress.errors = []
            self.progress.warnings = []
    
    def get_file_info(self, path):
        """
        Get detailed file information
        
        Args:
            path: File path
            
        Returns:
            dict: File information
        """
        try:
            stat_info = os.stat(path)
            
            info = {
                'path': path,
                'name': os.path.basename(path),
                'size': stat_info.st_size,
                'size_formatted': format_size(stat_info.st_size),
                'is_dir': os.path.isdir(path),
                'is_file': os.path.isfile(path),
                'is_link': os.path.islink(path),
                'permissions': oct(stat_info.st_mode)[-3:],
                'permissions_string': self.get_permissions_string(path),
                'owner': stat_info.st_uid,
                'group': stat_info.st_gid,
                'created': stat_info.st_ctime,
                'modified': stat_info.st_mtime,
                'accessed': stat_info.st_atime,
            }
            
            # Get owner/group names
            user, group = self.get_ownership(path)
            if user:
                info['owner_name'] = user
            if group:
                info['group_name'] = group
            
            return info
            
        except Exception as e:
            logger.error("[FileOps] Cannot get file info for %s: %s", path, e)
            return None
    
    def calculate_directory_size(self, path):
        """
        Calculate total size of directory
        
        Args:
            path: Directory path
            
        Returns:
            int: Total size in bytes
        """
        total_size = 0
        file_count = 0
        
        logger.debug("[FileOps] Calculating directory size: %s", path)
        
        try:
            for root, dirs, files in os.walk(path):
                # Filter out directories we can't access
                dirs[:] = [d for d in dirs if os.access(os.path.join(root, d), os.R_OK | os.X_OK)]
                
                for f in files:
                    try:
                        filepath = safe_join(root, f)
                        if os.path.exists(filepath) and not os.path.islink(filepath):
                            total_size += os.path.getsize(filepath)
                            file_count += 1
                    except (OSError, PermissionError):
                        pass
        
        except Exception as e:
            logger.error("[FileOps] Error calculating directory size: %s", e)
        
        logger.debug("[FileOps] Directory size: %s (%d files)", format_size(total_size), file_count)
        return total_size
    
    def get_directory_contents(self, path):
        """
        Get directory contents with detailed info
        
        Args:
            path: Directory path
            
        Returns:
            list: List of file info dictionaries
        """
        contents = []
        
        try:
            for item in safe_listdir(path):
                item_path = safe_join(path, item)
                info = self.get_file_info(item_path)
                if info:
                    contents.append(info)
        
        except Exception as e:
            logger.error("[FileOps] Error getting directory contents: %s", e)
        
        return contents
    
    def compare_files(self, file1, file2):
        """
        Compare two files (size and content)
        
        Args:
            file1: First file path
            file2: Second file path
            
        Returns:
            dict: Comparison results
        """
        logger.debug("[FileOps] Comparing files: %s vs %s", file1, file2)
        
        result = {
            'identical': False,
            'size_match': False,
            'content_match': False,
            'size1': 0,
            'size2': 0,
            'hash1': '',
            'hash2': ''
        }
        
        try:
            # Compare sizes
            size1 = os.path.getsize(file1)
            size2 = os.path.getsize(file2)
            result['size1'] = size1
            result['size2'] = size2
            result['size_match'] = (size1 == size2)
            
            # Compare content if sizes match
            if result['size_match']:
                hash1 = self._calculate_md5(file1)
                hash2 = self._calculate_md5(file2)
                result['hash1'] = hash1
                result['hash2'] = hash2
                result['content_match'] = (hash1 == hash2)
                result['identical'] = result['content_match']
            
            logger.debug("[FileOps] Comparison result: %s", result)
            return result
            
        except Exception as e:
            logger.error("[FileOps] Error comparing files: %s", e)
            return result
    
    def create_symlink(self, target_path, link_path):
        """
        Create symbolic link
        
        Args:
            target_path: Target file/directory path
            link_path: Link path to create
            
        Returns:
            bool: True if successful
        """
        logger.info("[FileOps] Creating symlink: %s -> %s", link_path, target_path)
        
        try:
            os.symlink(target_path, link_path)
            logger.info("[FileOps] Symlink created successfully")
            return True
        except Exception as e:
            error_msg = f"Cannot create symlink {link_path}: {str(e)}"
            logger.error("[FileOps] %s", error_msg)
            with self.progress_lock:
                self.progress.errors.append(error_msg)
            return False
    
    def get_symlink_target(self, link_path):
        """
        Get symlink target
        
        Args:
            link_path: Symlink path
            
        Returns:
            str: Target path or None
        """
        try:
            target = os.readlink(link_path)
            logger.debug("[FileOps] Symlink target for %s: %s", link_path, target)
            return target
        except Exception as e:
            logger.error("[FileOps] Cannot read symlink target: %s", e)
            return None