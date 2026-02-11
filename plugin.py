"""
Enigma2 Plugin Entry Point for WG File Manager Pro
"""

from __future__ import absolute_import, print_function

# Define PluginDescriptor at module level BEFORE any conditionals
PluginDescriptor = None
ENIGMA2_AVAILABLE = False

# Try to import Enigma2 components
try:
    from Plugins.Plugin import PluginDescriptor as RealPluginDescriptor
    from Screens.Screen import Screen
    PluginDescriptor = RealPluginDescriptor
    ENIGMA2_AVAILABLE = True
    print("[WGFileManager] Enigma2 components imported successfully")
except ImportError:
    # Running outside Enigma2 (testing mode)
    ENIGMA2_AVAILABLE = False
    print("[WGFileManager] Running in test mode (no Enigma2)")


def main(session, **kwargs):
    """
    Main entry point for plugin
    
    Args:
        session: Enigma2 session
        **kwargs: Additional arguments
    """
    try:
        # ABSOLUTE IMPORTS FOR ENIGMA2
        from Plugins.Extensions.WGFileManagerPro.ui.main_screen import WGFileManagerMain
        from Plugins.Extensions.WGFileManagerPro.utils.logger import get_logger, set_debug_mode
        from Plugins.Extensions.WGFileManagerPro.core.config import get_config
        
        # Get config and set debug mode
        config = get_config()
        debug_enabled = config.get('debug_mode', False)
        set_debug_mode(debug_enabled)
        
        logger = get_logger()
        logger.info("=" * 60)
        logger.info("Starting WG File Manager Pro")
        logger.info("Debug mode: %s", "ENABLED" if debug_enabled else "DISABLED")
        logger.info("=" * 60)
        
        # Create and open main screen
        session.open(WGFileManagerMain)
        
    except ImportError as e:
        error_msg = f"Import Error: {str(e)}"
        print(f"[WGFileManager] {error_msg}")
        if ENIGMA2_AVAILABLE:
            try:
                from Screens.MessageBox import MessageBox
                session.open(MessageBox, 
                            f"WG File Manager Import Error:\n{str(e)}",
                            MessageBox.TYPE_ERROR)
            except:
                print(f"[WGFileManager] Could not show error dialog: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        print(f"[WGFileManager] Error starting: {error_msg}")
        if ENIGMA2_AVAILABLE:
            try:
                from Screens.MessageBox import MessageBox
                session.open(MessageBox, 
                            f"WG File Manager Error:\n{error_msg}",
                            MessageBox.TYPE_ERROR)
            except:
                print(f"[WGFileManager] Could not show error dialog: {error_msg}")


def autostart(reason, **kwargs):
    """
    Plugin autostart handler
    
    Args:
        reason: Autostart reason
        **kwargs: Additional arguments
    """
    if reason == 0:  # Startup
        print("[WGFileManager] System started")
    elif reason == 1:  # Shutdown
        print("[WGFileManager] System shutting down")


def menu(menuid, **kwargs):
    """
    Menu integration
    
    Args:
        menuid: Menu ID
        **kwargs: Additional arguments
        
    Returns:
        Menu entry or None
    """
    if menuid == "mainmenu":
        return [("WG File Manager Pro", main, "wg_filemanager", 50)]
    return []


def Plugins(**kwargs):
    """
    Plugin descriptor
    
    Returns:
        list: List of plugin descriptors
    """
    # Always return a list, even if empty
    if not ENIGMA2_AVAILABLE:
        print("[WGFileManager] Enigma2 not available - returning empty plugin list")
        return []
    
    if PluginDescriptor is None:
        print("[WGFileManager] PluginDescriptor is None - returning empty plugin list")
        return []
    
    try:
        descriptors = []
        
        # Main menu entry
        descriptors.append(
            PluginDescriptor(
                name="WG File Manager Pro",
                description="Advanced dual-pane file manager with visual progress",
                where=PluginDescriptor.WHERE_PLUGINMENU,
                fnc=main,
                icon="filemanager.png",
                needsRestart=False
            )
        )
        
        # Extensions menu
        descriptors.append(
            PluginDescriptor(
                name="WG File Manager Pro",
                description="Advanced File Manager",
                where=PluginDescriptor.WHERE_EXTENSIONSMENU,
                fnc=main,
                needsRestart=False
            )
        )
        
        # Menu hook
        descriptors.append(
            PluginDescriptor(
                name="WG File Manager Pro",
                where=PluginDescriptor.WHERE_MENU,
                fnc=menu,
                needsRestart=False
            )
        )
        
        print("[WGFileManager] Created %d plugin descriptors" % len(descriptors))
        return descriptors
        
    except Exception as e:
        print("[WGFileManager] Error creating plugin descriptors: %s" % str(e))
        return []


# For testing without Enigma2
if __name__ == "__main__":
    print("=" * 60)
    print("WG File Manager Pro - Plugin Test")
    print("=" * 60)
    print("Enigma2 Available: %s" % ENIGMA2_AVAILABLE)
    print("PluginDescriptor: %s" % ("Available" if PluginDescriptor else "None"))
    
    # Test plugin creation
    plugins = Plugins()
    print("Plugin descriptors created: %d" % len(plugins))
    
    if ENIGMA2_AVAILABLE:
        print("\nThis plugin requires Enigma2 GUI to run.")
        print("Run from plugin menu in Enigma2.")
    else:
        print("\nRunning in test mode...")
        try:
            # For test mode, use relative imports
            from .ui.main_screen import create_main_screen
            screen = create_main_screen()
            print("✓ Test screen created successfully")
        except Exception as e:
            print("✗ Test error: %s" % str(e))
    
    print("=" * 60)