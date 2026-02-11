"""
Permission dialog for changing file permissions
"""

from __future__ import absolute_import, print_function
import os
import stat

try:
    from Screens.Screen import Screen
    from Screens.MessageBox import MessageBox
    from Components.Label import Label
    from Components.ActionMap import ActionMap
    from Components.CheckBox import CheckBox
    from enigma import eTimer
    ENIGMA2_AVAILABLE = True
except ImportError:
    ENIGMA2_AVAILABLE = False
    Screen = object

from Plugins.Extensions.WGFileManagerPro.core.file_ops import FileOperations
from Plugins.Extensions.WGFileManagerPro.utils.formatters import format_permissions_with_octal, get_file_owner_info
from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger

logger = get_logger(__name__)


if ENIGMA2_AVAILABLE:
    
    class PermissionDialog(Screen):
        """Dialog for changing file permissions"""
        
        # Skin definition
        skin = """
            <screen position="center,center" size="700,500" title="Change Permissions">
                <widget name="title" position="20,20" size="660,40" font="Regular;26" />
                <widget name="file_info" position="20,70" size="660,30" font="Regular;20" />
                <widget name="current_perms" position="20,110" size="660,30" font="Regular;18" />
                
                <!-- Permission checkboxes -->
                <widget name="label_owner" position="50,160" size="200,25" font="Regular;20" />
                <widget name="owner_read" position="50,190" size="200,30" font="Regular;18" />
                <widget name="owner_write" position="50,230" size="200,30" font="Regular;18" />
                <widget name="owner_execute" position="50,270" size="200,30" font="Regular;18" />
                
                <widget name="label_group" position="250,160" size="200,25" font="Regular;20" />
                <widget name="group_read" position="250,190" size="200,30" font="Regular;18" />
                <widget name="group_write" position="250,230" size="200,30" font="Regular;18" />
                <widget name="group_execute" position="250,270" size="200,30" font="Regular;18" />
                
                <widget name="label_others" position="450,160" size="200,25" font="Regular;20" />
                <widget name="others_read" position="450,190" size="200,30" font="Regular;18" />
                <widget name="others_write" position="450,230" size="200,30" font="Regular;18" />
                <widget name="others_execute" position="450,270" size="200,30" font="Regular;18" />
                
                <!-- Special bits -->
                <widget name="label_special" position="50,320" size="600,25" font="Regular;20" />
                <widget name="setuid" position="50,350" size="200,30" font="Regular;18" />
                <widget name="setgid" position="250,350" size="200,30" font="Regular;18" />
                <widget name="sticky" position="450,350" size="200,30" font="Regular;18" />
                
                <!-- Quick presets -->
                <widget name="label_presets" position="50,400" size="600,25" font="Regular;20" />
                <widget name="preset_755" position="50,430" size="120,35" font="Regular;18" />
                <widget name="preset_644" position="190,430" size="120,35" font="Regular;18" />
                <widget name="preset_777" position="330,430" size="120,35" font="Regular;18" />
                <widget name="preset_600" position="470,430" size="120,35" font="Regular;18" />
                
                <!-- Apply options -->
                <widget name="recursive" position="50,480" size="300,30" font="Regular;18" />
                
                <!-- Buttons -->
                <widget name="buttons" position="20,520" size="660,30" font="Regular;20" halign="center" />
            </screen>
        """
        
        def __init__(self, session, filepath, recursive=False):
            """
            Initialize permission dialog
            
            Args:
                session: Enigma2 session
                filepath: File/directory path
                recursive: Apply recursively to directories
            """
            Screen.__init__(self, session)
            
            self.filepath = filepath
            self.recursive = recursive
            self.file_ops = FileOperations()
            
            # Get current permissions
            self.current_mode = 0
            self.is_dir = False
            try:
                self.current_mode = os.stat(filepath).st_mode
                self.is_dir = os.path.isdir(filepath)
            except:
                pass
            
            # UI components
            self["title"] = Label("Change Permissions")
            self["file_info"] = Label(os.path.basename(filepath))
            self["current_perms"] = Label("")
            
            # Permission labels
            self["label_owner"] = Label("Owner")
            self["label_group"] = Label("Group")
            self["label_others"] = Label("Others")
            
            # Permission checkboxes
            self["owner_read"] = CheckBox("Read", self.current_mode & stat.S_IRUSR)
            self["owner_write"] = CheckBox("Write", self.current_mode & stat.S_IWUSR)
            self["owner_execute"] = CheckBox("Execute", self.current_mode & stat.S_IXUSR)
            
            self["group_read"] = CheckBox("Read", self.current_mode & stat.S_IRGRP)
            self["group_write"] = CheckBox("Write", self.current_mode & stat.S_IWGRP)
            self["group_execute"] = CheckBox("Execute", self.current_mode & stat.S_IXGRP)
            
            self["others_read"] = CheckBox("Read", self.current_mode & stat.S_IROTH)
            self["others_write"] = CheckBox("Write", self.current_mode & stat.S_IWOTH)
            self["others_execute"] = CheckBox("Execute", self.current_mode & stat.S_IXOTH)
            
            # Special bits
            self["label_special"] = Label("Special Bits:")
            self["setuid"] = CheckBox("SetUID", self.current_mode & stat.S_ISUID)
            self["setgid"] = CheckBox("SetGID", self.current_mode & stat.S_ISGID)
            self["sticky"] = CheckBox("Sticky", self.current_mode & stat.S_ISVTX)
            
            # Quick presets
            self["label_presets"] = Label("Quick Presets:")
            self["preset_755"] = Label("755 (rwxr-xr-x)")
            self["preset_644"] = Label("644 (rw-r--r--)")
            self["preset_777"] = Label("777 (rwxrwxrwx)")
            self["preset_600"] = Label("600 (rw-------)")
            
            # Apply options
            self["recursive"] = CheckBox("Apply recursively to directories", recursive)
            
            # Buttons
            self["buttons"] = Label("[OK] Apply  [Cancel]")
            
            # Setup actions
            self["actions"] = ActionMap(
                ["WGFileManagerActions", "ColorActions"],
                {
                    "ok": self.apply_permissions,
                    "cancel": self.close,
                    "green": self.apply_permissions,
                    "red": self.close,
                    "yellow": self.toggle_recursive,
                    "blue": self.apply_preset_755,
                    "1": self.apply_preset_755,
                    "2": self.apply_preset_644,
                    "3": self.apply_preset_777,
                    "4": self.apply_preset_600,
                },
                -1
            )
            
            # Update current permissions display
            self.update_display()
            
            logger.info("[PermissionDialog] Initialized for: %s", filepath)
        
        def update_display(self):
            """Update display with current permissions"""
            try:
                # Get current permissions string
                perm_str = format_permissions_with_octal(self.filepath)
                
                # Get owner info
                user, group, _, _ = get_file_owner_info(self.filepath)
                owner_info = f"{user}:{group}" if user and group else ""
                
                self["current_perms"].setText(f"Current: {perm_str}  Owner: {owner_info}")
            except Exception as e:
                logger.error("[PermissionDialog] Update display error: %s", e)
        
        def calculate_mode(self):
            """Calculate mode from checkboxes"""
            mode = 0
            
            # Owner
            if self["owner_read"].getValue():
                mode |= stat.S_IRUSR
            if self["owner_write"].getValue():
                mode |= stat.S_IWUSR
            if self["owner_execute"].getValue():
                mode |= stat.S_IXUSR
            
            # Group
            if self["group_read"].getValue():
                mode |= stat.S_IRGRP
            if self["group_write"].getValue():
                mode |= stat.S_IWGRP
            if self["group_execute"].getValue():
                mode |= stat.S_IXGRP
            
            # Others
            if self["others_read"].getValue():
                mode |= stat.S_IROTH
            if self["others_write"].getValue():
                mode |= stat.S_IWOTH
            if self["others_execute"].getValue():
                mode |= stat.S_IXOTH
            
            # Special bits
            if self["setuid"].getValue():
                mode |= stat.S_ISUID
            if self["setgid"].getValue():
                mode |= stat.S_ISGID
            if self["sticky"].getValue():
                mode |= stat.S_ISVTX
            
            return mode
        
        def apply_permissions(self):
            """Apply the selected permissions"""
            new_mode = self.calculate_mode()
            recursive = self["recursive"].getValue()
            
            logger.info("[PermissionDialog] Applying mode %o to %s (recursive: %s)", 
                       new_mode, self.filepath, recursive)
            
            # Apply permissions
            success = self.file_ops.set_permissions(self.filepath, new_mode)
            
            if success:
                # Apply recursively if needed
                if recursive and self.is_dir:
                    self.apply_recursive(new_mode)
                
                self.update_display()
                self.session.open(MessageBox, "Permissions applied successfully!", 
                                MessageBox.TYPE_INFO, timeout=2)
            else:
                errors = self.file_ops.get_errors()
                error_msg = "\n".join(errors) if errors else "Unknown error"
                self.session.open(MessageBox, f"Failed to apply permissions:\n{error_msg}", 
                                MessageBox.TYPE_ERROR)
        
        def apply_recursive(self, mode):
            """Apply permissions recursively to directory contents"""
            import threading
            
            def recursive_worker():
                for root, dirs, files in os.walk(self.filepath):
                    for name in dirs + files:
                        path = os.path.join(root, name)
                        try:
                            os.chmod(path, mode)
                        except:
                            pass
            
            # Run in thread to avoid blocking UI
            thread = threading.Thread(target=recursive_worker)
            thread.daemon = True
            thread.start()
        
        def toggle_recursive(self):
            """Toggle recursive checkbox"""
            current = self["recursive"].getValue()
            self["recursive"].setValue(not current)
        
        def apply_preset_755(self):
            """Apply 755 (rwxr-xr-x) preset"""
            self.apply_preset(0o755, "755 (rwxr-xr-x)")
        
        def apply_preset_644(self):
            """Apply 644 (rw-r--r--) preset"""
            self.apply_preset(0o644, "644 (rw-r--r--)")
        
        def apply_preset_777(self):
            """Apply 777 (rwxrwxrwx) preset"""
            self.apply_preset(0o777, "777 (rwxrwxrwx)")
        
        def apply_preset_600(self):
            """Apply 600 (rw-------) preset"""
            self.apply_preset(0o600, "600 (rw-------)")
        
        def apply_preset(self, mode, preset_name):
            """Apply a permission preset"""
            logger.info("[PermissionDialog] Applying preset: %s", preset_name)
            
            # Update checkboxes
            self.update_checkboxes_from_mode(mode)
            
            # Show confirmation
            self.session.open(MessageBox, f"Preset '{preset_name}' loaded", 
                            MessageBox.TYPE_INFO, timeout=1)
        
        def update_checkboxes_from_mode(self, mode):
            """Update checkboxes from numeric mode"""
            # Owner
            self["owner_read"].setValue(bool(mode & stat.S_IRUSR))
            self["owner_write"].setValue(bool(mode & stat.S_IWUSR))
            self["owner_execute"].setValue(bool(mode & stat.S_IXUSR))
            
            # Group
            self["group_read"].setValue(bool(mode & stat.S_IRGRP))
            self["group_write"].setValue(bool(mode & stat.S_IWGRP))
            self["group_execute"].setValue(bool(mode & stat.S_IXGRP))
            
            # Others
            self["others_read"].setValue(bool(mode & stat.S_IROTH))
            self["others_write"].setValue(bool(mode & stat.S_IWOTH))
            self["others_execute"].setValue(bool(mode & stat.S_IXOTH))
            
            # Special bits
            self["setuid"].setValue(bool(mode & stat.S_ISUID))
            self["setgid"].setValue(bool(mode & stat.S_ISGID))
            self["sticky"].setValue(bool(mode & stat.S_ISVTX))
        
        def close(self):
            """Close dialog"""
            self.close(None)


else:
    # Non-Enigma2 permission dialog (simple console version)
    
    class PermissionDialog:
        """Simple permission dialog for testing"""
        
        def __init__(self, filepath, recursive=False):
            self.filepath = filepath
            self.recursive = recursive
            print(f"\n=== Permission Editor ===")
            print(f"File: {filepath}")
            
            try:
                import stat
                mode = os.stat(filepath).st_mode
                print(f"Current: {oct(mode)[-3:]} ({stat.filemode(mode)})")
            except:
                print("Current: Unable to read permissions")
        
        def show(self):
            """Show dialog"""
            print("\n1. 755 (rwxr-xr-x)")
            print("2. 644 (rw-r--r--)")
            print("3. 777 (rwxrwxrwx)")
            print("4. 600 (rw-------)")
            print("5. Custom")
            print("0. Cancel")
            
            choice = input("\nSelect: ")
            return choice