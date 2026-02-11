"""
Configuration management for WG File Manager Pro
Handles all settings, preferences, and persistent storage
"""

from __future__ import absolute_import, print_function
import os
# OR
from Plugins.Extensions.WGFileManagerPro.core.compatibility import ensure_str, ensure_unicode, ConfigParser

try:
    from Components.config import config, ConfigSubsection, ConfigSelection, \
        ConfigYesNo, ConfigText, ConfigInteger, ConfigNumber, configfile
    ENIGMA2_AVAILABLE = True
except ImportError:
    ENIGMA2_AVAILABLE = False
    # Fallback for testing without Enigma2
    class DummyConfig:
        pass
    config = DummyConfig()


class WGFileManagerConfig:
    """Main configuration manager"""
    
    def __init__(self):
        """Initialize configuration"""
        self.config_file = "/etc/enigma2/wg_filemanager.conf"
        self.setup_enigma2_config()
        
    def setup_enigma2_config(self):
        """Setup Enigma2 configuration entries"""
        if not ENIGMA2_AVAILABLE:
            return
            
        if not hasattr(config, 'plugins'):
            config.plugins = ConfigSubsection()
            
        if not hasattr(config.plugins, 'wgfilemanager'):
            config.plugins.wgfilemanager = ConfigSubsection()
        
        cfg = config.plugins.wgfilemanager
        
        # ==================== PATH SETTINGS ====================
        if not hasattr(cfg, 'left_path'):
            cfg.left_path = ConfigText(default="/media/hdd", fixed_size=False)
        if not hasattr(cfg, 'right_path'):
            cfg.right_path = ConfigText(default="/tmp", fixed_size=False)
        if not hasattr(cfg, 'save_left_on_exit'):
            cfg.save_left_on_exit = ConfigSelection(default="yes", choices=[("yes", "Yes"), ("no", "No")])
        if not hasattr(cfg, 'save_right_on_exit'):
            cfg.save_right_on_exit = ConfigSelection(default="yes", choices=[("yes", "Yes"), ("no", "No")])
        if not hasattr(cfg, 'default_left_path'):
            cfg.default_left_path = ConfigText(default="/media/hdd", fixed_size=False)
        if not hasattr(cfg, 'default_right_path'):
            cfg.default_right_path = ConfigText(default="/tmp", fixed_size=False)
        
        # ==================== NAVIGATION SETTINGS ====================
        if not hasattr(cfg, 'enable_wraparound'):
            cfg.enable_wraparound = ConfigYesNo(default=True)
        if not hasattr(cfg, 'scroll_speed'):
            cfg.scroll_speed = ConfigSelection(
                default="normal",
                choices=[("slow", "Slow"), ("normal", "Normal"), ("fast", "Fast")]
            )
        if not hasattr(cfg, 'items_per_page'):
            cfg.items_per_page = ConfigInteger(default=20, limits=(5, 100))
        if not hasattr(cfg, 'confirm_exit'):
            cfg.confirm_exit = ConfigYesNo(default=True)
        if not hasattr(cfg, 'exit_behavior'):
            cfg.exit_behavior = ConfigSelection(
                default="parent",
                choices=[("parent", "Go to parent"), ("exit", "Exit immediately")]
            )
        
        # ==================== VIEW SETTINGS ====================
        if not hasattr(cfg, 'show_hidden_files'):
            cfg.show_hidden_files = ConfigYesNo(default=False)
        if not hasattr(cfg, 'show_file_size'):
            cfg.show_file_size = ConfigYesNo(default=True)
        if not hasattr(cfg, 'show_file_date'):
            cfg.show_file_date = ConfigYesNo(default=False)
        if not hasattr(cfg, 'show_icons'):
            cfg.show_icons = ConfigYesNo(default=True)
        if not hasattr(cfg, 'show_permissions'):
            cfg.show_permissions = ConfigYesNo(default=False)
        if not hasattr(cfg, 'sort_dirs_first'):
            cfg.sort_dirs_first = ConfigYesNo(default=True)
        if not hasattr(cfg, 'sort_case_sensitive'):
            cfg.sort_case_sensitive = ConfigYesNo(default=False)
        if not hasattr(cfg, 'view_mode'):
            cfg.view_mode = ConfigSelection(default="list", choices=[("list", "List"), ("grid", "Grid")])
        if not hasattr(cfg, 'font_size'):
            cfg.font_size = ConfigSelection(
                default="auto",
                choices=[("auto", "Auto"), ("small", "Small"), ("medium", "Medium"), ("large", "Large")]
            )
        
        # ==================== THEME SETTINGS ====================
        if not hasattr(cfg, 'theme'):
            cfg.theme = ConfigSelection(
                default="dark",
                choices=[
                    ("dark", "Dark"),
                    ("light", "Light"),
                    ("blue", "Blue"),
                    ("green", "Green"),
                    ("orange", "Orange"),
                    ("purple", "Purple")
                ]
            )
        if not hasattr(cfg, 'icon_set'):
            cfg.icon_set = ConfigSelection(
                default="modern",
                choices=[
                    ("modern", "Modern"),
                    ("classic", "Classic"),
                    ("minimal", "Minimal"),
                    ("colorful", "Colorful")
                ]
            )
        if not hasattr(cfg, 'highlight_color'):
            cfg.highlight_color = ConfigSelection(
                default="blue",
                choices=[("blue", "Blue"), ("green", "Green"), ("red", "Red"), ("yellow", "Yellow")]
            )
        
        # ==================== OPERATION SETTINGS ====================
        if not hasattr(cfg, 'confirm_delete'):
            cfg.confirm_delete = ConfigYesNo(default=True)
        if not hasattr(cfg, 'confirm_overwrite'):
            cfg.confirm_overwrite = ConfigYesNo(default=True)
        if not hasattr(cfg, 'use_trash'):
            cfg.use_trash = ConfigYesNo(default=True)
        if not hasattr(cfg, 'verify_copy'):
            cfg.verify_copy = ConfigYesNo(default=False)
        if not hasattr(cfg, 'buffer_size'):
            cfg.buffer_size = ConfigInteger(default=64, limits=(4, 1024))  # KB
        if not hasattr(cfg, 'preserve_permissions'):
            cfg.preserve_permissions = ConfigYesNo(default=True)
        if not hasattr(cfg, 'default_file_perms'):
            cfg.default_file_perms = ConfigText(default="644", fixed_size=False)
        if not hasattr(cfg, 'default_dir_perms'):
            cfg.default_dir_perms = ConfigText(default="755", fixed_size=False)
        
        # ==================== NETWORK SETTINGS ====================
        if not hasattr(cfg, 'ftp_timeout'):
            cfg.ftp_timeout = ConfigInteger(default=30, limits=(5, 300))
        if not hasattr(cfg, 'network_buffer'):
            cfg.network_buffer = ConfigInteger(default=32, limits=(4, 256))  # KB
        if not hasattr(cfg, 'enable_ftp'):
            cfg.enable_ftp = ConfigYesNo(default=False)
        if not hasattr(cfg, 'enable_smb'):
            cfg.enable_smb = ConfigYesNo(default=False)
        
        # ==================== MEDIA SETTINGS ====================
        if not hasattr(cfg, 'auto_thumbnails'):
            cfg.auto_thumbnails = ConfigYesNo(default=True)
        if not hasattr(cfg, 'thumbnail_size'):
            cfg.thumbnail_size = ConfigSelection(
                default="medium",
                choices=[("small", "Small"), ("medium", "Medium"), ("large", "Large")]
            )
        if not hasattr(cfg, 'show_metadata'):
            cfg.show_metadata = ConfigYesNo(default=True)
        if not hasattr(cfg, 'auto_play_media'):
            cfg.auto_play_media = ConfigYesNo(default=True)
        if not hasattr(cfg, 'media_player'):
            cfg.media_player = ConfigSelection(
                default="enigma2",
                choices=[("enigma2", "Enigma2 Player"), ("external", "External Player")]
            )
        
        # ==================== ADVANCED SETTINGS ====================
        if not hasattr(cfg, 'debug_mode'):
            cfg.debug_mode = ConfigYesNo(default=False)
        if not hasattr(cfg, 'log_operations'):
            cfg.log_operations = ConfigYesNo(default=True)
        if not hasattr(cfg, 'max_history'):
            cfg.max_history = ConfigInteger(default=50, limits=(10, 500))
        if not hasattr(cfg, 'max_log_size'):
            cfg.max_log_size = ConfigInteger(default=1024, limits=(100, 10240))  # KB
        if not hasattr(cfg, 'enable_animations'):
            cfg.enable_animations = ConfigYesNo(default=True)
        if not hasattr(cfg, 'cache_size'):
            cfg.cache_size = ConfigInteger(default=10, limits=(1, 100))  # MB
        
        logger = get_logger()
        logger.info("[Config] Configuration initialized")
        
    def get(self, key, default=None):
        """
        Get configuration value
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if not ENIGMA2_AVAILABLE:
            return default
            
        try:
            cfg = config.plugins.wgfilemanager
            parts = key.split('.')
            obj = cfg
            for part in parts:
                obj = getattr(obj, part)
            return obj.value if hasattr(obj, 'value') else obj
        except AttributeError:
            # Try to get from file cache
            return self._get_from_file(key, default)
    
    def _get_from_file(self, key, default=None):
        """Get value from config file"""
        try:
            if os.path.exists(self.config_file):
                parser = ConfigParser.ConfigParser()
                parser.read(self.config_file)
                
                if '.' in key:
                    section, option = key.split('.', 1)
                else:
                    section = 'general'
                    option = key
                
                if parser.has_section(section) and parser.has_option(section, option):
                    value = parser.get(section, option)
                    
                    # Try to convert to appropriate type
                    if value.lower() in ('yes', 'true', '1'):
                        return True
                    elif value.lower() in ('no', 'false', '0'):
                        return False
                    elif value.isdigit():
                        return int(value)
                    else:
                        return ensure_unicode(value)
        except:
            pass
        
        return default
    
    def set(self, key, value):
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: New value
        """
        if not ENIGMA2_AVAILABLE:
            return
            
        try:
            cfg = config.plugins.wgfilemanager
            parts = key.split('.')
            obj = cfg
            for part in parts[:-1]:
                obj = getattr(obj, part)
            final_key = parts[-1]
            if hasattr(obj, final_key):
                getattr(obj, final_key).value = value
                getattr(obj, final_key).save()
                
                # Also update file cache
                self._save_to_file(key, value)
        except AttributeError:
            # Save to file only
            self._save_to_file(key, value)
    
    def _save_to_file(self, key, value):
        """Save value to config file"""
        try:
            parser = ConfigParser.ConfigParser()
            if os.path.exists(self.config_file):
                parser.read(self.config_file)
            
            if '.' in key:
                section, option = key.split('.', 1)
            else:
                section = 'general'
                option = key
            
            if not parser.has_section(section):
                parser.add_section(section)
            
            # Convert value to string
            if isinstance(value, bool):
                str_value = 'yes' if value else 'no'
            else:
                str_value = ensure_str(str(value))
            
            parser.set(section, option, str_value)
            
            with open(self.config_file, 'w') as f:
                parser.write(f)
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error saving to file: %s", e)
    
    def save(self):
        """Save all configuration to disk"""
        if ENIGMA2_AVAILABLE:
            configfile.save()
        
        logger = get_logger()
        logger.debug("[Config] Configuration saved")
    
    def reset_to_defaults(self, section=None):
        """
        Reset configuration to defaults
        
        Args:
            section: Specific section to reset (None for all)
        """
        logger = get_logger()
        logger.info("[Config] Resetting configuration to defaults")
        
        if section == 'paths' or section is None:
            self.set('left_path', self.get('default_left_path', '/media/hdd'))
            self.set('right_path', self.get('default_right_path', '/tmp'))
        
        if section == 'view' or section is None:
            self.set('show_hidden_files', False)
            self.set('show_file_size', True)
            self.set('show_icons', True)
            self.set('show_permissions', False)
            self.set('sort_dirs_first', True)
        
        if section == 'operations' or section is None:
            self.set('confirm_delete', True)
            self.set('use_trash', True)
            self.set('preserve_permissions', True)
        
        self.save()
    
    def get_bookmarks(self):
        """
        Get saved bookmarks
        
        Returns:
            list: List of bookmark paths
        """
        bookmarks = []
        try:
            if os.path.exists(self.config_file):
                parser = ConfigParser.ConfigParser()
                parser.read(self.config_file)
                if parser.has_section('bookmarks'):
                    for key, value in parser.items('bookmarks'):
                        bookmarks.append({
                            'id': key,
                            'path': ensure_unicode(value),
                            'name': os.path.basename(ensure_unicode(value))
                        })
        except Exception:
            pass
        return bookmarks
    
    def save_bookmark(self, path, name=None):
        """
        Save a bookmark
        
        Args:
            path: Path to bookmark
            name: Optional bookmark name
        """
        try:
            parser = ConfigParser.ConfigParser()
            if os.path.exists(self.config_file):
                parser.read(self.config_file)
            
            if not parser.has_section('bookmarks'):
                parser.add_section('bookmarks')
            
            if name is None:
                name = os.path.basename(path) or path
            
            # Find next available key
            i = 1
            while parser.has_option('bookmarks', 'bookmark_%d' % i):
                i += 1
            
            parser.set('bookmarks', 'bookmark_%d' % i, ensure_str(path))
            
            with open(self.config_file, 'w') as f:
                parser.write(f)
            
            logger = get_logger()
            logger.info("[Config] Bookmark saved: %s -> %s", name, path)
            
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error saving bookmark: %s", e)
    
    def remove_bookmark(self, path):
        """
        Remove a bookmark
        
        Args:
            path: Path to remove
        """
        try:
            parser = ConfigParser.ConfigParser()
            if os.path.exists(self.config_file):
                parser.read(self.config_file)
            
            if parser.has_section('bookmarks'):
                for key, value in parser.items('bookmarks'):
                    if ensure_unicode(value) == ensure_unicode(path):
                        parser.remove_option('bookmarks', key)
                
                with open(self.config_file, 'w') as f:
                    parser.write(f)
            
            logger = get_logger()
            logger.info("[Config] Bookmark removed: %s", path)
            
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error removing bookmark: %s", e)
    
    def get_recent_paths(self):
        """
        Get recently visited paths
        
        Returns:
            list: List of recent paths
        """
        recent = []
        try:
            if os.path.exists(self.config_file):
                parser = ConfigParser.ConfigParser()
                parser.read(self.config_file)
                if parser.has_section('recent'):
                    items = [(key, value) for key, value in parser.items('recent')]
                    items.sort(reverse=True)  # Most recent first
                    recent = [ensure_unicode(value) for key, value in items[:20]]
        except Exception:
            pass
        return recent
    
    def add_recent_path(self, path):
        """
        Add path to recent history
        
        Args:
            path: Path to add
        """
        try:
            parser = ConfigParser.ConfigParser()
            if os.path.exists(self.config_file):
                parser.read(self.config_file)
            
            if not parser.has_section('recent'):
                parser.add_section('recent')
            
            # Use timestamp as key for sorting
            import time
            key = 'recent_%d' % int(time.time())
            parser.set('recent', key, ensure_str(path))
            
            # Keep only last 20
            items = [(k, v) for k, v in parser.items('recent')]
            if len(items) > 20:
                items.sort()
                for k, v in items[:-20]:
                    parser.remove_option('recent', k)
            
            with open(self.config_file, 'w') as f:
                parser.write(f)
            
            logger = get_logger()
            logger.debug("[Config] Recent path added: %s", path)
            
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error adding recent path: %s", e)
    
    def get_all_settings(self):
        """
        Get all settings as dictionary
        
        Returns:
            dict: All configuration settings
        """
        settings = {}
        
        if ENIGMA2_AVAILABLE:
            try:
                cfg = config.plugins.wgfilemanager
                for key in dir(cfg):
                    if not key.startswith('_'):
                        value = getattr(cfg, key)
                        if hasattr(value, 'value'):
                            settings[key] = value.value
                        else:
                            settings[key] = value
            except:
                pass
        
        return settings
    
    def export_settings(self, filepath):
        """
        Export settings to file
        
        Args:
            filepath: Path to export file
            
        Returns:
            bool: True if successful
        """
        try:
            import json
            settings = self.get_all_settings()
            
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            
            logger = get_logger()
            logger.info("[Config] Settings exported to: %s", filepath)
            return True
            
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error exporting settings: %s", e)
            return False
    
    def import_settings(self, filepath):
        """
        Import settings from file
        
        Args:
            filepath: Path to import file
            
        Returns:
            bool: True if successful
        """
        try:
            import json
            
            with open(filepath, 'r') as f:
                settings = json.load(f)
            
            for key, value in settings.items():
                self.set(key, value)
            
            self.save()
            
            logger = get_logger()
            logger.info("[Config] Settings imported from: %s", filepath)
            return True
            
        except Exception as e:
            logger = get_logger()
            logger.error("[Config] Error importing settings: %s", e)
            return False


# Singleton instance
_config_instance = None

def get_config():
    """Get global config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = WGFileManagerConfig()
    return _config_instance