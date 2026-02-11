"""
Progress dialog with dual progress bars and operation controls
Shows real-time progress for file operations
"""

from __future__ import absolute_import, print_function
import threading

try:
    from Screens.Screen import Screen
    from Components.Label import Label
    from Components.ProgressBar import ProgressBar
    from Components.ActionMap import ActionMap
    from enigma import eTimer
    ENIGMA2_AVAILABLE = True
except ImportError:
    ENIGMA2_AVAILABLE = False
    Screen = object

from Plugins.Extensions.WGFileManagerPro.utils.formatters import format_size, format_speed, format_time
from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger

logger = get_logger(__name__)


if ENIGMA2_AVAILABLE:
    
    class OperationProgressDialog(Screen):
        """Progress dialog for file operations"""
        
        # Skin definition
        skin = """
            <screen position="center,center" size="800,450" title="Operation in Progress">
                <widget name="title" position="20,20" size="760,40" font="Regular;28" />
                
                <!-- Current file progress -->
                <widget name="current_label" position="20,80" size="760,30" font="Regular;22" />
                <widget name="current_file" position="20,115" size="760,25" font="Regular;20" />
                <widget name="current_progress" position="20,145" size="760,30" />
                <widget name="current_stats" position="20,180" size="760,22" font="Regular;18" />
                
                <!-- Overall progress -->
                <widget name="overall_label" position="20,220" size="760,30" font="Regular;22" />
                <widget name="overall_progress" position="20,255" size="760,30" />
                <widget name="overall_stats" position="20,290" size="760,22" font="Regular;18" />
                
                <!-- Status log -->
                <widget name="log" position="20,330" size="760,60" font="Regular;16" />
                
                <!-- Controls -->
                <widget name="buttons" position="20,400" size="760,30" font="Regular;20" halign="center" />
            </screen>
        """
        
        def __init__(self, session, operation_name="File Operation", file_operation=None):
            """
            Initialize progress dialog
            
            Args:
                session: Enigma2 session
                operation_name: Name of operation
                file_operation: FileOperations instance
            """
            Screen.__init__(self, session)
            
            self.operation_name = operation_name
            self.file_operation = file_operation
            self.paused = False
            self.cancelled = False
            
            # UI components
            self["title"] = Label(operation_name)
            self["current_label"] = Label("Current File:")
            self["current_file"] = Label("Initializing...")
            self["current_progress"] = ProgressBar()
            self["current_stats"] = Label("")
            self["overall_label"] = Label("Overall Progress:")
            self["overall_progress"] = ProgressBar()
            self["overall_stats"] = Label("")
            self["log"] = Label("")
            self["buttons"] = Label("[PAUSE]  [SKIP]  [CANCEL]")
            
            # Setup actions
            self["actions"] = ActionMap(
                ["WGFileManagerActions", "ColorActions"],
                {
                    "yellow": self.toggle_pause,
                    "blue": self.skip_file,
                    "red": self.cancel_operation,
                    "ok": self.toggle_pause,
                    "cancel": self.handle_exit,
                },
                -1
            )
            
            # Update timer
            self.update_timer = eTimer()
            self.update_timer.callback.append(self.update_display)
            
            # Last progress data
            self.last_progress = {}
            
            logger.info("[Progress] Dialog initialized: %s", operation_name)
        
        def start(self):
            """Start progress tracking"""
            # Start update timer (100ms intervals)
            self.update_timer.start(100, False)
            logger.debug("[Progress] Progress tracking started")
        
        def stop(self):
            """Stop progress tracking"""
            if self.update_timer.isActive():
                self.update_timer.stop()
            logger.debug("[Progress] Progress tracking stopped")
        
        def update_progress(self, data):
            """
            Update progress from operation
            
            Args:
                data: Progress data dictionary
            """
            self.last_progress = data
        
        def update_display(self):
            """Update display with latest progress"""
            if not self.last_progress:
                return
            
            try:
                data = self.last_progress
                
                # Current file
                if 'file' in data:
                    self["current_file"].setText(data['file'])
                
                if 'percent' in data:
                    self["current_progress"].setValue(data['percent'])
                
                # Current stats
                stats = []
                if 'copied' in data and 'total' in data:
                    stats.append("%s / %s" % (
                        format_size(data['copied']),
                        format_size(data['total'])
                    ))
                
                if 'speed' in data:
                    stats.append("Speed: %s" % format_speed(data['speed']))
                
                if 'eta' in data:
                    stats.append("ETA: %s" % format_time(data['eta']))
                
                if stats:
                    self["current_stats"].setText("  |  ".join(stats))
                
                # Overall progress
                if 'overall_percent' in data:
                    self["overall_progress"].setValue(data['overall_percent'])
                
                # Overall stats
                overall_stats = []
                if 'completed' in data and 'files_total' in data:
                    overall_stats.append("Files: %d / %d" % (
                        data['completed'],
                        data['files_total']
                    ))
                
                if 'elapsed' in data:
                    overall_stats.append("Elapsed: %s" % format_time(data['elapsed']))
                
                if 'errors' in data and data['errors'] > 0:
                    overall_stats.append("Errors: %d" % data['errors'])
                
                if overall_stats:
                    self["overall_stats"].setText("  |  ".join(overall_stats))
                
                # Check if operation is complete
                if data.get('overall_percent', 0) >= 100:
                    self.operation_complete()
                    
            except Exception as e:
                logger.error("[Progress] Display update error: %s", e)
        
        def toggle_pause(self):
            """Toggle pause state"""
            if not self.file_operation:
                return
            
            self.paused = not self.paused
            
            if self.paused:
                self.file_operation.pause()
                self["buttons"].setText("[RESUME]  [SKIP]  [CANCEL]")
                self["log"].setText("Operation paused")
                logger.debug("[Progress] Operation paused")
            else:
                self.file_operation.resume()
                self["buttons"].setText("[PAUSE]  [SKIP]  [CANCEL]")
                self["log"].setText("Operation resumed")
                logger.debug("[Progress] Operation resumed")
        
        def skip_file(self):
            """Skip current file"""
            # Note: Implement skip functionality in FileOperations if needed
            self["log"].setText("Skip not implemented yet")
            logger.debug("[Progress] Skip requested")
        
        def cancel_operation(self):
            """Cancel operation"""
            if not self.file_operation:
                return
            
            self.file_operation.cancel()
            self.cancelled = True
            self["log"].setText("Cancelling operation...")
            self["buttons"].setText("Please wait...")
            logger.info("[Progress] Operation cancelled by user")
        
        def handle_exit(self):
            """Handle exit button"""
            if self.paused or self.cancelled:
                self.close_dialog()
            else:
                # Ask to cancel
                self.cancel_operation()
        
        def operation_complete(self):
            """Handle operation completion"""
            self.stop()
            
            # Show completion message
            errors = self.last_progress.get('errors', 0)
            if errors > 0:
                self["log"].setText("Completed with %d error(s)" % errors)
            else:
                self["log"].setText("Operation completed successfully!")
            
            self["buttons"].setText("[OK to close]")
            logger.info("[Progress] Operation completed. Errors: %d", errors)
            
            # Auto-close after 2 seconds if no errors
            if errors == 0:
                from enigma import eTimer
                close_timer = eTimer()
                close_timer.callback.append(self.close_dialog)
                close_timer.start(2000, True)  # 2 seconds, single shot
        
        def close_dialog(self):
            """Close the dialog"""
            self.stop()
            self.close(self.cancelled)
        
        def __del__(self):
            """Cleanup"""
            self.stop()


else:
    # Non-Enigma2 progress dialog (simple console version)
    
    class OperationProgressDialog:
        """Simple progress dialog for testing"""
        
        def __init__(self, operation_name="Operation", file_operation=None):
            self.operation_name = operation_name
            self.file_operation = file_operation
            self.paused = False
            self.cancelled = False
            print("\n=== %s ===" % operation_name)
        
        def start(self):
            """Start tracking"""
            pass
        
        def stop(self):
            """Stop tracking"""
            pass
        
        def update_progress(self, data):
            """Update progress"""
            if 'file' in data:
                print("File: %s" % data['file'])
            if 'percent' in data:
                print("Progress: %d%%" % data['percent'])
            if 'overall_percent' in data:
                print("Overall: %d%%" % data['overall_percent'])
        
        def toggle_pause(self):
            """Toggle pause"""
            self.paused = not self.paused
            if self.file_operation:
                if self.paused:
                    self.file_operation.pause()
                else:
                    self.file_operation.resume()
        
        def cancel_operation(self):
            """Cancel"""
            if self.file_operation:
                self.file_operation.cancel()
            self.cancelled = True
        
        def close_dialog(self):
            """Close"""
            print("=== Operation Complete ===\n")


# Factory function
def create_progress_dialog(session, operation_name, file_operation=None):
    """
    Create appropriate progress dialog
    
    Args:
        session: Enigma2 session (or None)
        operation_name: Operation name
        file_operation: FileOperations instance
        
    Returns:
        Progress dialog instance
    """
    if ENIGMA2_AVAILABLE and session:
        return OperationProgressDialog(session, operation_name, file_operation)
    else:
        return OperationProgressDialog(operation_name, file_operation)
