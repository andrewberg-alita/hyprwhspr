"""
Configuration manager for hyprwhspr
Handles loading, saving, and managing application settings
"""

import json
from pathlib import Path
from typing import Any, Dict
import tomllib
import tomli_w


class ConfigManager:
    """Manages application configuration and settings"""
    
    def __init__(self):
        # Default configuration values - minimal set for hyprwhspr
        self.default_config = {
            'primary_shortcut': 'SUPER+ALT+D',
            'push_to_talk': False,  # Enable push-to-talk mode (hold to record, release to stop)
            'model': 'base',
            'threads': 4,           # Thread count for whisper processing
            'language': None,       # Language code for transcription (None = auto-detect, or 'en', 'nl', 'fr', etc.)
            'word_overrides': {},  # Dictionary of word replacements: {"original": "replacement"}
            'whisper_prompt': 'Transcribe with proper capitalization, including sentence beginnings, proper nouns, titles, and standard English capitalization rules.',
            'clipboard_behavior': False,  # Boolean: true = clear clipboard after delay, false = keep (current behavior)
            'clipboard_clear_delay': 5.0,  # Float: seconds to wait before clearing clipboard (only used if clipboard_behavior is true)
            # Values: "super" | "ctrl_shift" | "ctrl"
            # Default "ctrl_shift" for flexible unix-y primitive
            'paste_mode': 'ctrl_shift',
            # Back-compat for older configs (used only if paste_mode is absent):
            'shift_paste': True,  # true = Ctrl+Shift+V, false = Ctrl+V
            # Transcription backend settings
            'transcription_backend': 'pywhispercpp',  # "pywhispercpp" (or "cpu"/"nvidia"/"amd") or "rest-api"
            'rest_endpoint_url': None,         # Full HTTP or HTTPS URL for remote transcription
            'rest_api_provider': None,          # Provider identifier for credential lookup (e.g., 'openai', 'groq', 'custom')
            'rest_api_key': None,              # DEPRECATED: Optional API key for authentication (kept for backward compatibility)
            'rest_headers': {},                # Additional HTTP headers for remote transcription
            'rest_body': {},                   # Additional body fields for remote transcription
            'rest_timeout': 30,                # Request timeout in seconds
            'rest_audio_format': 'wav',        # Audio format for remote transcription

            # Streaming / VAD settings
            'streaming_mode': True,            # Enable VAD-based streaming transcription
            'silence_threshold': 0.02,         # RMS threshold for silence detection
            'silence_duration': 0.6,           # Seconds of silence to trigger transcription
            'min_audio_duration': 0.5,         # Minimum duration to transcribe
        }
        
        # Set up config directory and file path
        self.config_dir = Path.home() / '.config' / 'hyprwhspr'
        self.config_file = self.config_dir / 'config.toml'
        self.json_config_file = self.config_dir / 'config.json'
        
        # Current configuration (starts with defaults)
        self.config = self.default_config.copy()
        
        # Ensure config directory exists
        self._ensure_config_dir()
        
        # Load existing configuration
        self._load_config()
    
    def _ensure_config_dir(self):
        """Ensure the configuration directory exists"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            try:
                from .logger import log_warning
                log_warning(f"Could not create config directory: {e}", "CONFIG")
            except ImportError:
                print(f"Warning: Could not create config directory: {e}")
    
    def _load_config(self):
        """Load configuration from file (TOML preferred, JSON migration supported)"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'rb') as f:
                    loaded_config = tomllib.load(f)
                
                # Merge loaded config with defaults
                self.config.update(loaded_config)
                
                # Normalize 'None' values back if they were empty strings or missing
                # (Optional: depends on how we handle them)
                if self.config.get('language') == "":
                    self.config['language'] = None
                
                # Attempt automatic migration of API key if needed
                self.migrate_api_key_to_credential_manager()
                
                print(f"Configuration loaded from {self.config_file}")
            
            elif self.json_config_file.exists():
                print("Found legacy config.json, migrating to config.toml...")
                with open(self.json_config_file, 'r', encoding='utf-8') as f:
                    try:
                        loaded_json = json.load(f)
                        self.config.update(loaded_json)
                    except json.JSONDecodeError:
                        print("Warning: Could not parse legacy config.json")
                
                # Migrate API key first
                self.migrate_api_key_to_credential_manager()
                
                # Save as TOML (this will create config.toml)
                # We use the initial template if we can to preserve comments, 
                # but since we have custom values, we might have to just dump.
                # Use tomli-w dump for migration to ensure correctness of values.
                self.save_config()
                
                # Rename old json
                legacy_backup = self.json_config_file.with_suffix('.json.bak')
                self.json_config_file.rename(legacy_backup)
                print(f"Migrated config.json to {legacy_backup}")
                
            else:
                print("No existing configuration found, creating default config.toml")
                # Save default configuration with comments
                self._save_initial_config_with_comments()
                
        except Exception as e:
            print(f"Warning: Could not load configuration: {e}")
            print("Using default configuration")
    
    def _save_initial_config_with_comments(self):
        """Save a new config.toml with helpful comments"""
        toml_content = """# hyprwhspr configuration
# =======================

# Primary keyboard shortcut to toggle recording
# Examples: "SUPER+ALT+D", "CTRL+SPACE", "F9"
primary_shortcut = "SUPER+ALT+D"

# Push-to-talk mode
# false: Toggle mode (press to start, press to stop)
# true:  Hold to record, release to stop
push_to_talk = false

# Whisper model to use
# Options: "tiny", "base", "small", "medium", "large", "large-v3"
# Appendix ".en" for English-only models (e.g. "base.en") which are faster.
model = "base"

# Number of threads for Whisper processing
threads = 4

# Language code for transcription
# "" (empty) = Auto-detect
# Examples: "en", "nl", "fr", "de", "es"
language = ""

# Clipboard behavior
# false: Keep transcribed text in clipboard (default)
# true:  Clear clipboard after a delay
clipboard_behavior = false

# Delay in seconds before clearing clipboard (if enabled)
clipboard_clear_delay = 5.0

# Paste mode
# "ctrl_shift": Use Ctrl+Shift+V (Classic terminal style)
# "ctrl":       Use Ctrl+V (Standard GUI style)
# "super":      Use Super+V (Custom)
paste_mode = "ctrl_shift"
shift_paste = true

# Word overrides
# Dictionary of word replacements: {"original" = "replacement"}
[word_overrides]
# "example" = "replacement"

# Transcription backend settings
# "pywhispercpp": Local, fast, CPU optimized (default)
# "cpu", "nvidia", "amd": Specific hardware targets
# "rest-api": Remote server (e.g. cloud or parakeet)
transcription_backend = "pywhispercpp"

# REST API settings (only used if transcription_backend = "rest-api")
rest_endpoint_url = ""
rest_timeout = 30
rest_audio_format = "wav"

[rest_headers]
# "Authorization" = "Bearer ..."

[rest_body]
# "model" = "custom_model"
"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(toml_content)
            print(f"Default configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error: Could not save default configuration: {e}")
            return False

    def save_config(self) -> bool:
        """Save current configuration to file (Warning: strips comments)"""
        try:
            # Prepare config for TOML (remove None values)
            save_data = {}
            for k, v in self.config.items():
                if v is None:
                    # Special cases for keys we want to keep as empty strings
                    if k in ['language', 'rest_endpoint_url']:
                        save_data[k] = ""
                    else:
                        continue # Skip other None values (like rest_api_key)
                else:
                    save_data[k] = v
                 
            with open(self.config_file, 'wb') as f:
                tomli_w.dump(save_data, f)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error: Could not save configuration: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting"""
        return self.config.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set a configuration setting"""
        self.config[key] = value
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings"""
        return self.config.copy()
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = self.default_config.copy()
        print("Configuration reset to defaults")
    
    def get_temp_directory(self) -> Path:
        """Get the temporary directory for audio files"""
        # Use user-writable temp directory instead of system installation directory
        temp_dir = Path.home() / '.local' / 'share' / 'hyprwhspr' / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def get_word_overrides(self) -> Dict[str, str]:
        """Get the word overrides dictionary"""
        return self.config.get('word_overrides', {}).copy()
    
    def add_word_override(self, original: str, replacement: str):
        """Add or update a word override"""
        if 'word_overrides' not in self.config:
            self.config['word_overrides'] = {}
        self.config['word_overrides'][original.lower().strip()] = replacement.strip()
    
    def remove_word_override(self, original: str):
        """Remove a word override"""
        if 'word_overrides' in self.config:
            self.config['word_overrides'].pop(original.lower().strip(), None)
    
    def clear_word_overrides(self):
        """Clear all word overrides"""
        self.config['word_overrides'] = {}
    
    def migrate_api_key_to_credential_manager(self) -> bool:
        """
        Migrate API key from config.json to credential manager.
        
        This function attempts to migrate existing rest_api_key from config
        to the secure credential manager. It tries to identify the provider
        from the endpoint URL or API key prefix, defaulting to 'custom' if
        identification fails.
        
        Returns:
            True if migration was performed, False if no migration was needed
        """
        # Check if migration is needed
        api_key = self.config.get('rest_api_key')
        provider_id = self.config.get('rest_api_provider')
        
        # No migration needed if:
        # - No API key in config, OR
        # - Provider already set (already migrated)
        if not api_key or provider_id:
            return False
        
        # Import here to avoid circular dependencies
        from .credential_manager import save_credential
        from .provider_registry import PROVIDERS
        
        # Try to identify provider from endpoint URL
        endpoint_url = self.config.get('rest_endpoint_url', '')
        identified_provider = None
        
        # Check known provider endpoints
        for provider_id_check, provider_data in PROVIDERS.items():
            if provider_data.get('endpoint') == endpoint_url:
                identified_provider = provider_id_check
                break
        
        # If not identified by endpoint, try API key prefix
        if not identified_provider:
            for provider_id_check, provider_data in PROVIDERS.items():
                prefix = provider_data.get('api_key_prefix')
                if prefix and api_key.startswith(prefix):
                    identified_provider = provider_id_check
                    break
        
        # Default to 'custom' if we can't identify
        if not identified_provider:
            identified_provider = 'custom'
        
        # Save API key to credential manager
        if save_credential(identified_provider, api_key):
            # Update config: set provider, remove API key
            self.config['rest_api_provider'] = identified_provider
            self.config['rest_api_key'] = None  # Set to None instead of deleting for backward compat
            self.save_config()
            
            try:
                from .logger import log_info
                log_info(f"Migrated API key to credential manager (provider: {identified_provider})", "CONFIG")
            except ImportError:
                print(f"Migrated API key to credential manager (provider: {identified_provider})")
            
            return True
        else:
            # Failed to save credential, keep old config
            try:
                from .logger import log_warning
                log_warning("Failed to migrate API key to credential manager", "CONFIG")
            except ImportError:
                print("Warning: Failed to migrate API key to credential manager")
            return False
