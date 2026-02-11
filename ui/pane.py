"""
File pane widget - Single pane for dual-pane interface
Features: Visual indicators, icons, sorting, filtering
"""

from __future__ import absolute_import, print_function
import os
import stat

try:
    from Screens.Screen import Screen
    from Components.MenuList import MenuList
    from Components.FileList import FileList
    from Components.Label import Label
    from Components.ScrollLabel import ScrollLabel
    from Components.config import config
    from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, \
        eServiceReference, loadPNG, ePicLoad, getDesktop
    ENIGMA2_AVAILABLE = True
except ImportError:
    ENIGMA2_AVAILABLE = False
    Screen = object
    MenuList = object
    FileList = object

from Plugins.Extensions.WGFileManagerPro.core.compatibility import ensure_unicode, ensure_str, safe_listdir, safe_join
from Plugins.Extensions.WGFileManagerPro.utils.formatters import format_size, get_file_icon, is_hidden, human_sort_key, format_permissions_with_octal
from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger

logger = get_logger(__name__)


if ENIGMA2_AVAILABLE:
    
    class EnhancedFileList(FileList):
        """Enhanced file list with visual features - FIXED VERSION"""
        
        def __init__(self, directory, config=None, showDirectories=True, 
                     showFiles=True, showMountpoints=True, showHidden=False, 
                     useServiceRef=False, inhibitDirs=False, inhibitMounts=False, 
                     isTop=False, enableWrapAround=True, additionalExtensions=None):
            """
            Initialize enhanced file list - PROPERLY OVERRIDES FileList
            """
            logger.debug("[EnhancedFileList] Initializing with directory: %s", directory)
            
            # Store configuration
            self._config = config
            self._marked_files = set()
            
            # Load settings from config
            self._show_hidden = False
            self._show_size = True
            self._show_icons = True
            self._show_permissions = False
            self._sort_dirs_first = True
            
            if config:
                try:
                    self._show_hidden = config.get('show_hidden_files', False)
                    self._show_size = config.get('show_file_size', True)
                    self._show_icons = config.get('show_icons', True)
                    self._show_permissions = config.get('show_permissions', False)
                    self._sort_dirs_first = config.get('sort_dirs_first', True)
                except Exception as e:
                    logger.error("[EnhancedFileList] Config error: %s", e)
            
            # Override showHidden parameter with config value
            showHidden = self._show_hidden or showHidden
            
            # Call parent constructor with ALL required parameters
            FileList.__init__(
                self,
                directory,
                showDirectories=showDirectories,
                showFiles=showFiles,
                showMountpoints=showMountpoints,
                showHidden=showHidden,
                useServiceRef=useServiceRef,
                inhibitDirs=inhibitDirs,
                inhibitMounts=inhibitMounts,
                isTop=isTop,
                enableWrapAround=enableWrapAround,
                additionalExtensions=additionalExtensions
            )
            
            # Setup callbacks
            self.onSelectionChanged = []
            
            # Set custom font if needed
            try:
                desktop = getDesktop(0)
                screen_width = desktop.size().width()
                if screen_width >= 1920:
                    # HD/Full HD screens
                    self.l.setFont(0, gFont("Regular", 22))
                else:
                    # SD screens
                    self.l.setFont(0, gFont("Regular", 18))
            except:
                pass
            
            logger.info("[EnhancedFileList] Initialized: %s", directory)
        
        # ==================== ENHANCEMENT METHODS ====================
        
        def changeDir(self, directory, select=None):
            """
            Change directory with enhanced features
            
            Args:
                directory: New directory path
                select: File to select after change
            """
            logger.debug("[EnhancedFileList] changeDir to: %s", directory)
            
            try:
                # Call parent method
                result = FileList.changeDir(self, directory, select)
                
                # Apply our enhancements after directory change
                self._apply_enhancements()
                
                # Notify selection change
                self._notify_selection_changed()
                
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] changeDir error: %s", e)
                return False
        
        def _apply_enhancements(self):
            """Apply sorting and filtering to current list"""
            self._apply_sorting()
            self._apply_filtering()
        
        def _apply_sorting(self):
            """Apply custom sorting to file list"""
            if not hasattr(self, 'list') or not self.list:
                return
            
            try:
                # Get current list items with metadata
                items = []
                for idx, item in enumerate(self.list):
                    if isinstance(item, (list, tuple)) and len(item) > 0:
                        if isinstance(item[0], (list, tuple)) and len(item[0]) > 2:
                            path = item[0][0]
                            is_dir = item[0][1]
                            name = item[0][2]
                            items.append({
                                'idx': idx,
                                'path': path,
                                'is_dir': is_dir,
                                'name': name,
                                'item': item
                            })
                
                if not items:
                    return
                
                # Separate directories and files
                if self._sort_dirs_first:
                    dirs = []
                    files = []
                    
                    for item_info in items:
                        if item_info['is_dir']:
                            dirs.append(item_info)
                        else:
                            files.append(item_info)
                    
                    # Sort each group by name
                    dirs.sort(key=lambda x: human_sort_key(x['name'].lower()))
                    files.sort(key=lambda x: human_sort_key(x['name'].lower()))
                    
                    # Combine
                    sorted_items = dirs + files
                    self.list = [item['item'] for item in sorted_items]
                    
                else:
                    # Sort all together
                    self.list.sort(key=lambda x: human_sort_key(x[0][2].lower()) 
                                  if len(x[0]) > 2 else '')
                
                # Update display
                if hasattr(self, 'l'):
                    self.l.setList(self.list)
                    
                logger.debug("[EnhancedFileList] Applied sorting (%d items)", len(self.list))
                
            except Exception as e:
                logger.error("[EnhancedFileList] Sorting error: %s", e)
        
        def _apply_filtering(self):
            """Apply filtering (hide hidden files if configured)"""
            if self._show_hidden or not hasattr(self, 'list'):
                return
            
            try:
                # Filter out hidden files (starting with .)
                filtered_list = []
                for item in self.list:
                    if isinstance(item, (list, tuple)) and len(item) > 0:
                        if isinstance(item[0], (list, tuple)) and len(item[0]) > 2:
                            name = item[0][2]
                            if not is_hidden(name) or name == '..':
                                filtered_list.append(item)
                            else:
                                logger.debug("[EnhancedFileList] Filtered out: %s", name)
                
                self.list = filtered_list
                
                # Update display
                if hasattr(self, 'l'):
                    self.l.setList(self.list)
                    
                logger.debug("[EnhancedFileList] Applied filtering (%d -> %d items)", 
                           len(self.list) + (len(self.list) - len(filtered_list)), 
                           len(filtered_list))
                
            except Exception as e:
                logger.error("[EnhancedFileList] Filtering error: %s", e)
        
        def refresh(self):
            """Refresh file list with enhancements"""
            logger.debug("[EnhancedFileList] Refreshing")
            
            try:
                # Save current selection
                current_selection = None
                if hasattr(self, 'getCurrent'):
                    current = self.getCurrent()
                    if current:
                        if isinstance(current, eServiceReference):
                            current_selection = current.getPath()
                        elif isinstance(current, (list, tuple)) and len(current) > 0:
                            if isinstance(current[0], (list, tuple)) and len(current[0]) > 2:
                                current_selection = current[0][2]
                
                # Call parent refresh
                FileList.refresh(self)
                
                # Apply enhancements
                self._apply_enhancements()
                
                # Try to restore selection
                if current_selection and hasattr(self, 'moveToFile'):
                    try:
                        self.moveToFile(current_selection)
                    except:
                        pass
                
                # Notify selection change
                self._notify_selection_changed()
                
                logger.debug("[EnhancedFileList] Refresh complete")
                
            except Exception as e:
                logger.error("[EnhancedFileList] Refresh error: %s", e)
        
        # ==================== MARKING METHODS ====================
        
        def mark_file(self, path):
            """
            Mark file for batch operations
            
            Args:
                path: File path to mark
            """
            if not path:
                return
            
            path = ensure_unicode(path)
            if path in self._marked_files:
                self._marked_files.discard(path)
                logger.debug("[EnhancedFileList] Unmarked: %s", path)
            else:
                self._marked_files.add(path)
                logger.debug("[EnhancedFileList] Marked: %s", path)
            
            # Refresh display to show mark indicator
            if hasattr(self, 'l'):
                self.l.invalidate()
        
        def is_marked(self, path):
            """
            Check if file is marked
            
            Args:
                path: File path
                
            Returns:
                bool: True if marked
            """
            return ensure_unicode(path) in self._marked_files
        
        def get_marked_files(self):
            """
            Get list of marked files
            
            Returns:
                list: Marked file paths
            """
            return list(self._marked_files)
        
        def clear_marks(self):
            """Clear all marks"""
            self._marked_files.clear()
            if hasattr(self, 'l'):
                self.l.invalidate()
            logger.debug("[EnhancedFileList] Cleared all marks")
        
        # ==================== VIEW SETTINGS METHODS ====================
        
        def toggle_hidden_files(self):
            """Toggle display of hidden files"""
            self._show_hidden = not self._show_hidden
            
            # Update config if available
            if self._config:
                try:
                    self._config.set('show_hidden_files', self._show_hidden)
                except:
                    pass
            
            # Refresh to apply changes
            self.refresh()
            logger.info("[EnhancedFileList] Hidden files: %s", 
                       "SHOWN" if self._show_hidden else "HIDDEN")
        
        def toggle_permissions_display(self):
            """Toggle display of permissions"""
            self._show_permissions = not self._show_permissions
            
            # Update config if available
            if self._config:
                try:
                    self._config.set('show_permissions', self._show_permissions)
                except:
                    pass
            
            # Refresh display
            if hasattr(self, 'l'):
                self.l.invalidate()
            logger.info("[EnhancedFileList] Permissions display: %s", 
                       "ON" if self._show_permissions else "OFF")
        
        def toggle_size_display(self):
            """Toggle display of file sizes"""
            self._show_size = not self._show_size
            
            # Update config if available
            if self._config:
                try:
                    self._config.set('show_file_size', self._show_size)
                except:
                    pass
            
            # Refresh display
            if hasattr(self, 'l'):
                self.l.invalidate()
            logger.info("[EnhancedFileList] Size display: %s", 
                       "ON" if self._show_size else "OFF")
        
        def toggle_sort_dirs_first(self):
            """Toggle directory-first sorting"""
            self._sort_dirs_first = not self._sort_dirs_first
            
            # Update config if available
            if self._config:
                try:
                    self._config.set('sort_dirs_first', self._sort_dirs_first)
                except:
                    pass
            
            # Re-apply sorting
            self._apply_sorting()
            logger.info("[EnhancedFileList] Sort dirs first: %s", 
                       "ON" if self._sort_dirs_first else "OFF")
        
        # ==================== SELECTION & INFO METHODS ====================
        
        def get_selection(self):
            """
            Get current selection - ENHANCED VERSION
            
            Returns:
                tuple: (path, is_dir, name) or None
            """
            try:
                current = self.getCurrent()
                if not current:
                    return None
                
                # Handle different return types
                if isinstance(current, eServiceReference):
                    # Service reference from parent class
                    path = current.getPath()
                    if path:
                        name = os.path.basename(path)
                        is_dir = os.path.isdir(path)
                        return (path, is_dir, name)
                
                elif isinstance(current, (list, tuple)):
                    # List/tuple from parent class
                    if len(current) > 0:
                        if isinstance(current[0], (list, tuple)) and len(current[0]) > 2:
                            # Standard format: [[path, is_dir, name, ...], ...]
                            path = current[0][0]
                            is_dir = current[0][1]
                            name = current[0][2]
                            return (path, is_dir, name)
                        elif len(current) > 2:
                            # Alternative format: [path, is_dir, name, ...]
                            path = current[0]
                            is_dir = current[1]
                            name = current[2]
                            return (path, is_dir, name)
                
                # Try to get from service reference
                if hasattr(self, 'getServiceRef'):
                    service_ref = self.getServiceRef()
                    if service_ref:
                        path = service_ref.getPath()
                        if path:
                            name = os.path.basename(path)
                            is_dir = os.path.isdir(path)
                            return (path, is_dir, name)
                
                logger.debug("[EnhancedFileList] Could not parse selection: %s", type(current))
                return None
                
            except Exception as e:
                logger.error("[EnhancedFileList] get_selection error: %s", e)
                return None
        
        def get_info_text(self):
            """
            Get info text for selected file
            
            Returns:
                str: Info text with size, permissions, etc.
            """
            selection = self.get_selection()
            if not selection:
                return "No selection"
            
            try:
                path, is_dir, name = selection
                info_parts = []
                
                if name == '..':
                    return "Parent directory"
                
                if is_dir:
                    # Count items in directory
                    try:
                        items = safe_listdir(path)
                        count = len(items)
                        info_parts.append(f"{count} item{'s' if count != 1 else ''}")
                    except Exception as e:
                        logger.debug("[EnhancedFileList] Directory count error: %s", e)
                        info_parts.append("Directory")
                else:
                    # Show file size
                    try:
                        size = os.path.getsize(ensure_str(path))
                        info_parts.append(format_size(size))
                    except:
                        info_parts.append("File")
                
                # Add permissions if enabled
                if self._show_permissions:
                    try:
                        perms = format_permissions_with_octal(path)
                        info_parts.append(perms)
                    except:
                        pass
                
                # Add marked status
                if self.is_marked(path):
                    info_parts.append("MARKED")
                
                return " | ".join(info_parts) if info_parts else "No info"
                
            except Exception as e:
                logger.error("[EnhancedFileList] get_info_text error: %s", e)
                return "Error getting info"
        
        def get_current_directory(self):
            """
            Get current directory path
            
            Returns:
                str: Current directory path
            """
            try:
                return self.getCurrentDirectory()
            except:
                return "/"
        
        # ==================== DISPLAY ENHANCEMENTS ====================
        
        def buildEntry(self, service_ref, name, isDir):
            """
            Build display entry for file list - OVERRIDES parent method
            
            Args:
                service_ref: Service reference
                name: File/directory name
                isDir: True if directory
                
            Returns:
                list: Display entry for eListboxPythonMultiContent
            """
            # Call parent method first
            entry = FileList.buildEntry(self, service_ref, name, isDir)
            
            if not entry or len(entry) < 1:
                return entry
            
            try:
                # Get the first element (usually a list)
                if isinstance(entry[0], list):
                    display_item = entry[0]
                    
                    # Get path from service reference
                    path = service_ref.getPath() if service_ref else ""
                    
                    # Add icon at beginning if enabled
                    if self._show_icons:
                        icon = get_file_icon(name, isDir)
                        # Insert icon at position 0 (before text)
                        if len(display_item) > 0:
                            # Convert to list to modify
                            if isinstance(display_item, tuple):
                                display_item = list(display_item)
                            
                            # Ensure we have enough elements
                            while len(display_item) < 3:
                                display_item.append("")
                            
                            # Add icon before name
                            display_item[2] = f"{icon} {display_item[2]}"
                    
                    # Add size if enabled and not directory
                    if self._show_size and not isDir and name != '..':
                        try:
                            if path and os.path.exists(path):
                                size = os.path.getsize(path)
                                size_str = format_size(size)
                                # Append size to display text
                                if len(display_item) > 2:
                                    display_item[2] = f"{display_item[2]}  [{size_str}]"
                        except:
                            pass
                    
                    # Add permissions if enabled
                    if self._show_permissions and path and os.path.exists(path) and name != '..':
                        try:
                            perms = format_permissions_with_octal(path)
                            # Prepend permissions
                            if len(display_item) > 2:
                                display_item[2] = f"{perms} {display_item[2]}"
                        except:
                            pass
                    
                    # Add mark indicator
                    if path and self.is_marked(path):
                        if len(display_item) > 2:
                            display_item[2] = f"✓ {display_item[2]}"
                    
                    entry[0] = tuple(display_item) if isinstance(display_item, list) else display_item
                
                return entry
                
            except Exception as e:
                logger.error("[EnhancedFileList] buildEntry error: %s", e)
                return entry
        
        # ==================== NAVIGATION OVERRIDES ====================
        
        def up(self):
            """Move selection up - OVERRIDE"""
            logger.debug("[EnhancedFileList] up()")
            try:
                result = FileList.up(self)
                self._notify_selection_changed()
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] up() error: %s", e)
                return False
        
        def down(self):
            """Move selection down - OVERRIDE"""
            logger.debug("[EnhancedFileList] down()")
            try:
                result = FileList.down(self)
                self._notify_selection_changed()
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] down() error: %s", e)
                return False
        
        def pageUp(self):
            """Page up - OVERRIDE"""
            logger.debug("[EnhancedFileList] pageUp()")
            try:
                result = FileList.pageUp(self)
                self._notify_selection_changed()
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] pageUp() error: %s", e)
                return False
        
        def pageDown(self):
            """Page down - OVERRIDE"""
            logger.debug("[EnhancedFileList] pageDown()")
            try:
                result = FileList.pageDown(self)
                self._notify_selection_changed()
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] pageDown() error: %s", e)
                return False
        
        def moveTo(self, index):
            """Move to specific index - OVERRIDE"""
            logger.debug("[EnhancedFileList] moveTo(%d)", index)
            try:
                result = FileList.moveTo(self, index)
                self._notify_selection_changed()
                return result
            except Exception as e:
                logger.error("[EnhancedFileList] moveTo() error: %s", e)
                return False
        
        # ==================== EVENT HANDLING ====================
        
        def _notify_selection_changed(self):
            """Notify all selection change callbacks"""
            for callback in self.onSelectionChanged:
                try:
                    callback()
                except Exception as e:
                    logger.error("[EnhancedFileList] Callback error: %s", e)
        
        def selectionChanged(self):
            """Handle selection changes - OVERRIDE"""
            # Call parent if it exists
            if hasattr(FileList, 'selectionChanged'):
                try:
                    FileList.selectionChanged(self)
                except:
                    pass
            
            # Notify our callbacks
            self._notify_selection_changed()
        
        # ==================== UTILITY METHODS ====================
        
        def get_file_count(self):
            """Get count of files in current directory"""
            try:
                current_dir = self.getCurrentDirectory()
                if os.path.isdir(current_dir):
                    items = safe_listdir(current_dir)
                    # Filter out hidden files if not showing them
                    if not self._show_hidden:
                        items = [item for item in items if not is_hidden(item)]
                    return len(items)
            except:
                pass
            return 0
        
        def get_directory_size(self):
            """Get total size of current directory"""
            total_size = 0
            try:
                current_dir = self.getCurrentDirectory()
                for dirpath, dirnames, filenames in os.walk(current_dir):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            try:
                                total_size += os.path.getsize(fp)
                            except:
                                pass
            except:
                pass
            return total_size
        
        def is_empty(self):
            """Check if current directory is empty"""
            try:
                current_dir = self.getCurrentDirectory()
                items = safe_listdir(current_dir)
                # Filter out hidden files if not showing them
                if not self._show_hidden:
                    items = [item for item in items if not is_hidden(item)]
                return len(items) == 0
            except:
                return True
        
        def get_settings(self):
            """Get current display settings"""
            return {
                'show_hidden': self._show_hidden,
                'show_size': self._show_size,
                'show_icons': self._show_icons,
                'show_permissions': self._show_permissions,
                'sort_dirs_first': self._sort_dirs_first
            }
        
        def __str__(self):
            """String representation for debugging"""
            try:
                current_dir = self.getCurrentDirectory()
                selection = self.get_selection()
                marked_count = len(self._marked_files)
                return f"EnhancedFileList(dir='{current_dir}', selected='{selection}', marked={marked_count})"
            except:
                return "EnhancedFileList(Error getting info)"


else:
    # Non-Enigma2 file pane (for testing)
    
    class EnhancedFileList:
        """Simple file list for testing without Enigma2"""
        
        def __init__(self, directory, config=None, **kwargs):
            logger.info("[EnhancedFileList] Test mode: %s", directory)
            self.directory = directory
            self.config = config
            self.marked_files = set()
            self.current_index = 0
            self.items = []
            
            # Load settings
            self.show_hidden = False
            self.show_size = True
            self.show_icons = True
            self.show_permissions = False
            self.sort_dirs_first = True
            
            if config:
                try:
                    self.show_hidden = config.get('show_hidden_files', False)
                    self.show_size = config.get('show_file_size', True)
                    self.show_icons = config.get('show_icons', True)
                    self.show_permissions = config.get('show_permissions', False)
                    self.sort_dirs_first = config.get('sort_dirs_first', True)
                except:
                    pass
            
            # Populate items
            self.refresh()
            
            # Callbacks
            self.onSelectionChanged = []
        
        def refresh(self):
            """Refresh file list"""
            self.items = []
            
            # Add parent entry if not root
            if self.directory != '/':
                parent = os.path.dirname(self.directory)
                self.items.append((parent, True, '..', 0))
            
            try:
                # List directory
                for name in safe_listdir(self.directory):
                    # Skip hidden files if configured
                    if not self.show_hidden and is_hidden(name):
                        continue
                    
                    path = safe_join(self.directory, name)
                    is_dir = os.path.isdir(path)
                    
                    # Get size
                    size = 0
                    if not is_dir:
                        try:
                            size = os.path.getsize(path)
                        except:
                            pass
                    
                    self.items.append((path, is_dir, name, size))
                
                # Apply sorting
                if self.sort_dirs_first:
                    dirs = []
                    files = []
                    
                    for item in self.items:
                        path, is_dir, name, size = item
                        if name == '..':
                            dirs.append(item)
                        elif is_dir:
                            dirs.append(item)
                        else:
                            files.append(item)
                    
                    # Sort each group
                    dirs.sort(key=lambda x: human_sort_key(x[2]))
                    files.sort(key=lambda x: human_sort_key(x[2]))
                    
                    self.items = dirs + files
                else:
                    self.items.sort(key=lambda x: human_sort_key(x[2]))
                    
            except Exception as e:
                logger.error("[EnhancedFileList] Test refresh error: %s", e)
        
        def get_selection(self):
            """Get current selection"""
            if 0 <= self.current_index < len(self.items):
                path, is_dir, name, size = self.items[self.current_index]
                return (path, is_dir, name)
            return None
        
        def up(self):
            """Move selection up"""
            if self.current_index > 0:
                self.current_index -= 1
                self._notify_selection_changed()
                return True
            return False
        
        def down(self):
            """Move selection down"""
            if self.current_index < len(self.items) - 1:
                self.current_index += 1
                self._notify_selection_changed()
                return True
            return False
        
        def pageUp(self):
            """Page up"""
            if self.current_index >= 10:
                self.current_index -= 10
            else:
                self.current_index = 0
            self._notify_selection_changed()
            return True
        
        def pageDown(self):
            """Page down"""
            if self.current_index <= len(self.items) - 11:
                self.current_index += 10
            else:
                self.current_index = len(self.items) - 1
            self._notify_selection_changed()
            return True
        
        def changeDir(self, directory, select=None):
            """Change directory"""
            if os.path.isdir(directory):
                self.directory = directory
                self.current_index = 0
                self.refresh()
                self._notify_selection_changed()
                return True
            return False
        
        def getCurrentDirectory(self):
            """Get current directory"""
            return self.directory
        
        def mark_file(self, path):
            """Mark/unmark file"""
            path = ensure_unicode(path)
            if path in self.marked_files:
                self.marked_files.discard(path)
            else:
                self.marked_files.add(path)
        
        def is_marked(self, path):
            """Check if file is marked"""
            return ensure_unicode(path) in self.marked_files
        
        def get_marked_files(self):
            """Get marked files"""
            return list(self.marked_files)
        
        def clear_marks(self):
            """Clear all marks"""
            self.marked_files.clear()
        
        def get_info_text(self):
            """Get info text"""
            selection = self.get_selection()
            if not selection:
                return "No selection"
            
            path, is_dir, name = selection
            
            if name == '..':
                return "Parent directory"
            
            if is_dir:
                try:
                    items = safe_listdir(path)
                    count = len(items)
                    return f"{count} item{'s' if count != 1 else ''}"
                except:
                    return "Directory"
            else:
                try:
                    size = os.path.getsize(path)
                    return format_size(size)
                except:
                    return "File"
        
        def _notify_selection_changed(self):
            """Notify selection change"""
            for callback in self.onSelectionChanged:
                try:
                    callback()
                except:
                    pass


# FilePane class (non-Enigma2 compatible)
class FilePane:
    """
    File pane for dual-pane interface
    Non-Enigma2 compatible version - for testing only
    """
    
    def __init__(self, directory, config=None):
        """
        Initialize file pane
        
        Args:
            directory: Initial directory
            config: Configuration object
        """
        self.directory = ensure_str(directory)
        self.config = config
        self.marked_files = set()
        self.history = []
        self.history_pos = -1
        self.show_hidden = False
        self.show_permissions = False
        
        if config:
            try:
                self.show_hidden = config.get('show_hidden_files', False)
                self.show_permissions = config.get('show_permissions', False)
            except:
                pass
    
    def change_directory(self, path):
        """
        Change current directory
        
        Args:
            path: New directory path
        """
        path = ensure_str(path)
        if os.path.isdir(path):
            # Add to history
            if self.history_pos < len(self.history) - 1:
                self.history = self.history[:self.history_pos + 1]
            self.history.append(self.directory)
            self.history_pos += 1
            
            self.directory = path
            return True
        return False
    
    def go_back(self):
        """Go back in history"""
        if self.history_pos > 0:
            self.history_pos -= 1
            self.directory = self.history[self.history_pos]
            return True
        return False
    
    def go_forward(self):
        """Go forward in history"""
        if self.history_pos < len(self.history) - 1:
            self.history_pos += 1
            self.directory = self.history[self.history_pos]
            return True
        return False
    
    def get_parent_directory(self):
        """Get parent directory path"""
        return os.path.dirname(self.directory)
    
    def go_to_parent(self):
        """Navigate to parent directory"""
        parent = self.get_parent_directory()
        if parent and parent != self.directory:
            return self.change_directory(parent)
        return False
    
    def list_directory(self):
        """
        List current directory contents
        
        Returns:
            list: List of (path, is_dir, name, size, permissions) tuples
        """
        items = []
        
        try:
            # Add parent entry if not root
            if self.directory != '/':
                parent = self.get_parent_directory()
                items.append((parent, True, '..', 0, ''))
            
            # List directory
            for name in safe_listdir(self.directory):
                # Skip hidden files if configured
                if not self.show_hidden and is_hidden(name):
                    continue
                
                path = safe_join(self.directory, name)
                is_dir = os.path.isdir(path)
                
                # Get size
                size = 0
                if not is_dir:
                    try:
                        size = os.path.getsize(path)
                    except:
                        pass
                
                # Get permissions
                permissions = ''
                if self.show_permissions:
                    try:
                        permissions = format_permissions_with_octal(path)
                    except:
                        pass
                
                items.append((path, is_dir, name, size, permissions))
            
            # Sort: directories first, then by name
            items.sort(key=lambda x: (not x[1], human_sort_key(x[2])))
            
        except Exception as e:
            logger.error("[FilePane] Error listing directory: %s", e)
        
        return items
    
    def mark_file(self, path):
        """Mark/unmark file"""
        path = ensure_unicode(path)
        if path in self.marked_files:
            self.marked_files.remove(path)
        else:
            self.marked_files.add(path)
    
    def is_marked(self, path):
        """Check if file is marked"""
        return ensure_unicode(path) in self.marked_files
    
    def get_marked_files(self):
        """Get marked files list"""
        return list(self.marked_files)
    
    def clear_marks(self):
        """Clear all marks"""
        self.marked_files.clear()