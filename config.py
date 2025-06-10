import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.youtube_downloader'
        self.config_file = self.config_dir / 'config.json'
        self.ensure_config_dir()
        self.load_config()
    
    def ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            'theme': 'cosmo',
            'dark_mode': False,
            'default_download_path': str(Path.home() / 'Downloads'),
            'default_format': 'mp4',
            'default_quality': 'best',
            'audio_quality': '192',
            'download_subtitles': False,
            'subtitle_languages': ['en'],
            'max_concurrent_downloads': 3,
            'notification_enabled': True,
            'auto_detect_playlist': True,
            'window_geometry': '800x600',
            'last_used_path': str(Path.home() / 'Downloads')
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self.config = {**default_config, **loaded_config}
            except (json.JSONDecodeError, FileNotFoundError):
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value and save"""
        self.config[key] = value
        self.save_config()
    
    def get_available_themes(self):
        """Get list of available ttkbootstrap themes"""
        return [
            'cosmo', 'flatly', 'journal', 'literal', 'lumen', 'minty',
            'pulse', 'sandstone', 'united', 'yeti', 'morph', 'simplex',
            'cerculean', 'solar', 'superhero', 'darkly', 'cyborg', 'vapor'
        ]
    
    def get_video_qualities(self):
        """Get available video quality options"""
        return {
            'best': 'Best Available',
            'worst': 'Worst Available',
            '2160': '4K (2160p)',
            '1440': '1440p',
            '1080': '1080p',
            '720': '720p',
            '480': '480p',
            '360': '360p',
            '240': '240p'
        }
    
    def get_audio_qualities(self):
        """Get available audio quality options"""
        return {
            '320': '320 kbps',
            '256': '256 kbps',
            '192': '192 kbps',
            '128': '128 kbps',
            '96': '96 kbps',
            '64': '64 kbps'
        }
    
    def get_formats(self):
        """Get available download formats"""
        return {
            'mp4': 'MP4 Video',
            'webm': 'WebM Video',
            'mkv': 'MKV Video',
            'mp3': 'MP3 Audio',
            'aac': 'AAC Audio',
            'ogg': 'OGG Audio',
            'wav': 'WAV Audio',
            'm4a': 'M4A Audio'
        }

# Global config instance
config = Config()
