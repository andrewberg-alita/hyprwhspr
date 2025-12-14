"""
Global shortcuts handler for hyprwhspr
Manages system-wide keyboard shortcuts for dictation control
"""

import sys
import threading
import select
import time
from typing import Callable, Optional, List, Set, Dict, NamedTuple
from pathlib import Path

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes, UInput
except (ImportError, ModuleNotFoundError) as e:
    print("ERROR: python-evdev is not available in this Python environment.", file=sys.stderr)
    print(f"ImportError: {e}", file=sys.stderr)
    print("\nThis is a required dependency. Please install it:", file=sys.stderr)
    print("  pacman -S python-evdev    # system-wide on Arch", file=sys.stderr)
    sys.exit(1)


# Key aliases mapping to evdev KEY_* constants
KEY_ALIASES: dict[str, str] = {
    # Left-side modifiers
    'ctrl': 'KEY_LEFTCTRL', 'control': 'KEY_LEFTCTRL', 'lctrl': 'KEY_LEFTCTRL',
    'alt': 'KEY_LEFTALT', 'lalt': 'KEY_LEFTALT',
    'shift': 'KEY_LEFTSHIFT', 'lshift': 'KEY_LEFTSHIFT',
    'super': 'KEY_LEFTMETA', 'meta': 'KEY_LEFTMETA', 'lsuper': 'KEY_LEFTMETA',
    'win': 'KEY_LEFTMETA', 'windows': 'KEY_LEFTMETA', 'cmd': 'KEY_LEFTMETA',
    
    # Right-side modifiers
    'rctrl': 'KEY_RIGHTCTRL', 'rightctrl': 'KEY_RIGHTCTRL',
    'ralt': 'KEY_RIGHTALT', 'rightalt': 'KEY_RIGHTALT',
    'rshift': 'KEY_RIGHTSHIFT', 'rightshift': 'KEY_RIGHTSHIFT',
    'rsuper': 'KEY_RIGHTMETA', 'rightsuper': 'KEY_RIGHTMETA', 'rmeta': 'KEY_RIGHTMETA',
    
    # Common special keys
    'enter': 'KEY_ENTER', 'return': 'KEY_ENTER',
    'backspace': 'KEY_BACKSPACE', 'bksp': 'KEY_BACKSPACE',
    'tab': 'KEY_TAB',
    'caps': 'KEY_CAPSLOCK', 'capslock': 'KEY_CAPSLOCK',
    'esc': 'KEY_ESC', 'escape': 'KEY_ESC',
    'space': 'KEY_SPACE', 'spacebar': 'KEY_SPACE',
    'delete': 'KEY_DELETE', 'del': 'KEY_DELETE',
    'insert': 'KEY_INSERT', 'ins': 'KEY_INSERT',
    'home': 'KEY_HOME',
    'end': 'KEY_END',
    'pageup': 'KEY_PAGEUP', 'pgup': 'KEY_PAGEUP',
    'pagedown': 'KEY_PAGEDOWN', 'pgdn': 'KEY_PAGEDOWN', 'pgdown': 'KEY_PAGEDOWN',
    
    # Arrow keys
    'up': 'KEY_UP', 'uparrow': 'KEY_UP',
    'down': 'KEY_DOWN', 'downarrow': 'KEY_DOWN',
    'left': 'KEY_LEFT', 'leftarrow': 'KEY_LEFT',
    'right': 'KEY_RIGHT', 'rightarrow': 'KEY_RIGHT',
    
    # Lock keys
    'numlock': 'KEY_NUMLOCK',
    'scrolllock': 'KEY_SCROLLLOCK', 'scroll': 'KEY_SCROLLLOCK',
    
    # Function keys (f1-f24)
    'f1': 'KEY_F1', 'f2': 'KEY_F2', 'f3': 'KEY_F3', 'f4': 'KEY_F4',
    'f5': 'KEY_F5', 'f6': 'KEY_F6', 'f7': 'KEY_F7', 'f8': 'KEY_F8',
    'f9': 'KEY_F9', 'f10': 'KEY_F10', 'f11': 'KEY_F11', 'f12': 'KEY_F12',
    'f13': 'KEY_F13', 'f14': 'KEY_F14', 'f15': 'KEY_F15', 'f16': 'KEY_F16',
    'f17': 'KEY_F17', 'f18': 'KEY_F18', 'f19': 'KEY_F19', 'f20': 'KEY_F20',
    'f21': 'KEY_F21', 'f22': 'KEY_F22', 'f23': 'KEY_F23', 'f24': 'KEY_F24',
    
    # Numpad keys
    'kp0': 'KEY_KP0', 'kp1': 'KEY_KP1', 'kp2': 'KEY_KP2', 'kp3': 'KEY_KP3',
    'kp4': 'KEY_KP4', 'kp5': 'KEY_KP5', 'kp6': 'KEY_KP6', 'kp7': 'KEY_KP7',
    'kp8': 'KEY_KP8', 'kp9': 'KEY_KP9',
    'kpenter': 'KEY_KPENTER', 'kpplus': 'KEY_KPPLUS', 'kpminus': 'KEY_KPMINUS',
    'kpmultiply': 'KEY_KPASTERISK', 'kpdivide': 'KEY_KPSLASH',
    'kpdot': 'KEY_KPDOT', 'kpperiod': 'KEY_KPDOT',
    
    # Media keys
    'mute': 'KEY_MUTE', 'volumemute': 'KEY_MUTE',
    'volumeup': 'KEY_VOLUMEUP', 'volup': 'KEY_VOLUMEUP',
    'volumedown': 'KEY_VOLUMEDOWN', 'voldown': 'KEY_VOLUMEDOWN',
    'play': 'KEY_PLAYPAUSE', 'playpause': 'KEY_PLAYPAUSE',
    'stop': 'KEY_STOPCD', 'mediastop': 'KEY_STOPCD',
    'nextsong': 'KEY_NEXTSONG', 'next': 'KEY_NEXTSONG',
    'previoussong': 'KEY_PREVIOUSSONG', 'prev': 'KEY_PREVIOUSSONG',
    
    # Browser keys (for keyboards with browser control buttons)
    'browser': 'KEY_WWW',
    'browserback': 'KEY_BACK',
    'browserforward': 'KEY_FORWARD',
    'refresh': 'KEY_REFRESH',
    'browsersearch': 'KEY_SEARCH',
    'favorites': 'KEY_BOOKMARKS',
    
    # System keys
    'menu': 'KEY_MENU',
    'print': 'KEY_PRINT', 'printscreen': 'KEY_SYSRQ', 'prtsc': 'KEY_SYSRQ',
    'pause': 'KEY_PAUSE', 'break': 'KEY_PAUSE',
    'sysrq': 'KEY_SYSRQ',

    # Punctuation and symbol keys
    '.': 'KEY_DOT', 'dot': 'KEY_DOT', 'period': 'KEY_DOT',
    ',': 'KEY_COMMA', 'comma': 'KEY_COMMA',
    '/': 'KEY_SLASH', 'slash': 'KEY_SLASH',
    '\\': 'KEY_BACKSLASH', 'backslash': 'KEY_BACKSLASH',
    ';': 'KEY_SEMICOLON', 'semicolon': 'KEY_SEMICOLON',
    "'": 'KEY_APOSTROPHE', 'apostrophe': 'KEY_APOSTROPHE', 'quote': 'KEY_APOSTROPHE',
    '[': 'KEY_LEFTBRACE', 'leftbrace': 'KEY_LEFTBRACE', 'lbrace': 'KEY_LEFTBRACE',
    ']': 'KEY_RIGHTBRACE', 'rightbrace': 'KEY_RIGHTBRACE', 'rbrace': 'KEY_RIGHTBRACE',
    '-': 'KEY_MINUS', 'minus': 'KEY_MINUS', 'dash': 'KEY_MINUS',
    '=': 'KEY_EQUAL', 'equal': 'KEY_EQUAL', 'equals': 'KEY_EQUAL',
    '`': 'KEY_GRAVE', 'grave': 'KEY_GRAVE', 'backtick': 'KEY_GRAVE',

    # Number keys (top row)
    '0': 'KEY_0', '1': 'KEY_1', '2': 'KEY_2', '3': 'KEY_3', '4': 'KEY_4',
    '5': 'KEY_5', '6': 'KEY_6', '7': 'KEY_7', '8': 'KEY_8', '9': 'KEY_9',

    # Letter keys (for completeness - allows lowercase in config)
    'a': 'KEY_A', 'b': 'KEY_B', 'c': 'KEY_C', 'd': 'KEY_D', 'e': 'KEY_E',
    'f': 'KEY_F', 'g': 'KEY_G', 'h': 'KEY_H', 'i': 'KEY_I', 'j': 'KEY_J',
    'k': 'KEY_K', 'l': 'KEY_L', 'm': 'KEY_M', 'n': 'KEY_N', 'o': 'KEY_O',
    'p': 'KEY_P', 'q': 'KEY_Q', 'r': 'KEY_R', 's': 'KEY_S', 't': 'KEY_T',
    'u': 'KEY_U', 'v': 'KEY_V', 'w': 'KEY_W', 'x': 'KEY_X', 'y': 'KEY_Y',
    'z': 'KEY_Z',
}

class Shortcut(NamedTuple):
    id: str
    target_keys: Set[int]
    callback: Callable
    release_callback: Optional[Callable] = None


class GlobalShortcuts:
    """Handles global keyboard shortcuts using evdev for hardware-level capture"""

    def __init__(self, device_path: Optional[str] = None, grab_keys: bool = True):
        self.selected_device_path = device_path
        self.grab_keys = grab_keys

        # Device and event handling
        self.devices = []
        self.device_fds = {}
        self.listener_thread = None
        self.is_running = False
        self.stop_event = threading.Event()

        # Virtual keyboard for re-emitting non-shortcut keys
        self.uinput = None
        self.devices_grabbed = False

        # State tracking
        self.pressed_keys = set()
        self.debounce_time = 0.1  # 100ms debounce
        self.last_trigger_times = {} # Map shortcut ID -> last trigger time
        self.last_release_times = {} # Map shortcut ID -> last release time
        
        # Track active shortcuts (currently pressed combinations)
        self.active_shortcuts = set() # Set of shortcut IDs currently considered "active"

        # Track which keys are currently being suppressed (part of an active shortcut)
        self.suppressed_keys = set()
        
        # Registered shortcuts
        self.shortcuts: List[Shortcut] = []
        
        # All required input keys across all shortcuts
        self.all_required_keys = set()

        # Initialize keyboard devices
        # (Defer this until after shortcuts are added, or call it explicitly)
        
    def add_shortcut(self, key_string: str, callback: Callable, release_callback: Optional[Callable] = None) -> str:
        """Add a new shortcut to listen for. Returns the shortcut ID."""
        target_keys = self._parse_key_combination(key_string)
        if not target_keys:
             print(f"[ERROR] Invalid shortcut string: {key_string}")
             return None

        shortcut_id = f"{key_string}_{len(self.shortcuts)}"
        shortcut = Shortcut(shortcut_id, target_keys, callback, release_callback)
        self.shortcuts.append(shortcut)
        
        # Update set of all keys we care about
        self.all_required_keys.update(target_keys)
        
        return shortcut_id

    def _discover_keyboards(self):
        """Discover and initialize input devices that can emit the configured shortcut"""
        self.devices = []
        self.device_fds = {}
        
        if not self.shortcuts:
            print("[WARN] No shortcuts registered before discovering keyboards")
            return

        try:
            # Find all input devices
            all_device_paths = evdev.list_devices()
            devices = [evdev.InputDevice(path) for path in all_device_paths]
            
            # If a specific device path is selected, only use that device and skip auto-detection
            if self.selected_device_path:
                selected_device = None
                for device in devices:
                    if device.path == self.selected_device_path:
                        selected_device = device
                    else:
                        # Close devices that don't match the selected path
                        device.close()
                
                if selected_device is None:
                    print(f"[WARN] Selected device {self.selected_device_path} not found!")
                    return
                
                devices = [selected_device]
            
            for device in devices:
                # Require EV_KEY events
                capabilities = device.capabilities()
                if ecodes.EV_KEY not in capabilities:
                    device.close()
                    continue
                
                # Check that device can emit ALL keys required for AT LEAST ONE shortcut
                available_keys = set(capabilities[ecodes.EV_KEY])
                
                # Check if device is potentially useful
                # For simplicity, we just check if it has keyboard capabilities basically
                # but ideally we'd check if it covers the keys for at least one shortcut.
                # However, modifier keys might be on one device and letter on another?
                # Probably not common. Let's assume a single device needs to support the content.
                
                can_emit_any_shortcut = False
                for shortcut in self.shortcuts:
                    if shortcut.target_keys.issubset(available_keys):
                        can_emit_any_shortcut = True
                        break
                
                if not can_emit_any_shortcut:
                    # If this device can't fully support ANY configured shortcut, verify if it is missing essential keys
                    # If we explicitly selected it, warn
                    if self.selected_device_path:
                         print(f"[WARN] Selected device '{device.name}' doesn't seem to support all keys for the configured shortcuts")
                    
                    # We might skip it, or include it anyway? Safe to skip if strict.
                    if not self.selected_device_path: 
                        device.close()
                        continue
                
                # Device seems valid - test if we can grab it
                try:
                    device.grab()
                    device.ungrab()
                    
                    self.devices.append(device)
                    self.device_fds[device.fd] = device
                    
                    # If we selected a specific device, we're done
                    if self.selected_device_path:
                        break
                    
                except (OSError, IOError) as e:
                    if self.selected_device_path:
                        print(f"[ERROR] Cannot access selected device '{device.name}' ({device.path}): {e}")
                        device.close()
                        return
                    print(f"[WARN] Cannot access device {device.name}: {e}")
                    device.close()
                        
        except Exception as e:
            print(f"[ERROR] Error discovering devices: {e}")
            import traceback
            traceback.print_exc()
            
        if not self.devices:
            print("[ERROR] No accessible devices found that can emit the configured shortcuts!")
    
    def _parse_key_combination(self, key_string: str) -> Set[int]:
        """Parse a key combination string into a set of evdev key codes"""
        keys = set()
        key_lower = key_string.lower().strip()
        
        # Remove angle brackets if present
        key_lower = key_lower.replace('<', '').replace('>', '')
        
        # Split into parts for modifier + key combinations
        parts = key_lower.split('+')
        
        for part in parts:
            part = part.strip()
            keycode = self._string_to_keycode(part)
            if keycode is not None:
                keys.add(keycode)
            else:
                print(f"Warning: Could not parse key '{part}' in '{key_string}'")
                return None # Fail on invalid key
                
        return keys
    
    def _string_to_keycode(self, key_string: str) -> Optional[int]:
        """Convert a human-friendly key string into an evdev keycode."""
        original = key_string
        key_string = key_string.lower().strip()
        
        # 1. Try alias mapping first, easy names
        if key_string in KEY_ALIASES:
            key_name = KEY_ALIASES[key_string]
        else:
            # 2. Try as direct evdev KEY_* name
            key_name = key_string.upper()
            if not key_name.startswith('KEY_'):
                key_name = f'KEY_{key_name}'
        
        # 3. Look up the keycode in evdev's complete mapping
        code = ecodes.ecodes.get(key_name)

        if code is None:
            # print(f"Warning: Unknown key string '{original}' (resolved to '{key_name}')")
            return None
        
        return code
    
    def _keycode_to_name(self, keycode: int) -> str:
        """Convert evdev keycode to human readable name"""
        try:
            key_name = ecodes.KEY[keycode]
            # Handle case where evdev returns a tuple of multiple event codes
            if isinstance(key_name, tuple):
                key_name = key_name[0]
            return key_name.replace('KEY_', '')
        except KeyError:
            return f"KEY_{keycode}"
    
    def _event_loop(self):
        """Main event loop for processing keyboard events"""
        try:
            while not self.stop_event.is_set():
                if not self.devices:
                    time.sleep(0.1)
                    continue
                    
                # Use select to wait for events from any device
                device_fds = [dev.fd for dev in self.devices]
                ready_fds, _, _ = select.select(device_fds, [], [], 0.1)
                
                for fd in ready_fds:
                    if fd in self.device_fds:
                        device = self.device_fds[fd]
                        try:
                            # device.read() returns a generator, convert to list
                            events = list(device.read())
                            for event in events:
                                self._process_event(event)
                        except (OSError, IOError) as e:
                            # Device disconnected or error
                            print(f"[ERROR] Lost connection to device: {device.name}: {e}")
                            self._remove_device(device)
                            
        except Exception as e:
            print(f"[ERROR] Error in keyboard event loop: {e}")
            import traceback
            traceback.print_exc()
        
    def _remove_device(self, device: InputDevice):
        """Remove a disconnected device from monitoring"""
        try:
            if device in self.devices:
                self.devices.remove(device)
            if device.fd in self.device_fds:
                del self.device_fds[device.fd]
            device.close()
        except:
            pass
    
    # Modifier keys that should never get "stuck" - always pass through releases
    MODIFIER_KEYS = {
        ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL,
        ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT,
        ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT,
        ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA,
    }

    def _process_event(self, event):
        """Process individual keyboard events"""
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            should_suppress = False

            if key_event.keystate == key_event.key_down:
                # Key pressed
                self.pressed_keys.add(event.code)

                # Check if this key completes ANY configured shortcut
                matched_shortcut = False
                for shortcut in self.shortcuts:
                    if event.code in shortcut.target_keys and shortcut.target_keys.issubset(self.pressed_keys):
                        # Calculate extra modifiers for this specific shortcut
                        extra_keys = self.pressed_keys - shortcut.target_keys
                        extra_modifiers = extra_keys & self.MODIFIER_KEYS
                        
                        # Only suppress if this key completes a VALID shortcut (no extra modifiers)
                        if len(extra_modifiers) == 0:
                            # This key completes a shortcut!
                            # Suppress it if it's not a modifier itself (to be safe? usually modifiers aren't the final key but possible)
                            # Actually, we should suppressing the trigger key
                            if event.code not in self.MODIFIER_KEYS:
                                should_suppress = True
                                self.suppressed_keys.add(event.code)
                            matched_shortcut = True
                
                # Now check all combinations to trigger callbacks
                self._check_all_shortcut_combinations()

            elif key_event.keystate == key_event.key_up:
                # Key released
                was_active_map = {sid: (sid in self.active_shortcuts) for sid in [s.id for s in self.shortcuts]}
                
                self.pressed_keys.discard(event.code)

                # If this key was suppressed, suppress its release too
                if event.code in self.suppressed_keys:
                    self.suppressed_keys.discard(event.code)
                    if event.code not in self.MODIFIER_KEYS:
                        should_suppress = True

                self._check_all_combinations_release(was_active_map)

            elif key_event.keystate == 2:  # Key repeat
                # Suppress repeats for suppressed keys
                if event.code in self.suppressed_keys:
                    should_suppress = True

            # Re-emit non-suppressed key events to virtual keyboard
            if self.uinput and self.devices_grabbed and not should_suppress:
                try:
                    self.uinput.write(ecodes.EV_KEY, event.code, event.value)
                    self.uinput.syn()
                except Exception as e:
                    pass
                    # print(f"Warning: Failed to re-emit key: {e}")

        elif self.uinput and self.devices_grabbed:
            # Pass through non-key events
            try:
                self.uinput.write(event.type, event.code, event.value)
            except:
                pass
    
    def _check_all_shortcut_combinations(self):
        """Check status of all shortcuts"""
        current_time = time.time()
        
        for shortcut in self.shortcuts:
            # Check if target keys match
            if not shortcut.target_keys.issubset(self.pressed_keys):
                is_match = False
            else:
                # Check extras
                extra_keys = self.pressed_keys - shortcut.target_keys
                extra_modifiers = extra_keys & self.MODIFIER_KEYS
                is_match = (len(extra_modifiers) == 0)
            
            # Handle activation
            if is_match:
                # Get last trigger for this shortcut
                last_trigger = self.last_trigger_times.get(shortcut.id, 0)
                
                if (shortcut.id not in self.active_shortcuts) and (current_time - last_trigger > self.debounce_time):
                    self.last_trigger_times[shortcut.id] = current_time
                    self.active_shortcuts.add(shortcut.id)
                    self._trigger_callback(shortcut)
            else:
                if shortcut.id in self.active_shortcuts:
                     self.active_shortcuts.remove(shortcut.id)

    def _trigger_callback(self, shortcut: Shortcut):
        """Trigger the callback for a specific shortcut"""
        if shortcut.callback:
            try:
                callback_thread = threading.Thread(target=shortcut.callback, daemon=True)
                callback_thread.start()
            except Exception as e:
                print(f"[ERROR] Error calling shortcut callback: {e}")

    def _check_all_combinations_release(self, was_active_map: Dict[str, bool]):
        """Check releases for all shortcuts"""
        current_time = time.time()
        
        for shortcut in self.shortcuts:
            was_active = was_active_map.get(shortcut.id, False)
            
            # If it was active, and now keys are missing, it's a release event
            # Note: We check if target_keys are NO LONGER matching
            if was_active:
                # Check if it is still valid matches
                still_matches = shortcut.target_keys.issubset(self.pressed_keys)
                if not still_matches:
                    # It was active, now it's not -> Release
                    last_release = self.last_release_times.get(shortcut.id, 0)
                    
                    if current_time - last_release > self.debounce_time:
                        self.last_release_times[shortcut.id] = current_time
                        self._trigger_release_callback(shortcut)

    def _trigger_release_callback(self, shortcut: Shortcut):
        """Trigger the release callback"""
        if shortcut.release_callback:
            try:
                callback_thread = threading.Thread(target=shortcut.release_callback, daemon=True)
                callback_thread.start()
            except Exception as e:
                print(f"[ERROR] Error calling shortcut release callback: {e}")
    
    def start(self) -> bool:
        """Start listening for global shortcuts"""
        if self.is_running:
            return True

        # Rediscover keyboards
        print("Discovering keyboard devices...")
        self._discover_keyboards()

        if not self.devices:
            print("No keyboard devices available")
            return False

        try:
            # Set up key grabbing if enabled
            if self.grab_keys:
                self._setup_key_grabbing()

            self.stop_event.clear()
            self.listener_thread = threading.Thread(target=self._event_loop, daemon=True)
            self.listener_thread.start()
            self.is_running = True

            return True

        except Exception as e:
            print(f"[ERROR] Failed to start global shortcuts: {e}")
            self._cleanup_key_grabbing()
            return False

    def _setup_key_grabbing(self):
        """Set up UInput virtual keyboard and grab physical devices"""
        try:
            self.uinput = UInput(name="hyprwhspr-virtual-keyboard")

            grabbed_count = 0
            for device in self.devices:
                try:
                    device.grab()
                    grabbed_count += 1
                except Exception as e:
                    print(f"[ERROR] Could not grab {device.name}: {e}")

            if grabbed_count == 0:
                print("[ERROR] No devices were grabbed! Shortcuts will not work!")
                
            self.devices_grabbed = True

        except Exception as e:
            print(f"[ERROR] Could not set up key grabbing: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup_key_grabbing()

    def _cleanup_key_grabbing(self):
        """Clean up UInput and ungrab devices"""
        if self.devices_grabbed:
            for device in self.devices:
                try:
                    device.ungrab()
                except:
                    pass
            self.devices_grabbed = False

        if self.uinput:
            try:
                self.uinput.close()
            except:
                pass
            self.uinput = None

    def stop(self):
        """Stop listening for global shortcuts"""
        if not self.is_running:
            return

        try:
            self.stop_event.set()

            if self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=1.0)

            self._cleanup_key_grabbing()

            for device in self.devices[:]:
                self._remove_device(device)

            self.is_running = False
            self.pressed_keys.clear()
            self.suppressed_keys.clear()

        except Exception as e:
            print(f"Error stopping global shortcuts: {e}")
    
    def __del__(self):
        try:
            self.stop()
        except:
            pass

# Utility functions for key handling
def normalize_key_name(key_name: str) -> str:
    """Normalize key names for consistent parsing"""
    return key_name.lower().strip().replace(' ', '')

def _string_to_keycode_standalone(key_string: str) -> Optional[int]:
    """Standalone version of string to keycode conversion"""
    key_string = key_string.lower().strip()
    
    if key_string in KEY_ALIASES:
        key_name = KEY_ALIASES[key_string]
    else:
        key_name = key_string.upper()
        if not key_name.startswith('KEY_'):
            key_name = f'KEY_{key_name}'
    
    code = ecodes.ecodes.get(key_name)
    return code

def _parse_key_combination_standalone(key_string: str) -> Set[int]:
    """Standalone version of key combination parsing"""
    keys = set()
    key_lower = key_string.lower().strip()
    key_lower = key_lower.replace('<', '').replace('>', '')
    parts = key_lower.split('+')
    
    for part in parts:
        part = part.strip()
        keycode = _string_to_keycode_standalone(part)
        if keycode is not None:
            keys.add(keycode)
        
    if not keys:
        keys.add(ecodes.KEY_F12)
        
    return keys

def get_available_keyboards(shortcut: Optional[str] = None) -> List[Dict[str, str]]:
    """Get a list of available input devices."""
    keyboards = []
    
    target_keys = None
    if shortcut:
        target_keys = _parse_key_combination_standalone(shortcut)
    
    try:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            capabilities = device.capabilities()
            if ecodes.EV_KEY not in capabilities:
                device.close()
                continue
            
            available_keys = set(capabilities[ecodes.EV_KEY])
            
            if target_keys and not target_keys.issubset(available_keys):
                device.close()
                continue
            
            try:
                device.grab()
                device.ungrab()
                
                keyboards.append({
                    'name': device.name,
                    'path': device.path,
                    'display_name': f"{device.name} ({device.path})"
                })
            except (OSError, IOError):
                pass
            finally:
                device.close()
                
    except Exception as e:
        print(f"Error getting available keyboards: {e}")
    
    return keyboards

def test_key_accessibility() -> Dict:
    """Test which keyboard devices are accessible"""
    results = {
        'accessible_devices': [],
        'inaccessible_devices': [],
        'total_devices': 0
    }
    
    try:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        results['total_devices'] = len(devices)
        
        for device in devices:
            if ecodes.EV_KEY in device.capabilities():
                try:
                    device.grab()
                    device.ungrab()
                    results['accessible_devices'].append({
                        'name': device.name,
                        'path': device.path
                    })
                except (OSError, IOError):
                    results['inaccessible_devices'].append({
                        'name': device.name,
                        'path': device.path
                    })
                device.close()
    except Exception:
        pass
    
    return results
