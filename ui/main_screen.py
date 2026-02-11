"""
Main Screen - Dual-pane file manager interface
Features: Visual dual panes, arrow navigation, progress bars
"""

from __future__ import absolute_import, print_function
import os
import threading

try:
    from Screens.Screen import Screen
    from Screens.MessageBox import MessageBox
    from Components.ActionMap import ActionMap, NumberActionMap
    from Components.Label import Label
    from Components.config import config, configfile
    from enigma import getDesktop, eTimer, ePoint
    ENIGMA2_AVAILABLE = True
except ImportError:
    ENIGMA2_AVAILABLE = False
    Screen = object

from Plugins.Extensions.WGFileManagerPro.core.config import get_config
from Plugins.Extensions.WGFileManagerPro.core.file_ops import FileOperations
from Plugins.Extensions.WGFileManagerPro.utils.formatters import format_disk_usage, get_file_icon, is_media_file, format_permissions_with_octal
from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger
from Plugins.Extensions.WGFileManagerPro.ui.pane import EnhancedFileList
from Plugins.Extensions.WGFileManagerPro.ui.progress import create_progress_dialog
from Plugins.Extensions.WGFileManagerPro.ui.permission_dialog import PermissionDialog

logger = get_logger(__name__)


if ENIGMA2_AVAILABLE:
    
    class WGFileManagerMain(Screen):
        """Main dual-pane file manager screen"""
        
        # Dynamic skin - adjusts to screen size
        skin = """
            <screen position="center,center" size="1280,720" title="WG File Manager Pro">
                <!-- Title bar -->
                <widget name="title" position="10,10" size="1260,40" font="Regular;28" />
                <widget name="disk_info" position="10,50" size="1260,25" font="Regular;18" halign="right" />
                
                <!-- Left pane -->
                <widget name="left_title" position="10,85" size="620,30" font="Regular;22" />
                <widget name="left_pane" position="10,120" size="620,480" scrollbarMode="showOnDemand" enableWrapAround="1" />
                <widget name="left_info" position="10,605" size="620,25" font="Regular;18" />
                
                <!-- Right pane -->
                <widget name="right_title" position="650,85" size="620,30" font="Regular;22" />
                <widget name="right_pane" position="650,120" size="620,480" scrollbarMode="showOnDemand" enableWrapAround="1" />
                <widget name="right_info" position="650,605" size="620,25" font="Regular;18" />
                
                <!-- Status bar -->
                <widget name="status_bar" position="10,635" size="1260,25" font="Regular;18" />
                
                <!-- Button bar -->
                <widget name="button_bar" position="10,665" size="1260,40" font="Regular;20" halign="center" valign="center" />
            </screen>
        """
        
        def __init__(self, session):
            """
            Initialize main screen
            
            Args:
                session: Enigma2 session
            """
            Screen.__init__(self, session)
            logger.info("[MainScreen] Initializing WG File Manager Pro")
            
            # Configuration
            self.config = get_config()
            
            # Get screen size for dynamic layout
            desktop = getDesktop(0)
            self.screen_width = desktop.size().width()
            self.screen_height = desktop.size().height()
            
            # State
            self.active_pane = 'left'
            self.marked_files = set()
            self.clipboard = []
            self.clipboard_mode = None  # 'copy' or 'move'
            self.operation_in_progress = False
            
            # File operations
            self.file_ops = FileOperations(progress_callback=self.on_progress_update)
            
            # Get initial paths from config
            left_path = self.config.get('left_path', '/media/hdd')
            right_path = self.config.get('right_path', '/tmp')
            
            # Validate paths
            if not os.path.exists(left_path):
                left_path = '/media/hdd' if os.path.exists('/media/hdd') else '/'
            if not os.path.exists(right_path):
                right_path = '/tmp'
            
            logger.info("[MainScreen] Left path: %s, Right path: %s", left_path, right_path)
            
            # UI Components
            self["title"] = Label("WG File Manager Pro")
            self["disk_info"] = Label("")
            self["status_bar"] = Label("Ready")
            
            # Left pane
            self["left_title"] = Label(left_path)
            self["left_pane"] = EnhancedFileList(
                left_path, 
                config=self.config,
                showDirectories=True,
                showFiles=True,
                showMountpoints=True,
                showHidden=self.config.get('show_hidden_files', False),
                enableWrapAround=True
            )
            self["left_info"] = Label("")
            
            # Right pane
            self["right_title"] = Label(right_path)
            self["right_pane"] = EnhancedFileList(
                right_path, 
                config=self.config,
                showDirectories=True,
                showFiles=True,
                showMountpoints=True,
                showHidden=self.config.get('show_hidden_files', False),
                enableWrapAround=True
            )
            self["right_info"] = Label("")
            
            # Button bar
            self["button_bar"] = Label("")
            
            # Setup actions
            self.setup_actions()
            
            # Update timer
            self.update_timer = eTimer()
            self.update_timer.callback.append(self.update_info)
            
            # Initialize on layout finish
            self.onLayoutFinish.append(self.on_layout_finish)
            
            logger.info("[MainScreen] Initialization complete")
        
        def setup_actions(self):
            """Setup keyboard/remote actions - COMPLETE FIX"""
            # Try different action map names for compatibility
            self["actions"] = ActionMap(
                ["WGFileManagerActions", "MenuActions", "InfobarMenuActions", "DirectionActions", "ColorActions", "MovieSelectionActions"],
                {
                    # Navigation - using standard Enigma2 action names
                    "up": self.key_up,
                    "down": self.key_down,
                    "left": self.key_left,
                    "right": self.key_right,
                    "channelUp": self.key_page_up,
                    "channelDown": self.key_page_down,
                    
                    # Actions
                    "ok": self.key_ok,
                    "cancel": self.key_exit,
                    "menu": self.key_menu,
                    
                    # Color buttons
                    "red": self.key_delete,
                    "green": self.key_copy,
                    "yellow": self.key_move,
                    "blue": self.key_mark,
                    
                    # Info button for permissions
                    "info": self.key_permissions,
                    
                    # Additional navigation
                    "nextBouquet": self.key_page_up,
                    "prevBouquet": self.key_page_down,
                    
                    # Number keys
                    "0": lambda: self.key_number(0),
                    "1": lambda: self.key_number(1),
                    "2": lambda: self.key_number(2),
                    "3": lambda: self.key_number(3),
                    "4": lambda: self.key_number(4),
                    "5": lambda: self.key_number(5),
                    "6": lambda: self.key_number(6),
                    "7": lambda: self.key_number(7),
                    "8": lambda: self.key_number(8),
                    "9": lambda: self.key_number(9),
                },
                -1  # Priority
            )
            
            # Also create a separate number action map
            self["number_actions"] = NumberActionMap(
                ["NumberActions"],
                {
                    "0": lambda: self.key_number(0),
                    "1": lambda: self.key_number(1),
                    "2": lambda: self.key_number(2),
                    "3": lambda: self.key_number(3),
                    "4": lambda: self.key_number(4),
                    "5": lambda: self.key_number(5),
                    "6": lambda: self.key_number(6),
                    "7": lambda: self.key_number(7),
                    "8": lambda: self.key_number(8),
                    "9": lambda: self.key_number(9),
                },
                -1
            )
        
        def on_layout_finish(self):
            """Called when layout is finished - FIXED"""
            logger.debug("[MainScreen] Layout finished")
            
            # Set active pane highlight
            self.update_pane_highlight()
            
            # Set initial focus
            self.set_focus_to_active_pane()
            
            # Update info displays
            self.update_info()
            
            # Connect selection change callbacks
            self.connect_selection_callbacks()
            
            # Start update timer (1 second intervals)
            self.update_timer.start(1000, False)
            
            # Update button bar
            self.update_button_bar()
            
            # Set status
            self["status_bar"].setText("Navigation: ↑↓←→ OK=Open EXIT=Back")
            
            logger.info("[MainScreen] Layout setup complete, ready for user input")
        
        def connect_selection_callbacks(self):
            """Connect selection change callbacks to both panes"""
            try:
                # Check if panes have onSelectionChanged attribute
                if hasattr(self["left_pane"], 'onSelectionChanged'):
                    self["left_pane"].onSelectionChanged.append(self.on_selection_changed)
                    logger.debug("[MainScreen] Connected left pane selection callback")
                
                if hasattr(self["right_pane"], 'onSelectionChanged'):
                    self["right_pane"].onSelectionChanged.append(self.on_selection_changed)
                    logger.debug("[MainScreen] Connected right pane selection callback")
            except Exception as e:
                logger.error("[MainScreen] Error connecting callbacks: %s", e)
        
        def set_focus_to_active_pane(self):
            """Set keyboard focus to active pane - FIXED"""
            try:
                logger.debug("[MainScreen] Setting focus to %s pane", self.active_pane)
                
                if self.active_pane == 'left':
                    # Enable left pane, disable right
                    if hasattr(self["left_pane"], 'selectionEnabled'):
                        self["left_pane"].selectionEnabled(1)
                    if hasattr(self["right_pane"], 'selectionEnabled'):
                        self["right_pane"].selectionEnabled(0)
                    
                    # Move instance to front
                    try:
                        self.instance.moveSelectionTo(self["left_pane"].instance)
                    except:
                        pass
                else:
                    # Enable right pane, disable left
                    if hasattr(self["left_pane"], 'selectionEnabled'):
                        self["left_pane"].selectionEnabled(0)
                    if hasattr(self["right_pane"], 'selectionEnabled'):
                        self["right_pane"].selectionEnabled(1)
                    
                    # Move instance to front
                    try:
                        self.instance.moveSelectionTo(self["right_pane"].instance)
                    except:
                        pass
            except Exception as e:
                logger.error("[MainScreen] Error setting focus: %s", e)
        
        def get_active_pane(self):
            """Get active pane widget"""
            return self["left_pane"] if self.active_pane == 'left' else self["right_pane"]
        
        def get_inactive_pane(self):
            """Get inactive pane widget"""
            return self["right_pane"] if self.active_pane == 'left' else self["left_pane"]
        
        def update_pane_highlight(self):
            """Update visual highlight for active pane"""
            try:
                left_dir = self["left_pane"].getCurrentDirectory()
                right_dir = self["right_pane"].getCurrentDirectory()
                
                if self.active_pane == 'left':
                    self["left_title"].setText("▶ " + left_dir)
                    self["right_title"].setText("  " + right_dir)
                else:
                    self["left_title"].setText("  " + left_dir)
                    self["right_title"].setText("▶ " + right_dir)
            except Exception as e:
                logger.error("[MainScreen] Error updating pane highlight: %s", e)
        
        def update_info(self):
            """Update information displays"""
            try:
                # Update disk info
                active_dir = self.get_active_pane().getCurrentDirectory()
                disk_info = format_disk_usage(active_dir)
                self["disk_info"].setText("Disk: %s" % disk_info)
                
                # Update pane info
                left_info = self.get_pane_info(self["left_pane"])
                right_info = self.get_pane_info(self["right_pane"])
                
                # Add marked files count
                left_marked = len(self["left_pane"].get_marked_files())
                right_marked = len(self["right_pane"].get_marked_files())
                
                if left_marked > 0:
                    left_info += " | Marked: %d" % left_marked
                if right_marked > 0:
                    right_info += " | Marked: %d" % right_marked
                
                self["left_info"].setText(left_info)
                self["right_info"].setText(right_info)
                
                # Update status bar with current selection
                selection = self.get_active_pane().get_selection()
                if selection:
                    path, is_dir, name = selection
                    status = f"Selected: {name} {'(Dir)' if is_dir else ''}"
                    self["status_bar"].setText(status)
                
            except Exception as e:
                logger.error("[MainScreen] Update info error: %s", e)
        
        def get_pane_info(self, pane):
            """Get info text for a pane"""
            try:
                return pane.get_info_text()
            except:
                return ""
        
        def on_selection_changed(self):
            """Called when selection changes in any pane"""
            self.update_info()
        
        def update_button_bar(self):
            """Update button bar text"""
            try:
                if self.clipboard:
                    mode = "COPY" if self.clipboard_mode == 'copy' else "MOVE"
                    text = "🟢Copy 🟡Move 🔴Delete 🔵Mark ℹ️Perms | Clipboard: %s (%d)" % (mode, len(self.clipboard))
                else:
                    text = "🟢Copy 🟡Move 🔴Delete 🔵Mark ℹ️Permissions"
                
                self["button_bar"].setText(text)
            except Exception as e:
                logger.error("[MainScreen] Error updating button bar: %s", e)
        
        # ==================== NAVIGATION METHODS ====================
        
        def key_up(self):
            """Move selection up"""
            logger.debug("[MainScreen] Key UP pressed")
            try:
                pane = self.get_active_pane()
                if hasattr(pane, 'up'):
                    pane.up()
                    self.update_info()
                else:
                    logger.error("[MainScreen] Pane has no 'up' method")
            except Exception as e:
                logger.error("[MainScreen] key_up error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_down(self):
            """Move selection down"""
            logger.debug("[MainScreen] Key DOWN pressed")
            try:
                pane = self.get_active_pane()
                if hasattr(pane, 'down'):
                    pane.down()
                    self.update_info()
                else:
                    logger.error("[MainScreen] Pane has no 'down' method")
            except Exception as e:
                logger.error("[MainScreen] key_down error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_left(self):
            """Switch to left pane"""
            logger.debug("[MainScreen] Key LEFT pressed")
            try:
                if self.active_pane != 'left':
                    self.active_pane = 'left'
                    self.update_pane_highlight()
                    self.set_focus_to_active_pane()
                    self.update_info()
                    self["status_bar"].setText("Switched to LEFT pane")
                else:
                    # Already in left pane, maybe scroll left?
                    self["status_bar"].setText("Already in left pane")
            except Exception as e:
                logger.error("[MainScreen] key_left error: %s", e)
        
        def key_right(self):
            """Switch to right pane"""
            logger.debug("[MainScreen] Key RIGHT pressed")
            try:
                if self.active_pane != 'right':
                    self.active_pane = 'right'
                    self.update_pane_highlight()
                    self.set_focus_to_active_pane()
                    self.update_info()
                    self["status_bar"].setText("Switched to RIGHT pane")
                else:
                    # Already in right pane, maybe scroll right?
                    self["status_bar"].setText("Already in right pane")
            except Exception as e:
                logger.error("[MainScreen] key_right error: %s", e)
        
        def key_page_up(self):
            """Page up"""
            logger.debug("[MainScreen] Key PAGE UP pressed")
            try:
                pane = self.get_active_pane()
                if hasattr(pane, 'pageUp'):
                    pane.pageUp()
                    self.update_info()
                    self["status_bar"].setText("Page Up")
                else:
                    logger.error("[MainScreen] Pane has no 'pageUp' method")
            except Exception as e:
                logger.error("[MainScreen] key_page_up error: %s", e)
        
        def key_page_down(self):
            """Page down"""
            logger.debug("[MainScreen] Key PAGE DOWN pressed")
            try:
                pane = self.get_active_pane()
                if hasattr(pane, 'pageDown'):
                    pane.pageDown()
                    self.update_info()
                    self["status_bar"].setText("Page Down")
                else:
                    logger.error("[MainScreen] Pane has no 'pageDown' method")
            except Exception as e:
                logger.error("[MainScreen] key_page_down error: %s", e)
        
        def key_number(self, number):
            """Quick jump using number keys"""
            logger.debug("[MainScreen] Number key %d pressed", number)
            self["status_bar"].setText(f"Number {number} - Quick jump not implemented yet")
            # TODO: Implement quick jump to items starting with numbers
        
        # ==================== ACTION METHODS ====================
        
        def key_ok(self):
            """Enter directory or play file"""
            logger.debug("[MainScreen] Key OK pressed")
            try:
                pane = self.get_active_pane()
                selection = pane.get_selection()
                
                if not selection:
                    self["status_bar"].setText("No selection")
                    return
                
                path, is_dir, name = selection
                
                logger.debug("[MainScreen] Selection: %s (is_dir: %s)", path, is_dir)
                
                if name == '..':
                    # Go to parent directory
                    parent = os.path.dirname(pane.getCurrentDirectory())
                    if parent and parent != pane.getCurrentDirectory():
                        pane.changeDir(parent)
                        self.update_pane_highlight()
                        self.update_info()
                        self["status_bar"].setText(f"Parent directory: {parent}")
                    else:
                        self["status_bar"].setText("Already at root directory")
                
                elif is_dir:
                    # Change to directory
                    pane.changeDir(path)
                    self.update_pane_highlight()
                    self.update_info()
                    self["status_bar"].setText(f"Entered: {name}")
                
                elif is_media_file(name):
                    # Play media file
                    self["status_bar"].setText(f"Playing: {name}")
                    self.play_file(path)
                
                else:
                    # Cannot open non-media files yet
                    self["status_bar"].setText(f"Cannot open: {name}")
                    self.session.open(MessageBox, 
                                    f"File type not supported:\n{name}",
                                    MessageBox.TYPE_INFO, 
                                    timeout=2)
                    
            except Exception as e:
                logger.error("[MainScreen] key_ok error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
                self.session.open(MessageBox, 
                                f"Error opening:\n{str(e)}",
                                MessageBox.TYPE_ERROR, 
                                timeout=3)
        
        def key_exit(self):
            """Go to parent directory or exit"""
            logger.debug("[MainScreen] Key EXIT pressed")
            try:
                pane = self.get_active_pane()
                current_dir = pane.getCurrentDirectory()
                
                if current_dir == '/':
                    # At root, exit application
                    self["status_bar"].setText("Exiting...")
                    self.exit_application()
                else:
                    # Go to parent directory
                    parent = os.path.dirname(current_dir)
                    pane.changeDir(parent)
                    self.update_pane_highlight()
                    self.update_info()
                    self["status_bar"].setText(f"Back to: {parent}")
                    
            except Exception as e:
                logger.error("[MainScreen] key_exit error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_menu(self):
            """Show context menu"""
            logger.debug("[MainScreen] Key MENU pressed")
            self["status_bar"].setText("Menu - Coming soon!")
            self.session.open(MessageBox, 
                            "Context Menu\n\nComing in next version!", 
                            MessageBox.TYPE_INFO, 
                            timeout=2)
        
        # ==================== COLOR BUTTON METHODS ====================
        
        def key_copy(self):
            """Copy marked files to clipboard"""
            logger.debug("[MainScreen] Key GREEN (Copy) pressed")
            try:
                pane = self.get_active_pane()
                marked = pane.get_marked_files()
                
                if marked:
                    self.clipboard = marked
                    self.clipboard_mode = 'copy'
                    self.update_button_bar()
                    self["status_bar"].setText(f"Copied {len(marked)} files to clipboard")
                    self.session.open(MessageBox, 
                                    f"{len(marked)} files copied to clipboard", 
                                    MessageBox.TYPE_INFO, 
                                    timeout=2)
                else:
                    # Copy current file
                    selection = pane.get_selection()
                    if selection and selection[2] != '..':
                        self.clipboard = [selection[0]]
                        self.clipboard_mode = 'copy'
                        self.update_button_bar()
                        self["status_bar"].setText(f"Copied: {selection[2]}")
                    else:
                        self["status_bar"].setText("No files selected")
                        
            except Exception as e:
                logger.error("[MainScreen] key_copy error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_move(self):
            """Move marked files to clipboard"""
            logger.debug("[MainScreen] Key YELLOW (Move) pressed")
            try:
                pane = self.get_active_pane()
                marked = pane.get_marked_files()
                
                if marked:
                    self.clipboard = marked
                    self.clipboard_mode = 'move'
                    self.update_button_bar()
                    self["status_bar"].setText(f"Ready to move {len(marked)} files")
                    self.session.open(MessageBox, 
                                    f"{len(marked)} files marked for move", 
                                    MessageBox.TYPE_INFO, 
                                    timeout=2)
                else:
                    # If clipboard has items, paste them
                    if self.clipboard:
                        self.paste_files()
                    else:
                        self["status_bar"].setText("No files marked for move")
                        
            except Exception as e:
                logger.error("[MainScreen] key_move error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_delete(self):
            """Delete marked files or current file"""
            logger.debug("[MainScreen] Key RED (Delete) pressed")
            try:
                pane = self.get_active_pane()
                marked = pane.get_marked_files()
                
                if not marked:
                    # Delete current file
                    selection = pane.get_selection()
                    if selection and selection[2] != '..':
                        marked = [selection[0]]
                
                if marked:
                    # Confirm deletion
                    self.session.openWithCallback(
                        self.delete_confirmed,
                        MessageBox,
                        f"Delete {len(marked)} item(s)?\n\nThis action cannot be undone.",
                        MessageBox.TYPE_YESNO
                    )
                    self["status_bar"].setText(f"Confirm delete {len(marked)} items")
                else:
                    self["status_bar"].setText("No files to delete")
                    
            except Exception as e:
                logger.error("[MainScreen] key_delete error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_mark(self):
            """Mark/unmark current file"""
            logger.debug("[MainScreen] Key BLUE (Mark) pressed")
            try:
                pane = self.get_active_pane()
                selection = pane.get_selection()
                
                if selection and selection[2] != '..':
                    pane.mark_file(selection[0])
                    # Move to next item
                    pane.down()
                    self.update_info()
                    
                    # Update status
                    marked_count = len(pane.get_marked_files())
                    self["status_bar"].setText(f"Marked: {selection[2]} ({marked_count} total)")
                else:
                    self["status_bar"].setText("Cannot mark this item")
                    
            except Exception as e:
                logger.error("[MainScreen] key_mark error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        def key_permissions(self):
            """Open permissions dialog"""
            logger.debug("[MainScreen] Key INFO (Permissions) pressed")
            try:
                pane = self.get_active_pane()
                selection = pane.get_selection()
                
                if selection and selection[2] != '..':
                    self.open_permission_dialog(selection[0])
                else:
                    self["status_bar"].setText("Select a file first")
                    self.session.open(MessageBox, 
                                    "Please select a file or directory first", 
                                    MessageBox.TYPE_INFO, 
                                    timeout=2)
                    
            except Exception as e:
                logger.error("[MainScreen] key_permissions error: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
        
        # ==================== OPERATION METHODS ====================
        
        def paste_files(self):
            """Paste files from clipboard"""
            if not self.clipboard:
                self["status_bar"].setText("Clipboard is empty")
                return
            
            logger.info("[MainScreen] Pasting %d files", len(self.clipboard))
            
            dest_dir = self.get_inactive_pane().getCurrentDirectory()
            
            # Create progress dialog
            operation = "Copying" if self.clipboard_mode == 'copy' else "Moving"
            progress_dlg = create_progress_dialog(
                self.session,
                "%s files..." % operation,
                self.file_ops
            )
            
            def do_operation():
                try:
                    if self.clipboard_mode == 'copy':
                        success = self.file_ops.copy(self.clipboard, dest_dir)
                        operation_name = "copied"
                    else:
                        success = self.file_ops.move(self.clipboard, dest_dir)
                        operation_name = "moved"
                    
                    # Refresh panes
                    self["left_pane"].refresh()
                    self["right_pane"].refresh()
                    
                    # Clear clipboard if move
                    if success and self.clipboard_mode == 'move':
                        self.clipboard = []
                        self.clipboard_mode = None
                    
                    # Update UI
                    self.update_button_bar()
                    self.update_info()
                    
                    if success:
                        self["status_bar"].setText(f"Successfully {operation_name} {len(self.clipboard)} files")
                    else:
                        errors = self.file_ops.get_errors()
                        error_msg = errors[0] if errors else "Unknown error"
                        self["status_bar"].setText(f"Operation failed: {error_msg}")
                        
                except Exception as e:
                    logger.error("[MainScreen] Paste operation error: %s", e)
                    self["status_bar"].setText(f"Error: {str(e)}")
            
            # Start operation in thread
            thread = threading.Thread(target=do_operation)
            thread.daemon = True
            thread.start()
            
            # Show progress dialog
            progress_dlg.start()
            self.session.open(progress_dlg)
        
        def delete_confirmed(self, confirmed):
            """Handle delete confirmation"""
            if not confirmed:
                self["status_bar"].setText("Delete cancelled")
                return
            
            marked = self.get_active_pane().get_marked_files()
            if not marked:
                selection = self.get_active_pane().get_selection()
                if selection:
                    marked = [selection[0]]
            
            if not marked:
                self["status_bar"].setText("No files to delete")
                return
            
            use_trash = self.config.get('use_trash', True)
            
            # Create progress dialog
            progress_dlg = create_progress_dialog(
                self.session,
                "Deleting files...",
                self.file_ops
            )
            
            def do_delete():
                try:
                    success = self.file_ops.delete(marked, use_trash=use_trash)
                    
                    # Refresh and clear marks
                    pane = self.get_active_pane()
                    pane.clear_marks()
                    pane.refresh()
                    self.update_info()
                    
                    if success:
                        self["status_bar"].setText(f"Deleted {len(marked)} files")
                    else:
                        errors = self.file_ops.get_errors()
                        error_msg = errors[0] if errors else "Unknown error"
                        self["status_bar"].setText(f"Delete failed: {error_msg}")
                        
                except Exception as e:
                    logger.error("[MainScreen] Delete operation error: %s", e)
                    self["status_bar"].setText(f"Error: {str(e)}")
            
            # Start operation
            thread = threading.Thread(target=do_delete)
            thread.daemon = True
            thread.start()
            
            progress_dlg.start()
            self.session.open(progress_dlg)
        
        # ==================== MEDIA & FILE METHODS ====================
        
        def play_file(self, path):
            """Play media file"""
            logger.info("[MainScreen] Playing media file: %s", path)
            try:
                from Screens.InfoBar import InfoBar
                from ServiceReference import ServiceReference
                
                # Check if InfoBar is available
                if InfoBar.instance:
                    # Create service reference
                    service_ref = ServiceReference(f"4097:0:1:0:0:0:0:0:0:0:{path}")
                    
                    # Play the file
                    InfoBar.instance.playService(service_ref.ref)
                    self["status_bar"].setText("Playing media file...")
                else:
                    # Fallback to MoviePlayer
                    from Screens.InfoBar import MoviePlayer
                    self.session.open(MoviePlayer, path)
                    self["status_bar"].setText("Opened in MoviePlayer")
                    
            except Exception as e:
                logger.error("[MainScreen] Error playing file: %s", e)
                self["status_bar"].setText(f"Cannot play: {str(e)}")
                self.session.open(MessageBox, 
                                f"Cannot play file:\n{str(e)}", 
                                MessageBox.TYPE_ERROR)
        
        def open_file(self, path):
            """Open file with appropriate handler"""
            # TODO: Implement file type handlers
            self["status_bar"].setText("File viewer not implemented yet")
            self.session.open(MessageBox, 
                            f"File viewer for:\n{os.path.basename(path)}\n\nComing soon!", 
                            MessageBox.TYPE_INFO, 
                            timeout=2)
        
        def open_permission_dialog(self, path):
            """Open permission dialog for selected file"""
            try:
                self.session.open(PermissionDialog, path)
                self["status_bar"].setText("Opening permissions editor...")
            except Exception as e:
                logger.error("[MainScreen] Error opening permission dialog: %s", e)
                self["status_bar"].setText(f"Error: {str(e)}")
                self.session.open(MessageBox, 
                                f"Cannot edit permissions:\n{str(e)}", 
                                MessageBox.TYPE_ERROR)
        
        # ==================== PROGRESS CALLBACK ====================
        
        def on_progress_update(self, progress_data):
            """Handle progress updates from file operations"""
            # This is called from worker thread
            # Progress dialog handles the display
            pass
        
        # ==================== EXIT & CLEANUP ====================
        
        def exit_application(self):
            """Exit and save state"""
            logger.info("[MainScreen] Exiting WG File Manager Pro")
            
            # Save paths
            try:
                if self.config.get('save_left_on_exit') == 'yes':
                    left_path = self["left_pane"].getCurrentDirectory()
                    self.config.set('left_path', left_path)
                    logger.debug("[MainScreen] Saved left path: %s", left_path)
                
                if self.config.get('save_right_on_exit') == 'yes':
                    right_path = self["right_pane"].getCurrentDirectory()
                    self.config.set('right_path', right_path)
                    logger.debug("[MainScreen] Saved right path: %s", right_path)
                
                self.config.save()
                logger.info("[MainScreen] Configuration saved")
                
            except Exception as e:
                logger.error("[MainScreen] Error saving config: %s", e)
            
            # Stop timer
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
                logger.debug("[MainScreen] Update timer stopped")
            
            # Clear clipboard
            self.clipboard = []
            self.clipboard_mode = None
            
            # Close
            logger.info("[MainScreen] Closing screen")
            self.close()
        
        # ==================== DEBUG & TEST METHODS ====================
        
        def debug_info(self):
            """Print debug information"""
            print("\n" + "="*60)
            print("WG File Manager Pro - Debug Info")
            print("="*60)
            
            print(f"\nActive pane: {self.active_pane}")
            print(f"Clipboard: {len(self.clipboard)} items ({self.clipboard_mode})")
            
            try:
                left_dir = self["left_pane"].getCurrentDirectory()
                right_dir = self["right_pane"].getCurrentDirectory()
                print(f"\nLeft directory: {left_dir}")
                print(f"Right directory: {right_dir}")
                
                left_selection = self["left_pane"].get_selection()
                right_selection = self["right_pane"].get_selection()
                print(f"\nLeft selection: {left_selection}")
                print(f"Right selection: {right_selection}")
                
                left_marked = len(self["left_pane"].get_marked_files())
                right_marked = len(self["right_pane"].get_marked_files())
                print(f"\nLeft marked: {left_marked} files")
                print(f"Right marked: {right_marked} files")
                
            except Exception as e:
                print(f"\nError getting debug info: {e}")
            
            print("\n" + "="*60)


else:
    # Non-Enigma2 main screen (for testing)
    
    class WGFileManagerMain:
        """Simple test version"""
        
        def __init__(self):
            logger.info("[MainScreen] Test mode initialized")
            print("WG File Manager Pro - Test Mode")
            print("=" * 50)
            print("Enigma2 components not available")
            print("Running in test/debug mode")
            print("=" * 50)
            
            # Create simple test interface
            self.test_navigation()
        
        def test_navigation(self):
            """Test navigation commands"""
            print("\nTest Navigation Commands:")
            print("  [↑] Move up")
            print("  [↓] Move down")
            print("  [←] Switch to left pane")
            print("  [←] Switch to right pane")
            print("  [ENTER] Open/Select")
            print("  [ESC] Back/Exit")
            print("  [F1-F4] Color buttons")
            print("\nNote: This is test mode only")
            print("Install on Enigma2 for full functionality")


# Factory function
def create_main_screen(session=None):
    """Create main screen instance"""
    if ENIGMA2_AVAILABLE and session:
        return WGFileManagerMain(session)
    else:
        return WGFileManagerMain()