import sys
import os
import time
import math
import json
import subprocess
import threading
import warnings

# Redirect stderr at OS level to suppress libpng warnings from C library
if os.name == 'nt':  # Windows
    import msvcrt
    import ctypes
    # Redirect stderr file descriptor to NUL
    if sys.stderr is not None:
        sys.stderr.flush()
    newstderr = os.open(os.devnull, os.O_WRONLY)
    os.dup2(newstderr, 2)
    os.close(newstderr)
else:  # Unix/Linux/Mac
    sys.stderr = open(os.devnull, 'w')

# Suppress Python warnings
warnings.filterwarnings('ignore')

# Initialize pygame and suppress prompts
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_AUDIODRIVER'] = 'directsound'  # Suppress audio warnings

import pygame

from unzip import read_osz_file
from osu_to_level import create_level_json

try:
    import requests
    from auto_updater import AutoUpdater
    AUTO_UPDATE_AVAILABLE = True
except ImportError:
    AUTO_UPDATE_AVAILABLE = False
    print("Auto-update not available: requests library not installed")

__version__ = "0.7.2"

# Settings management
class Settings:
    """Manages game settings with local storage"""
    
    DEFAULT_SETTINGS = {
        'music_volume': 0.7,
        'hitsound_volume': 0.3,
        'hitsounds_enabled': True,
        'scroll_speed': 75,
        'fade_effects': True,
        'autoplay_enabled': False,  # Debug feature - toggle with Ctrl+P
        'keybinds': {
            # Red keys (WASD by default)
            'red_top': pygame.K_w,
            'red_right': pygame.K_d,
            'red_bottom': pygame.K_s,
            'red_left': pygame.K_a,
            # Blue keys (Arrows by default)
            'blue_top': pygame.K_UP,
            'blue_right': pygame.K_RIGHT,
            'blue_bottom': pygame.K_DOWN,
            'blue_left': pygame.K_LEFT
        }
    }
    
    def __init__(self):
        self.settings_file = 'toa_settings.json'
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file or create default"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    # Ensure nested dicts are merged
                    if 'keybinds' in loaded:
                        settings['keybinds'] = {**self.DEFAULT_SETTINGS['keybinds'], **loaded['keybinds']}
                    if 'mouse_binds' in loaded:
                        settings['mouse_binds'] = {**self.DEFAULT_SETTINGS['mouse_binds'], **loaded['mouse_binds']}
                    return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value and save"""
        self.settings[key] = value
        self.save_settings()

# Global settings instance
game_settings = Settings()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # When running as exe, use the hidden .toa folder in exe directory
        if getattr(sys, 'frozen', False):
            # Running as exe - use .toa hidden folder in exe directory
            base_path = os.path.join(os.path.dirname(sys.executable), '.toa')
        else:
            # Running as script - use current directory
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def initialize_levels_from_osz():
    """Initialize levels and beatmaps from .osz files if they don't exist"""
    beatmaps_dir = resource_path('beatmaps')
    levels_dir = resource_path('levels')
    osz_dir = resource_path('assets/osz')
    
    # Check if levels and beatmaps exist and have content
    needs_init = False
    try:
        if not os.path.exists(levels_dir) or not os.listdir(levels_dir):
            needs_init = True
    except:
        needs_init = True
    
    try:
        if not os.path.exists(beatmaps_dir) or not os.listdir(beatmaps_dir):
            needs_init = True
    except:
        needs_init = True
    
    if not needs_init:
        return  # Already initialized
    
    print("\n" + "="*60)
    print("INITIALIZING GAME DATA")
    print("Extracting beatmaps and generating levels from .osz files...")
    print("This only happens once!")
    print("="*60 + "\n")
    
    # Create directories
    os.makedirs(beatmaps_dir, exist_ok=True)
    os.makedirs(levels_dir, exist_ok=True)
    
    # Check if osz directory exists
    if not os.path.exists(osz_dir):
        print(f"Warning: OSZ directory not found: {osz_dir}")
        return
    
    # Get all .osz files
    osz_files = [f for f in os.listdir(osz_dir) if f.endswith('.osz')]
    
    if not osz_files:
        print(f"Warning: No .osz files found in {osz_dir}")
        return
    
    print(f"Found {len(osz_files)} beatmap(s) to process\n")
    
    from unzip import read_osz_file
    from osu_to_level import create_level_json
    
    def sanitize_filename(name):
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()
    
    def get_difficulty_name(osu_file_path):
        try:
            with open(osu_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
        except:
            pass
        basename = os.path.basename(osu_file_path)
        if '[' in basename and ']' in basename:
            start = basename.rfind('[')
            end = basename.rfind(']')
            if start < end:
                return basename[start+1:end]
        return "Unknown"
    
    # Process each .osz file
    for idx, osz_file in enumerate(osz_files, 1):
        print(f"[{idx}/{len(osz_files)}] Processing: {osz_file}")
        
        osz_path = os.path.join(osz_dir, osz_file)
        extract_name = sanitize_filename(os.path.splitext(osz_file)[0])
        extract_dir = os.path.join(beatmaps_dir, extract_name)
        
        try:
            # Extract .osz file
            osu_files = read_osz_file(osz_path, extract_dir)
            
            if not osu_files:
                print(f"  ✗ No .osu files found")
                continue
            
            # Process each difficulty
            for osu_file in osu_files:
                difficulty = get_difficulty_name(osu_file)
                difficulty_safe = sanitize_filename(difficulty)
                
                if len(osu_files) == 1:
                    output_json = os.path.join(levels_dir, f"{extract_name}.json")
                else:
                    output_json = os.path.join(levels_dir, f"{extract_name}_{difficulty_safe}.json")
                
                if not os.path.exists(output_json):
                    create_level_json(osu_file, output_json, seed=42)
                    print(f"  ✓ Created: {os.path.basename(output_json)}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    print("\n" + "="*60)
    print("Initialization complete!")
    print("="*60 + "\n")

def process_osz_to_level(osz_path, extract_name, output_json, seed=42):
    """
    Process an .osz file: extract it, find the .osu file, and generate a level JSON.

    Args:
        osz_path: Path to the .osz file
        extract_name: Name for the extraction directory (will be beatmaps/{name})
        output_json: Filename for the output JSON file
        seed: Random seed for level generation

    Returns:
        Path to the generated JSON file
    """
    # Create extraction directory path
    extract_dir = f"beatmaps/{extract_name}"

    # Extract the .osz file
    print(f"\n{'='*60}")
    print(f"Processing: {osz_path}")
    print(f"{'='*60}\n")

    osu_files = read_osz_file(osz_path, extract_dir)

    if not osu_files:
        print("Error: No .osu files found in the archive!")
        return None

    # If multiple .osu files, list them and let user choose
    if len(osu_files) > 1:
        print(f"\nFound {len(osu_files)} difficulties:")
        for i, f in enumerate(osu_files):
            print(f"  [{i+1}] {os.path.basename(f)}")

        while True:
            try:
                choice = input(f"\nChoose difficulty [1-{len(osu_files)}]: ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(osu_files):
                    osu_file = osu_files[choice_idx]
                    print(f"Selected: {os.path.basename(osu_file)}\n")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(osu_files)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        osu_file = osu_files[0]
        print(f"\nUsing beatmap: {os.path.basename(osu_file)}\n")

    # Generate level JSON
    create_level_json(osu_file, output_json, seed=seed)

    print(f"\n{'='*60}")
    print(f"Successfully created: {output_json}")
    print(f"{'='*60}\n")

    return output_json, extract_dir

def fade_out(screen, duration=0.3):
    """Fade out the current screen to black"""
    if not game_settings.get('fade_effects', True):
        screen.fill((0, 0, 0))
        pygame.display.flip()
        return
        
    clock = pygame.time.Clock()
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))

    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        alpha = int(255 * (elapsed / duration))
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    # Ensure fully black at the end
    fade_surface.set_alpha(255)
    screen.blit(fade_surface, (0, 0))
    pygame.display.flip()

def fade_in(screen, content_func, duration=0.3):
    """Fade in from black to the current screen

    Args:
        screen: pygame display surface
        content_func: Function that draws the content (takes screen as argument)
        duration: Duration of fade in seconds
    """
    if not game_settings.get('fade_effects', True):
        content_func(screen)
        pygame.display.flip()
        return
        
    clock = pygame.time.Clock()
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))

    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        alpha = int(255 * (1 - elapsed / duration))

        # Draw the content
        content_func(screen)

        # Draw fading black overlay
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

def show_loading_screen():
    """Show loading screen, check for updates, and preload all assets"""
    pygame.init()
    try:
        pygame.mixer.init(buffer=256)  # Lower buffer for reduced audio latency
    except Exception as e:
        print(f"Warning: Could not set low-latency audio buffer: {e}")
    pygame.mixer.set_num_channels(64)  # Increase channels for rapid hitsounds

    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    # Set window icon based on dark mode (Windows/macOS)
    icon_file = "assets/icon_black.png"
    try:
        fallback = False
        if sys.platform == "win32":
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize")
                apps_use_light_theme, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                if apps_use_light_theme == 0:
                    icon_file = "assets/icon_white.png"
            except Exception:
                icon_file = "assets/icon.png"
                fallback = True
        elif sys.platform == "darwin":
            import subprocess
            try:
                result = subprocess.run([
                    "defaults", "read", "-g", "AppleInterfaceStyle"
                ], capture_output=True, text=True)
                if result.returncode == 0 and "Dark" in result.stdout:
                    icon_file = "assets/icon_white.png"
                elif result.returncode != 0:
                    icon_file = "assets/icon.png"
                    fallback = True
            except Exception:
                icon_file = "assets/icon.png"
                fallback = True
        icon_surface = pygame.image.load(resource_path(icon_file))
        pygame.display.set_icon(icon_surface)
    except Exception as e:
        print(f"Warning: Could not set window icon: {e}")
    pygame.display.set_caption(f"TOA - Loading")
    pygame.mouse.set_visible(True)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 60)
    font_status = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 30)
    font_small = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 24)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)

    # Start with black screen
    screen.fill(BLACK)
    pygame.display.flip()

    # Function to update loading screen with progress
    def update_loading_screen(status_msg, progress=None):
        screen.fill(BLACK)
        title_text = font_title.render("TOA", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        screen.blit(title_text, title_rect)

        status_text = font_status.render(status_msg, True, WHITE)
        status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
        screen.blit(status_text, status_rect)
        
        if progress is not None:
            # Draw progress bar with better styling
            bar_width = 600
            bar_height = 30
            bar_x = (window_width - bar_width) // 2
            bar_y = window_height // 2 + 100
            
            # Shadow/glow effect
            glow_surface = pygame.Surface((bar_width + 20, bar_height + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (0, 0, 0, 60), (0, 0, bar_width + 20, bar_height + 20), border_radius=20)
            screen.blit(glow_surface, (bar_x - 10, bar_y - 10))
            
            # Background (rounded)
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=15)
            
            # Progress (rounded)
            if progress > 0:
                progress_width = max(30, int(bar_width * progress))  # Min width for rounded corners
                pygame.draw.rect(screen, GREEN, (bar_x, bar_y, progress_width, bar_height), border_radius=15)
            
            # Border (rounded)
            pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=15)
            
            # Percentage text
            percent_text = font_small.render(f"{int(progress * 100)}%", True, WHITE)
            percent_rect = percent_text.get_rect(center=(window_width // 2, bar_y + bar_height + 30))
            screen.blit(percent_text, percent_rect)
        
        pygame.display.flip()
        clock.tick(60)

    # Fade in the loading screen
    fade_surface = pygame.Surface((window_width, window_height))
    fade_surface.fill((0, 0, 0))
    if game_settings.get('fade_effects', True):
        for alpha in range(255, 0, -25):
            screen.fill(BLACK)
            title_text = font_title.render("TOA", True, WHITE)
            title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
            screen.blit(title_text, title_rect)

            status_text = font_status.render("Loading...", True, WHITE)
            status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
            screen.blit(status_text, status_rect)

            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            clock.tick(60)
    
    # Preload all songpacks and convert levels
    update_loading_screen("Scanning song packs...")
    
    from songpack_loader import scan_and_load_songpacks, convert_level_to_json
    packs = scan_and_load_songpacks()
    
    # Cache for level metadata
    level_metadata_cache = {}
    
    if packs:
        total_levels = sum(len(pack['levels']) for pack in packs)
        converted_count = 0
        
        for pack in packs:
            pack_name = pack['pack_name']
            for level_info in pack['levels']:
                # Check if already converted
                import re
                safe_name = re.sub(r'[^\w\s-]', '', level_info['name']).strip().replace(' ', '_')
                existing_jsons = []
                if os.path.exists('levels'):
                    for file in os.listdir('levels'):
                        if file.startswith(safe_name) and file.endswith('.json'):
                            existing_jsons.append(os.path.join('levels', file))
                
                # Convert if not already done
                if not existing_jsons:
                    progress = converted_count / total_levels if total_levels > 0 else 0
                    update_loading_screen(f"Loading {pack_name}: {level_info['name']}", progress)
                    try:
                        created_jsons = convert_level_to_json(level_info)
                        existing_jsons.extend(created_jsons)
                    except Exception as e:
                        print(f"Error converting {level_info['name']}: {e}")
                
                # Cache metadata for all JSONs
                for json_path in existing_jsons:
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            meta = data.get('meta', {})
                            level_notes = data.get('level', [])
                            
                            # Calculate NPS range
                            notes_by_second = {}
                            for note in level_notes:
                                second = int(note.get('t', 0))
                                notes_by_second[second] = notes_by_second.get(second, 0) + 1
                            nps_min = min(notes_by_second.values()) if notes_by_second else None
                            nps_max = max(notes_by_second.values()) if notes_by_second else None
                            
                            # Store lightweight metadata
                            level_metadata_cache[json_path] = {
                                'title': meta.get('title', 'Unknown'),
                                'version': meta.get('version', 'Unknown'),
                                'artist': meta.get('artist', 'Unknown'),
                                'creator': meta.get('creator', 'Unknown'),
                                'note_count': len(level_notes),
                                'bpm_min': meta.get('bpm_min'),
                                'bpm_max': meta.get('bpm_max'),
                                'background_file': meta.get('background_file'),
                                'length': meta.get('length'),
                                'nps_min': nps_min,
                                'nps_max': nps_max
                            }
                    except Exception as e:
                        print(f"Error caching metadata for {json_path}: {e}")
                
                converted_count += 1
        
        update_loading_screen("Loading complete!", 1.0)
        pygame.time.wait(500)  # Brief pause to show completion

    # Verify file integrity (protect against tampering) with visual feedback
    if AUTO_UPDATE_AVAILABLE and getattr(sys, 'frozen', False):
        update_loading_screen("Checking for updates...")
        try:
            # Load update config
            config_path = os.path.join('.toa', 'update_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f).get('auto_update', {})
            
            updater = AutoUpdater(
                config.get('github_username', ''),
                config.get('repository_name', ''),
                config.get('branch', 'main')
            )
            
            # Only verify if not first run
            if not updater.is_first_run():
                code_files = ['main.py', 'auto_updater.py', 'launcher.py', 'songpack_loader.py', 'songpack_ui.py']
                corrupted_files = []
                
                for i, code_file in enumerate(code_files):
                    # Update screen with progress
                    screen.fill(BLACK)
                    title_text = font_title.render("TOA", True, WHITE)
                    title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
                    screen.blit(title_text, title_rect)
                    
                    status_text = font_status.render("Verifying game files...", True, WHITE)
                    status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
                    screen.blit(status_text, status_rect)
                    
                    progress_text = font_small.render(f"({i+1}/{len(code_files)}) {code_file}", True, BLUE)
                    progress_rect = progress_text.get_rect(center=(window_width // 2, window_height // 2 + 60))
                    screen.blit(progress_text, progress_rect)
                    
                    pygame.display.flip()
                    
                    # Verify file
                    if not updater.verify_file_integrity(code_file):
                        corrupted_files.append(code_file)
                
                # Auto-repair if needed
                if corrupted_files:
                    for i, file in enumerate(corrupted_files):
                        screen.fill(BLACK)
                        title_text = font_title.render("TOA TESTING", True, WHITE)
                        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
                        screen.blit(title_text, title_rect)
                        
                        status_text = font_status.render("Repairing files...", True, WHITE)
                        status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
                        screen.blit(status_text, status_rect)
                        
                        progress_text = font_small.render(f"({i+1}/{len(corrupted_files)}) {file}", True, GREEN)
                        progress_rect = progress_text.get_rect(center=(window_width // 2, window_height // 2 + 60))
                        screen.blit(progress_text, progress_rect)
                        
                        pygame.display.flip()
                        
                        updater.repair_file(file)
                    
                    # Show completion
                    screen.fill(BLACK)
                    title_text = font_title.render("TOA TESTING", True, WHITE)
                    title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
                    screen.blit(title_text, title_rect)
                    
                    status_text = font_status.render("Files restored!", True, GREEN)
                    status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
                    screen.blit(status_text, status_rect)
                    
                    pygame.display.flip()
                    pygame.time.wait(1000)
        except Exception as e:
            print(f"Verification error (non-critical): {e}")

    # Launcher already handles updates, so skip redundant check in main.py

    # No longer pre-loading OSU levels - song packs are loaded on demand

    # Show complete message briefly
    screen.fill(BLACK)
    title_text = font_title.render("TOA", True, WHITE)
    title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
    screen.blit(title_text, title_rect)

    status_text = font_status.render("Ready!", True, WHITE)
    status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
    screen.blit(status_text, status_rect)

    pygame.display.flip()
    time.sleep(0.3)

    # Fade out loading screen
    if game_settings.get('fade_effects', True):
        fade_out(screen, duration=0.5)

    # Keep screen black for transition
    screen.fill((0, 0, 0))
    pygame.display.flip()

    return level_metadata_cache

def show_main_menu(fade_in_start=False):
    """
    Show main menu with options for browsing levels or song packs.
    Returns: 'LEVELS' or 'SONGPACKS' or None/QUIT
    """
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption("TOA - Main Menu")
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    font_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 60)
    font_option = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 40)
    font_hint = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 20)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (150, 150, 150)
    GREEN = (112, 255, 148)
    
    # Menu options
    options = [
        ("Browse Levels", "LEVELS"),
        ("Song Packs", "SONGPACKS")
    ]
    
    hovered_index = None
    selected = None
    
    # Fade in effect
    fade_alpha = 0 if fade_in_start else 255
    fade_surface = pygame.Surface((window_width, window_height))
    fade_surface.fill(BLACK)
    
    while selected is None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    return "LEVELS"
                elif event.key == pygame.K_2 or event.key == pygame.K_KP2:
                    return "SONGPACKS"
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hovered_index is not None:
                    selected = options[hovered_index][1]
        
        # Draw
        screen.fill((0, 0, 0))  # Black background like level selector
        
        # Title
        title_text = font_title.render("TOA", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, 150))
        screen.blit(title_text, title_rect)
        
        # Options
        hovered_index = None
        start_y = 300
        option_spacing = 100
        
        for idx, (label, value) in enumerate(options):
            option_y = start_y + idx * option_spacing
            
            # Check hover
            option_text = font_option.render(label, True, WHITE)
            option_rect = option_text.get_rect(center=(window_width // 2, option_y))
            
            if option_rect.collidepoint(mouse_pos):
                hovered_index = idx
                # Draw hover background like level selector
                hover_rect = pygame.Rect(option_rect.x - 20, option_rect.y - 10, 
                                       option_rect.width + 40, option_rect.height + 20)
                pygame.draw.rect(screen, (40, 40, 40), hover_rect, border_radius=5)
                pygame.draw.rect(screen, GRAY, hover_rect, 2, border_radius=5)
                # Draw selection indicator
                indicator = font_option.render(">", True, GREEN)
                screen.blit(indicator, (option_rect.left - 50, option_rect.top))
            
            screen.blit(option_text, option_rect)
        
        # Hints
        hint_text = font_hint.render("ESC: Exit  |  1: Browse Levels  |  2: Song Packs", True, GRAY)
        hint_rect = hint_text.get_rect(center=(window_width // 2, window_height - 50))
        screen.blit(hint_text, hint_rect)
        
        # Fade in
        if fade_in_start and fade_alpha > 0:
            fade_alpha = max(0, fade_alpha - 10)
            fade_surface.set_alpha(fade_alpha)
            screen.blit(fade_surface, (0, 0))
        
        pygame.display.flip()
        clock.tick(60)
    
    return selected

def show_level_select_popup(fade_in_start=False, preloaded_metadata=None):
    """Show popup window to select a level

    Args:
        fade_in_start: If True, fade in from black at the start
        preloaded_metadata: Pre-loaded level metadata from loading screen
    """
    levels_dir = "levels"  # Define this first as it's used later

    # Use preloaded metadata if available, otherwise load now
    if preloaded_metadata is not None:
        level_metadata = preloaded_metadata
    else:
        # Fallback: Load metadata now (shouldn't happen with loading screen)
        pygame.init()
        pygame.mixer.set_num_channels(64)  # Increase channels for rapid hitsounds
        level_files = []
        try:
            levels_path = resource_path(levels_dir)
            level_files = [f for f in os.listdir(levels_path) if f.endswith('.json')]
            level_files.sort()
        except Exception as e:
            print(f"Error: Could not read levels directory: {levels_dir}")
            print(f"Full error: {e}")
            return None

        if not level_files:
            print("Error: No level files found!")
            return None

        level_metadata = []
        for level_file in level_files:
            try:
                with open(resource_path(os.path.join(levels_dir, level_file)), 'r') as f:
                    data = json.load(f)
                    title = data.get('meta', {}).get('title', 'Unknown')
                    version = data.get('meta', {}).get('version', 'Unknown')
                    artist = data.get('meta', {}).get('artist', 'Unknown')
                    creator = data.get('meta', {}).get('creator', 'Unknown')
                    beatmap_name = level_file.replace('.json', '').split('_')[0]
                    beatmap_dir = f"beatmaps/{beatmap_name}"
                    bg_image = None
                    try:
                        if os.path.exists(resource_path(beatmap_dir)):
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            for file in os.listdir(resource_path(beatmap_dir)):
                                if any(file.lower().endswith(ext) for ext in image_extensions):
                                    bg_path = os.path.join(beatmap_dir, file)
                                    bg_image = pygame.image.load(resource_path(bg_path))
                                    break
                    except:
                        bg_image = None
                    level_metadata.append((level_file, title, version, artist, creator, bg_image))
            except:
                level_metadata.append((level_file, level_file.replace('.json', ''), '', 'Unknown', 'Unknown', None))

    # Window setup - fullscreen borderless
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA - Select Level")
    pygame.mouse.set_visible(True)  # Show mouse in level selector
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 40)
    font_item_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 28)
    font_item_version = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 18)
    font_hint = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 20)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)

    # Scrolling setup - momentum-based smooth scrolling (butter.js style)
    scroll_offset = 0.0  # Current scroll position in pixels
    scroll_velocity = 0.0  # Current scroll velocity
    scroll_friction = 0.92  # Friction coefficient (higher = longer momentum)
    scroll_acceleration = 0.0  # Current acceleration
    item_height = 250
    list_start_y = 100
    list_end_y = window_height - 100  # Extended down more
    available_height = list_end_y - list_start_y
    total_content_height = len(level_metadata) * item_height
    max_scroll = max(0.0, total_content_height - available_height)
    scroll_speed = game_settings.get('scroll_speed', 75)  # Use setting

    # Scrollbar drag tracking
    scrollbar_dragging = False
    drag_start_y = 0
    drag_start_scroll = 0
    
    # Track mouse down position for drag scrolling
    mouse_down_pos = None
    mouse_down_y = 0
    item_dragging = False

    # Hover animation tracking
    hover_animations = {}  # {index: animation_progress (0.0 to 1.0)}
    hover_speed = 0.15  # Animation speed per frame

    selected_level = None
    hovered_index = None

    # We'll render once first, then fade in at the end of the first frame
    first_frame = True

    while selected_level is None:
        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                selected_level = "QUIT"
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Open settings menu
                    settings_result = show_settings_menu(from_selector=True)
                    if settings_result == 'QUIT':
                        selected_level = "QUIT"
                        break
                    # If result is 'BACK' or None, just continue
                    # Reload scroll speed in case it changed
                    scroll_speed = game_settings.get('scroll_speed', 75)
                elif event.key == pygame.K_UP:
                    scroll_velocity -= scroll_speed * 2  # Add velocity in up direction
                elif event.key == pygame.K_DOWN:
                    scroll_velocity += scroll_speed * 2  # Add velocity in down direction

            if event.type == pygame.MOUSEWHEEL:
                scroll_velocity -= event.y * scroll_speed * 1.5  # Multiply for more momentum

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if clicked on scrollbar thumb
                if total_content_height > available_height:
                    scrollbar_x = window_width - 35
                    scrollbar_y = list_start_y
                    scrollbar_width = 20
                    scrollbar_track_height = list_end_y - list_start_y
                    thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
                    thumb_y = scrollbar_y + int((scroll_offset / max_scroll) * (scrollbar_track_height - thumb_height)) if max_scroll > 0 else scrollbar_y
                    thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)

                    if thumb_rect.collidepoint(mouse_pos):
                        scrollbar_dragging = True
                        drag_start_y = mouse_y
                        drag_start_scroll = scroll_offset
                        continue
                
                # Track mouse down position for drag detection (only if inside level selector area)
                viewport_rect = pygame.Rect(0, list_start_y, window_width, list_end_y - list_start_y)
                if viewport_rect.collidepoint(mouse_pos):
                    mouse_down_pos = mouse_pos
                    mouse_down_y = mouse_y
                    item_dragging = False
                else:
                    mouse_down_pos = None

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False
                
                # Only select level if mouse hasn't moved much (not a drag) AND didn't drag at all
                if mouse_down_pos is not None and not item_dragging:
                    drag_distance = abs(mouse_y - mouse_down_y)
                    if drag_distance < 5:  # Tighter threshold - must be almost no movement
                        # Check if clicked on a level item
                        for i in range(len(level_metadata)):
                            item_y = list_start_y + (i * item_height) - scroll_offset
                            # Only check items that are visible in the viewport
                            if item_y + item_height < list_start_y or item_y > list_end_y:
                                continue
                            item_rect = pygame.Rect(50, item_y, window_width - 100, item_height - 5)
                            if item_rect.collidepoint(mouse_pos):
                                selected_level = resource_path(os.path.join(levels_dir, level_metadata[i][0]))
                                break
                
                # Reset drag state
                mouse_down_pos = None
                item_dragging = False

        # Handle continuous arrow key scrolling (when held down)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            scroll_velocity -= scroll_speed / 3  # Continuous velocity change
        if keys[pygame.K_DOWN]:
            scroll_velocity += scroll_speed / 3

        # Handle scrollbar dragging (direct manipulation, no momentum)
        if scrollbar_dragging and total_content_height > available_height:
            scrollbar_track_height = list_end_y - list_start_y
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
            drag_delta_y = mouse_y - drag_start_y
            scroll_delta = (drag_delta_y / (scrollbar_track_height - thumb_height)) * max_scroll if max_scroll > 0 else 0
            new_scroll = max(0, min(max_scroll, drag_start_scroll + scroll_delta))
            scroll_offset = new_scroll
            scroll_velocity = 0  # Cancel momentum during direct manipulation
        
        # Handle item drag scrolling (with momentum)
        elif mouse_down_pos is not None:
            drag_delta_y = mouse_y - mouse_down_y
            if abs(drag_delta_y) > 5:  # Started dragging
                item_dragging = True
                scroll_velocity = -drag_delta_y * 3  # Convert drag to velocity
                mouse_down_y = mouse_y  # Update for continuous drag
        
        # Apply velocity to scroll position
        scroll_offset += scroll_velocity
        
        # Apply friction to velocity (momentum decay)
        scroll_velocity *= scroll_friction
        
        # Stop velocity when it's very small (lower threshold for smoother stop)
        if abs(scroll_velocity) < 0.01:
            scroll_velocity = 0
        
        # Debug output
        if abs(scroll_velocity) > 0.01 or abs(scroll_offset - int(scroll_offset)) > 0.01:
            print(f"Scroll: offset={scroll_offset:.2f}, velocity={scroll_velocity:.2f}")
        
        # Clamp scroll offset and bounce back if out of bounds
        if scroll_offset < 0:
            scroll_offset = 0
            scroll_velocity *= -0.3  # Bounce effect
        elif scroll_offset > max_scroll:
            scroll_offset = max_scroll
            scroll_velocity *= -0.3  # Bounce effect

        # Rendering
        screen.fill((0, 0, 0))

        # Draw title
        title_text = font_title.render("Select a Level", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, 55))
        screen.blit(title_text, title_rect)

        # Draw level list
        list_start_y = 100
        hovered_index = None

        # Update hover animations
        for i in range(len(level_metadata)):
            item_y = list_start_y + (i * item_height) - scroll_offset
            # Only check items that are visible in the viewport
            if item_y + item_height < list_start_y or item_y > list_end_y:
                continue
            item_rect = pygame.Rect(50, item_y, window_width - 100, item_height - 5)

            # Check if mouse is hovering (but not during drag)
            is_hovered = False
            if not item_dragging and item_rect.collidepoint(mouse_pos):
                # Only allow hover if item is fully visible in viewport
                if item_y >= list_start_y and item_y + item_height <= list_end_y:
                    is_hovered = True
                    hovered_index = i

            # Update hover animation for this item
            if i not in hover_animations:
                hover_animations[i] = 0.0

            if is_hovered:
                # Ease in - increase animation progress
                hover_animations[i] = min(1.0, hover_animations[i] + hover_speed)
            else:
                # Fade out quickly
                hover_animations[i] = max(0.0, hover_animations[i] - hover_speed * 2)

        # Set cursor based on whether hovering over any item (not during drag)
        if hovered_index is not None and not item_dragging:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # Set clipping rect to constrain items to viewport
        viewport_rect = pygame.Rect(0, list_start_y, window_width, list_end_y - list_start_y)
        screen.set_clip(viewport_rect)

        # Draw items
        for i in range(len(level_metadata)):
            item_y = list_start_y + (i * item_height) - scroll_offset

            # Skip items that are not visible in the viewport
            if item_y + item_height < list_start_y or item_y > list_end_y:
                continue

            # Keep float position for smooth rendering, create rect for collision only
            item_x = 50
            rect_width = window_width - 100
            rect_height = item_height - 5
            
            # For collision detection, we need an int rect
            item_rect = pygame.Rect(int(item_x), int(item_y), rect_width, rect_height)

            # Get hover animation progress with ease-in curve
            hover_progress = hover_animations.get(i, 0.0)
            eased_progress = hover_progress * hover_progress  # Quadratic ease-in

            # Get metadata
            level_file, title, version, artist, creator, bg_image = level_metadata[i]

            # Draw background image if available (cover + center positioning)
            if bg_image is not None:
                # Calculate scaling to cover the rect while maintaining aspect ratio
                bg_width, bg_height = bg_image.get_size()

                scale_x = rect_width / bg_width
                scale_y = rect_height / bg_height
                scale = max(scale_x, scale_y)  # Cover mode - use larger scale

                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)

                # Scale the image
                scaled_bg = pygame.transform.scale(bg_image, (new_width, new_height))

                # Center crop
                crop_x = (new_width - rect_width) // 2
                crop_y = (new_height - rect_height) // 2
                cropped_bg = scaled_bg.subsurface(pygame.Rect(crop_x, crop_y, rect_width, rect_height))

                # Create a rounded surface for the background
                bg_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                bg_surface.blit(cropped_bg, (0, 0))

                # Apply rounded corners using a mask
                mask_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                pygame.draw.rect(mask_surface, (255, 255, 255, 255), (0, 0, rect_width, rect_height), border_radius=15)
                bg_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

                screen.blit(bg_surface, (item_x, item_y))

                # Draw black to transparent gradient overlay (left to right)
                gradient_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                for x in range(rect_width):
                    # Gradient from black (left) to transparent (right)
                    alpha = int(200 * (1 - x / rect_width))  # 200 max opacity at left, 0 at right
                    pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (x, 0), (x, rect_height))

                screen.blit(gradient_surface, (item_x, item_y))

                # Draw hover overlay with animation (dark overlay)
                if eased_progress > 0.0:
                    hover_alpha = int(100 * eased_progress)
                    hover_overlay = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_overlay, (0, 0, 0, hover_alpha), (0, 0, rect_width, rect_height), border_radius=15)
                    screen.blit(hover_overlay, (item_x, item_y))
            else:
                # No background image - draw solid color background with hover animation
                GRAY = (200, 200, 200)
                if eased_progress > 0.0:
                    # Interpolate between GRAY and darker gray based on hover progress
                    darken_amount = int(80 * eased_progress)
                    r = max(0, GRAY[0] - darken_amount)
                    g = max(0, GRAY[1] - darken_amount)
                    b = max(0, GRAY[2] - darken_amount)
                    item_color = (r, g, b)
                else:
                    item_color = GRAY
                pygame.draw.rect(screen, item_color, (item_x, item_y, rect_width, rect_height), border_radius=15)

            # Draw title (larger)
            total_text_height = 40
            if version:
                total_text_height += 30
            if artist and artist != 'Unknown':
                total_text_height += 25
            if creator and creator != 'Unknown':
                total_text_height += 25

            text_start_y = item_y + (rect_height - total_text_height) // 2

            text_color = (255, 255, 255) if bg_image is not None else (0, 0, 0)
            title_text = font_item_title.render(title, True, text_color)
            screen.blit(title_text, (item_x + 30, text_start_y))

            current_y = text_start_y + 40

            if version:
                version_text = font_item_version.render(f"[{version}]", True, text_color)
                screen.blit(version_text, (item_x + 30, current_y))
                current_y += 30

            if artist and artist != 'Unknown':
                artist_text = font_hint.render(f"Artist: {artist}", True, text_color)
                screen.blit(artist_text, (item_x + 30, current_y))
                current_y += 25

            if creator and creator != 'Unknown':
                creator_text = font_hint.render(f"Mapped by: {creator}", True, text_color)
                screen.blit(creator_text, (item_x + 30, current_y))

        # Remove clipping rect after drawing items
        screen.set_clip(None)

        # Draw scrollbar if needed
        if total_content_height > available_height:
            scrollbar_x = window_width - 35
            scrollbar_y = list_start_y
            scrollbar_width = 20
            scrollbar_track_height = list_end_y - list_start_y

            # Draw scrollbar track
            track_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_track_height)
            pygame.draw.rect(screen, WHITE, track_rect, border_radius=5)

            # Calculate scrollbar thumb size and position
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
            thumb_y = scrollbar_y + int((scroll_offset / max_scroll) * (scrollbar_track_height - thumb_height)) if max_scroll > 0 else scrollbar_y

            # Draw scrollbar thumb
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
            pygame.draw.rect(screen, BLACK, thumb_rect, border_radius=5)

        # Draw hints
        if total_content_height > available_height:
            visible_start = int(scroll_offset / item_height) + 1
            visible_end = min(len(level_metadata), int((scroll_offset + available_height) / item_height) + 1)
            hint_text = font_hint.render(f"Showing {visible_start}-{visible_end} of {len(level_metadata)} | Scroll or use Arrow Keys", True, (200, 200, 200))
            hint_rect = hint_text.get_rect(center=(window_width // 2, window_height - 30))
            screen.blit(hint_text, hint_rect)

        esc_text = font_hint.render("Press ESC for Settings", True, (200, 200, 200))
        esc_rect = esc_text.get_rect(center=(window_width // 2, window_height - 60))
        screen.blit(esc_text, esc_rect)

        # Draw UPDATE TEST in center over everything
        # font_update_test = pygame.font.Font(None, 120)
        # update_test_text = font_update_test.render("UPDATE TEST", True, (160, 32, 240))
        # update_test_rect = update_test_text.get_rect(center=(window_width // 2, window_height // 2))
        # screen.blit(update_test_text, update_test_rect)

        # Fade in on first frame
        if first_frame:
            first_frame = False
            pygame.display.flip()

            if game_settings.get('fade_effects', True):
                fade_surface = pygame.Surface((window_width, window_height))
                fade_surface.fill((0, 0, 0))
                fade_start_time = time.time()
                fade_duration = 0.5 if not fade_in_start else 0.7

                saved_screen = screen.copy()

                while time.time() - fade_start_time < fade_duration:
                    elapsed = time.time() - fade_start_time
                    alpha = int(255 * (1 - elapsed / fade_duration))

                    screen.blit(saved_screen, (0, 0))
                    fade_surface.set_alpha(alpha)
                    screen.blit(fade_surface, (0, 0))
                    pygame.display.flip()
                    clock.tick(60)

        pygame.display.flip()
        clock.tick(60)

    if selected_level == "QUIT":
        return None

    if game_settings.get('fade_effects', True):
        fade_out(screen, duration=0.5)
    return selected_level

def show_quit_confirmation(is_quit_to_menu=False):
    """Show yes/no confirmation for quitting game
    
    Args:
        is_quit_to_menu: If True, shows "Quit to Menu?" instead of "Quit Game?"
    
    Returns:
        True if user confirms quit, False otherwise
    """
    screen = pygame.display.get_surface()
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    # Save current screen
    saved_screen = screen.copy()
    
    font_large = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 52)
    font_button = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 40)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (100, 200, 100)
    RED = (255, 100, 100)
    
    # Create semi-transparent overlay
    overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    
    # Confirmation box dimensions
    box_width = 500
    box_height = 250
    box_x = (window_width - box_width) // 2
    box_y = (window_height - box_height) // 2
    
    result = None
    
    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result = False
                elif event.key == pygame.K_y:
                    result = True
                elif event.key == pygame.K_n:
                    result = False
                    
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if yes_button_rect.collidepoint(mouse_pos):
                    result = True
                elif no_button_rect.collidepoint(mouse_pos):
                    result = False
        
        # Draw saved screen first
        screen.blit(saved_screen, (0, 0))
        
        # Draw overlay
        screen.blit(overlay, (0, 0))
        
        # Draw confirmation box
        box_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(screen, WHITE, box_rect, border_radius=15)
        pygame.draw.rect(screen, BLACK, box_rect, 3, border_radius=15)
        
        # Draw text
        title_text_str = "Quit to Menu?" if is_quit_to_menu else "Quit Game?"
        title_text = font_large.render(title_text_str, True, BLACK)
        title_rect = title_text.get_rect(center=(window_width // 2, box_y + 60))
        screen.blit(title_text, title_rect)
        
        # Draw buttons
        button_y = box_y + 140
        yes_button_rect = pygame.Rect(box_x + 80, button_y, 150, 60)
        no_button_rect = pygame.Rect(box_x + 270, button_y, 150, 60)
        
        # Yes button
        pygame.draw.rect(screen, RED, yes_button_rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, yes_button_rect, 3, border_radius=10)
        yes_text = font_button.render("Yes", True, BLACK)
        yes_text_rect = yes_text.get_rect(center=yes_button_rect.center)
        screen.blit(yes_text, yes_text_rect)
        
        # No button
        pygame.draw.rect(screen, GREEN, no_button_rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, no_button_rect, 3, border_radius=10)
        no_text = font_button.render("No", True, BLACK)
        no_text_rect = no_text.get_rect(center=no_button_rect.center)
        screen.blit(no_text, no_text_rect)
        
        pygame.display.flip()
        clock.tick(60)
    
    return result

def show_settings_menu(from_game=False, from_selector=False):
    """Show settings menu with sliders and keybind remapping
    
    Args:
        from_game: If True, we're pausing from game; if False, it's a standalone settings menu
        from_selector: If True, we're opening from level selector
        
    Returns:
        'RESUME' to resume game, 'QUIT' to quit, or None
    """
    screen = pygame.display.get_surface()
    pygame.display.set_caption(f"TOA - Settings")
    pygame.mouse.set_visible(True)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    font_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 52)
    font_label = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 30)
    font_small = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 24)
    font_button = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 28)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    DARK_GRAY = (60, 60, 60)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)
    RED = (255, 100, 100)
    
    # UI layout
    slider_width = 300
    slider_height = 8
    knob_radius = 12
    
    # Settings state
    music_volume = game_settings.get('music_volume')
    hitsound_volume = game_settings.get('hitsound_volume')
    hitsounds_enabled = game_settings.get('hitsounds_enabled')
    scroll_speed = game_settings.get('scroll_speed')
    fade_effects = game_settings.get('fade_effects', True)
    
    # Keybind remapping state
    waiting_for_key = None  # Which keybind we're waiting to remap
    
    # Slider dragging state
    dragging_slider = None
    
    running = True
    result = None
    
    def draw_slider(x, y, width, height, value, min_val, max_val, label):
        """Draw a horizontal slider"""
        # Label
        label_surface = font_label.render(label, True, WHITE)
        screen.blit(label_surface, (x, y - 35))
        
        # Track
        track_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, DARK_GRAY, track_rect, border_radius=4)
        
        # Filled portion
        filled_width = int((value - min_val) / (max_val - min_val) * width)
        filled_rect = pygame.Rect(x, y, filled_width, height)
        pygame.draw.rect(screen, GREEN, filled_rect, border_radius=4)
        
        # Knob
        knob_x = x + filled_width
        knob_y = y + height // 2
        pygame.draw.circle(screen, WHITE, (knob_x, knob_y), knob_radius)
        pygame.draw.circle(screen, GRAY, (knob_x, knob_y), knob_radius, 2)
        
        # Value display
        value_text = f"{int(value * 100) if min_val == 0 and max_val == 1 else int(value)}"
        if min_val == 0 and max_val == 1:
            value_text += "%"
        value_surface = font_small.render(value_text, True, WHITE)
        screen.blit(value_surface, (x + width + 15, y - 8))
        
        return track_rect
    
    def draw_toggle(x, y, enabled, label):
        """Draw a toggle switch"""
        toggle_width = 60
        toggle_height = 30
        
        # Label
        label_surface = font_label.render(label, True, WHITE)
        screen.blit(label_surface, (x, y - 35))
        
        # Toggle background
        bg_color = GREEN if enabled else DARK_GRAY
        toggle_rect = pygame.Rect(x, y, toggle_width, toggle_height)
        pygame.draw.rect(screen, bg_color, toggle_rect, border_radius=15)
        
        # Toggle knob
        knob_x = x + toggle_width - 18 if enabled else x + 18
        knob_y = y + toggle_height // 2
        pygame.draw.circle(screen, WHITE, (knob_x, knob_y), 12)
        pygame.draw.circle(screen, GRAY, (knob_x, knob_y), 12, 2)
        
        return toggle_rect
    
    def draw_button(x, y, width, height, text, color=GRAY):
        """Draw a button and return its rect"""
        button_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, color, button_rect, border_radius=8)
        pygame.draw.rect(screen, GRAY, button_rect, 2, border_radius=8)
        
        text_surface = font_button.render(text, True, WHITE)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        
        return button_rect
    
    def get_key_name(key_code):
        """Get readable name for pygame key code"""
        if key_code is None:
            return "NONE"
        return pygame.key.name(key_code).upper()
    
    def get_mouse_name(button):
        """Get readable name for mouse button or key"""
        if button is None:
            return "NONE"
        if isinstance(button, int) and button > 10:  # Keyboard keys have higher values than mouse buttons (1-5)
            return get_key_name(button)
        names = {1: "Left Click", 2: "Middle Click", 3: "Right Click", 4: "Scroll Up", 5: "Scroll Down"}
        return names.get(button, f"Button {button}")
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = 'QUIT'
                running = False
                
            if event.type == pygame.KEYDOWN:
                if waiting_for_key:
                    # Check if key is already bound and swap if necessary
                    keybinds = game_settings.get('keybinds')
                    
                    # Check if this key is bound to another keybind
                    conflicting_bind = None
                    for bind_name, bind_key in keybinds.items():
                        if bind_name != waiting_for_key and bind_key == event.key:
                            conflicting_bind = bind_name
                            break
                    
                    # Clear conflict
                    if conflicting_bind:
                        keybinds[conflicting_bind] = None
                    
                    # Set the new binding
                    keybinds[waiting_for_key] = event.key
                    game_settings.set('keybinds', keybinds)
                    waiting_for_key = None
                elif event.key == pygame.K_ESCAPE:
                    if from_game:
                        result = 'BACK'
                    elif from_selector:
                        result = 'BACK'
                    else:
                        result = 'QUIT'
                    running = False
                    
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check slider clicks
                if music_slider_rect.collidepoint(mouse_pos):
                    dragging_slider = 'music'
                elif hitsound_slider_rect.collidepoint(mouse_pos):
                    dragging_slider = 'hitsound'
                elif scroll_slider_rect.collidepoint(mouse_pos):
                    dragging_slider = 'scroll'
                elif hitsounds_toggle_rect.collidepoint(mouse_pos):
                    hitsounds_enabled = not hitsounds_enabled
                    game_settings.set('hitsounds_enabled', hitsounds_enabled)
                elif fade_toggle_rect.collidepoint(mouse_pos):
                    fade_effects = not fade_effects
                    game_settings.set('fade_effects', fade_effects)
                elif quit_menu_rect and quit_menu_rect.collidepoint(mouse_pos):
                    # Show confirmation for quit to menu
                    if show_quit_confirmation(is_quit_to_menu=True):
                        result = 'QUIT_MENU'
                        running = False
                elif restart_rect and restart_rect.collidepoint(mouse_pos):
                    # Restart level
                    result = 'RESTART_LEVEL'
                    running = False
                elif quit_game_rect and quit_game_rect.collidepoint(mouse_pos):
                    # Show confirmation for quit game
                    if show_quit_confirmation(is_quit_to_menu=False):
                        result = 'QUIT'
                        running = False
                # Check keybind buttons
                elif keybind_red_top_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'red_top'
                elif keybind_red_right_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'red_right'
                elif keybind_red_bottom_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'red_bottom'
                elif keybind_red_left_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'red_left'
                elif keybind_blue_top_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'blue_top'
                elif keybind_blue_right_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'blue_right'
                elif keybind_blue_bottom_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'blue_bottom'
                elif keybind_blue_left_rect.collidepoint(mouse_pos):
                    waiting_for_key = 'blue_left'
                elif reset_keybinds_rect.collidepoint(mouse_pos):
                        # Reset all keybinds to default
                        default_keybinds = {
                            'red_top': pygame.K_w,
                            'red_right': pygame.K_d,
                            'red_bottom': pygame.K_s,
                            'red_left': pygame.K_a,
                            'blue_top': pygame.K_UP,
                            'blue_right': pygame.K_RIGHT,
                            'blue_bottom': pygame.K_DOWN,
                            'blue_left': pygame.K_LEFT
                        }
                        game_settings.set('keybinds', default_keybinds)
                        keybinds = default_keybinds
                        mouse_binds = default_mouse_binds
                        
            if event.type == pygame.MOUSEBUTTONUP:
                dragging_slider = None
        
        # Handle slider dragging
        if dragging_slider:
            if dragging_slider == 'music':
                rel_x = mouse_x - music_slider_rect.x
                music_volume = max(0.0, min(1.0, rel_x / slider_width))
                game_settings.set('music_volume', music_volume)
                pygame.mixer.music.set_volume(music_volume)
            elif dragging_slider == 'hitsound':
                rel_x = mouse_x - hitsound_slider_rect.x
                hitsound_volume = max(0.0, min(1.0, rel_x / slider_width))
                game_settings.set('hitsound_volume', hitsound_volume)
            elif dragging_slider == 'scroll':
                rel_x = max(0, min(slider_width, mouse_x - scroll_slider_rect.x))
                scroll_speed = 25 + int((rel_x / slider_width) * 675)  # 25-700
                scroll_speed = max(25, min(700, scroll_speed))  # Clamp
                game_settings.set('scroll_speed', scroll_speed)
        
        # Drawing
        screen.fill((0, 0, 0))
        
        # Title
        title_text = font_title.render("Settings", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, 50))
        screen.blit(title_text, title_rect)
        
        # Layout columns
        left_col_x = window_width // 4 - slider_width // 2
        right_col_x = 3 * window_width // 4 - 150
        
        # Volume sliders (left column)
        y_offset = 140
        music_slider_rect = draw_slider(left_col_x, y_offset, slider_width, slider_height, 
                                        music_volume, 0, 1, "Music Volume")
        
        y_offset += 100
        hitsound_slider_rect = draw_slider(left_col_x, y_offset, slider_width, slider_height,
                                           hitsound_volume, 0, 1, "Hitsound Volume")
        
        y_offset += 80
        hitsounds_toggle_rect = draw_toggle(left_col_x, y_offset, hitsounds_enabled, "Enable Hitsounds")
        
        y_offset += 80
        fade_toggle_rect = draw_toggle(left_col_x, y_offset, fade_effects, "Enable Fade Effects")
        
        y_offset += 100
        scroll_slider_rect = draw_slider(left_col_x, y_offset, slider_width, slider_height,
                                         scroll_speed, 25, 700, "Scroll Speed")
        
        # Keybinds (right column)
        keybinds = game_settings.get('keybinds')
        
        y_offset = 140
        keybind_label = font_label.render("Red Keys (WASD)", True, RED)
        screen.blit(keybind_label, (right_col_x, y_offset - 35))
        
        button_width = 200
        button_height = 35
        button_spacing = 42
        
        # Red keys
        if waiting_for_key == 'red_top':
            key_text = "Press a key..."
        else:
            key_text = f"Top: {get_key_name(keybinds['red_top'])}"
        color = BLUE if waiting_for_key == 'red_top' else GRAY
        keybind_red_top_rect = draw_button(right_col_x, y_offset, button_width, button_height, 
                                       key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'red_right':
            key_text = "Press a key..."
        else:
            key_text = f"Right: {get_key_name(keybinds['red_right'])}"
        color = BLUE if waiting_for_key == 'red_right' else GRAY
        keybind_red_right_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                         key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'red_bottom':
            key_text = "Press a key..."
        else:
            key_text = f"Bottom: {get_key_name(keybinds['red_bottom'])}"
        color = BLUE if waiting_for_key == 'red_bottom' else GRAY
        keybind_red_bottom_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                          key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'red_left':
            key_text = "Press a key..."
        else:
            key_text = f"Left: {get_key_name(keybinds['red_left'])}"
        color = BLUE if waiting_for_key == 'red_left' else GRAY
        keybind_red_left_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                        key_text, color)
        
        # Blue keys
        y_offset += button_spacing + 20
        blue_label = font_label.render("Blue Keys (Arrows)", True, BLUE)
        screen.blit(blue_label, (right_col_x, y_offset - 15))
        
        y_offset += 30
        if waiting_for_key == 'blue_top':
            key_text = "Press a key..."
        else:
            key_text = f"Top: {get_key_name(keybinds['blue_top'])}"
        color = BLUE if waiting_for_key == 'blue_top' else GRAY
        keybind_blue_top_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                     key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'blue_right':
            key_text = "Press a key..."
        else:
            key_text = f"Right: {get_key_name(keybinds['blue_right'])}"
        color = BLUE if waiting_for_key == 'blue_right' else GRAY
        keybind_blue_right_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                      key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'blue_bottom':
            key_text = "Press a key..."
        else:
            key_text = f"Bottom: {get_key_name(keybinds['blue_bottom'])}"
        color = BLUE if waiting_for_key == 'blue_bottom' else GRAY
        keybind_blue_bottom_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                          key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'blue_left':
            key_text = "Press a key..."
        else:
            key_text = f"Left: {get_key_name(keybinds['blue_left'])}"
        color = BLUE if waiting_for_key == 'blue_left' else GRAY
        keybind_blue_left_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                        key_text, color)
        
        # Reset button
        y_offset += button_spacing + 10
        reset_keybinds_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                         "Reset to Default", DARK_GRAY)
        
        # Bottom buttons
        button_y = window_height - 110
        if from_game:
            quit_menu_rect = draw_button(window_width // 2 - 320, button_y, 200, 50, "Quit to Menu", RED)
            restart_rect = draw_button(window_width // 2 - 100, button_y, 200, 50, "Restart", BLUE)
            quit_game_rect = draw_button(window_width // 2 + 120, button_y, 200, 50, "Quit Game", RED)
        elif from_selector:
            quit_menu_rect = None
            restart_rect = None
            quit_game_rect = draw_button(window_width // 2 - 100, button_y, 200, 50, "Quit Game", RED)
        else:
            quit_menu_rect = None
            restart_rect = None
            quit_game_rect = draw_button(window_width // 2 - 100, button_y, 200, 50, "Back", GRAY)
        
        # Hint text
        if from_selector or from_game:
            hint_text = "Press ESC to go back"
        else:
            hint_text = "Press ESC to go back"
        hint_surface = font_small.render(hint_text, True, GRAY)
        hint_rect = hint_surface.get_rect(center=(window_width // 2, window_height - 30))
        screen.blit(hint_surface, hint_rect)
        
        # Update cursor based on hover states
        mouse_pos = pygame.mouse.get_pos()
        hovering_button = False
        if quit_menu_rect and quit_menu_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif quit_game_rect and quit_game_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif reset_keybinds_rect and reset_keybinds_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_red_top_rect and keybind_red_top_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_red_right_rect and keybind_red_right_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_red_bottom_rect and keybind_red_bottom_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_red_left_rect and keybind_red_left_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_blue_top_rect and keybind_blue_top_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_blue_right_rect and keybind_blue_right_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_blue_bottom_rect and keybind_blue_bottom_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_blue_left_rect and keybind_blue_left_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif hitsounds_toggle_rect and hitsounds_toggle_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif fade_toggle_rect and fade_toggle_rect.collidepoint(mouse_pos):
            hovering_button = True
        
        if hovering_button or dragging_slider:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.mouse.set_visible(True)
    return result


def show_autoplay_popup():
    """Show popup window to ask about autoplay"""
    screen = pygame.display.get_surface()
    pygame.display.set_caption(f"TOA - Setup")
    pygame.mouse.set_visible(True)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 60)
    font_small = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 40)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    def draw_autoplay_content(surf):
        surf.fill((0, 0, 0))
        title_text = font_large.render("Enable Autoplay?", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        surf.blit(title_text, title_rect)

        yes_text = font_small.render("Press Y for Yes", True, WHITE)
        yes_rect = yes_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
        surf.blit(yes_text, yes_rect)

        no_text = font_small.render("Press N for No", True, WHITE)
        no_rect = no_text.get_rect(center=(window_width // 2, window_height // 2 + 80))
        surf.blit(no_text, no_rect)

    if game_settings.get('fade_effects', True):
        fade_in(screen, draw_autoplay_content, duration=0.5)
    else:
        draw_autoplay_content(screen)
        pygame.display.flip()

    result = None
    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    result = True
                    break
                elif event.key == pygame.K_n:
                    result = False
                    break
                elif event.key == pygame.K_ESCAPE:
                    result = 'BACK'
                    break

        if result is not None:
            break

        draw_autoplay_content(screen)
        pygame.display.flip()
        clock.tick(60)

    if game_settings.get('fade_effects', True):
        fade_out(screen, duration=0.3)
    return result

def main(level_json=None, audio_dir=None, returning_from_game=False, preloaded_metadata=None):
    """
    Main game function.

    Args:
        level_json: Path to the level JSON file (if None, will show level selection popup)
        audio_dir: Directory containing audio.mp3 (if None, will infer from level_json path)
        returning_from_game: If True, we're returning from game and should fade in level selector
        preloaded_metadata: Pre-loaded level metadata from loading screen
    """
    if level_json is None:
        # Go straight to song packs
        from songpack_ui import show_songpack_selector, show_pack_levels_selector, build_pack_metadata_cache
        
        # Initialize pygame if not already
        if not pygame.get_init():
            pygame.init()
        
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        
        while True:
            # Show song pack selector
            selected_pack = show_songpack_selector(screen, game_settings, resource_path)
            
            if selected_pack == "QUIT" or selected_pack is None:
                print("Exiting...")
                return
            
            # Use pre-loaded metadata cache for instant loading
            metadata_cache = selected_pack.get('metadata_cache', None)
            
            # Show levels in the pack (with pre-loaded metadata)
            level_json = show_pack_levels_selector(screen, selected_pack, game_settings, resource_path, metadata_cache)
            
            if level_json == "QUIT":
                return
            elif level_json is not None:
                # Level selected, break and continue to game
                break
            # else go back to song pack selector

    if audio_dir is None:
        # First check if the level JSON has audio_file metadata (from song packs)
        try:
            with open(level_json, 'r', encoding='utf-8') as f:
                level_data = json.load(f)
                audio_file_path = level_data.get('meta', {}).get('audio_file')
                
                if audio_file_path and os.path.exists(audio_file_path):
                    # Use the directory containing the audio file
                    audio_dir = os.path.dirname(audio_file_path)
                else:
                    # Fallback to traditional beatmap structure
                    level_filename = os.path.basename(level_json)
                    beatmap_name = level_filename.replace('.json', '').split('_')[0]
                    audio_dir = f"beatmaps/{beatmap_name}"
        except:
            # Fallback to traditional beatmap structure
            level_filename = os.path.basename(level_json)
            beatmap_name = level_filename.replace('.json', '').split('_')[0]
            audio_dir = f"beatmaps/{beatmap_name}"

    # Autoplay is now a debug feature controlled by Ctrl+P
    autoplay_enabled = game_settings.get('autoplay_enabled', False)

    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA")
    pygame.mouse.set_visible(True)

    pygame.event.pump()

    clock = pygame.time.Clock()
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (150, 150, 150)

    screen.fill(BLACK)
    pygame.display.flip()

    screen_width, screen_height = screen.get_size()
    center_x, center_y = screen_width // 2, screen_height // 2

    square_size = 70
    spacing = 75
    border_width = 3
    radius = 10

    last_clicked_button = None
    click_time = 0
    shake_time = 0
    shake_intensity = 0
    shake_box = None
    
    # Track input flashes for each box (shows taps even when nothing is hit)
    # Format: {box_idx: (time, color)}
    input_flashes = {}

    # ===== Particle system for hit effects =====
    particles = []  # [(x, y, vx, vy, color, size, birth_time)]
    
    # Hit glow effects
    hit_glows = []  # [(box_idx, start_time, intensity)]
    
    # Impact waves (expanding circles)
    impact_waves = []  # [(x, y, start_time, color)]
    
    # Screen flash for perfect hits
    screen_flash_time = 0
    screen_flash_alpha = 0

    # Dot switch animation
    last_active_dots = set()  # Track previously active dots
    dot_pulse_times = {}  # {dot_idx: start_time} for individual pulse animations
    dot_switch_ripples = []  # [(dot_idx, start_time)]

    game_start_time = time.time()
    current_event_index = 0
    score = 0
    total_hits = 0
    total_notes = 0
    accuracy_window = 0.15

    with open(resource_path(level_json), "r") as f:
        level_data = json.load(f)

    level = []
    for event in level_data["level"]:
        hitsound_data = {
            'whistle': event.get('whistle', False),
            'finish': event.get('finish', False),
            'clap': event.get('clap', False)
        }
        level.append((event["t"], event["box"], event["color"], hitsound_data))

    # Calculate optimal approach duration to prevent tile overlap
    # Find minimum time gap between any consecutive notes
    min_time_gap = float('inf')
    if len(level) > 1:
        for i in range(len(level) - 1):
            time_gap = level[i + 1][0] - level[i][0]
            if time_gap > 0 and time_gap < min_time_gap:
                min_time_gap = time_gap
    
    # Calculate approach duration that ensures tiles never overlap
    # tile_size = 65px, min_spacing = 10px, travel_distance = screen_width // 2
    tile_size = 65
    min_spacing = 10
    min_distance_needed = tile_size + min_spacing
    travel_distance = screen_width // 2
    
    # For tiles to not overlap: (travel_distance / approach_duration) * min_time_gap >= min_distance_needed
    # So: approach_duration <= (travel_distance * min_time_gap) / min_distance_needed
    if min_time_gap != float('inf'):
        max_safe_approach_duration = (travel_distance * min_time_gap) / min_distance_needed
        # Increase by 0.2s to make tiles move slower
        max_safe_approach_duration += 0.2
        # Clamp between 0.5s (too fast to read) and 2.0s (too slow)
        APPROACH_DURATION = max(0.5, min(2.0, max_safe_approach_duration))
    else:
        # Single note or no notes, use default
        APPROACH_DURATION = 1.0
    
    # Check if this is a converted SM chart (has source metadata)
    is_sm_chart = 'converted_from_sm' in level_data.get('meta', {}).get('pattern', '')
    
    # For SM charts, we need to handle timing differently
    music_offset_adjustment = 3.0
    audio_start_position = 0.0
    
    if is_sm_chart:
        # SM charts have offset baked in, which can result in negative note times
        # Negative note time means audio must be further ahead when that note plays
        if level:
            min_time = min(t for t, _, _, _ in level)
            if min_time < 0:
                # Shift all notes so first one is at 3.0 seconds (after countdown)
                shift_amount = 3.0 - min_time  # e.g., 3.0 - (-14.588) = 17.588
                level = [(t + shift_amount, box, color, hs) for t, box, color, hs in level]
                # Audio needs to seek forward by abs(min_time)
                # When game time is 3.0 (first note), audio should be at 14.588
                # Music starts at game time 3.0, so we seek to abs(min_time)
                audio_start_position = abs(min_time)
            else:
                # No negative times, just add countdown
                level = [(t + 3.0, box, color, hs) for t, box, color, hs in level]
        else:
            level = [(t + 3.0, box, color, hs) for t, box, color, hs in level]
    else:
        # OSU charts need the standard 3 second offset
        level = [(t + 3.0, box, color, hs) for t, box, color, hs in level]

    target_box = None
    target_color = None
    target_time = None
    target_hitsound = None

    # Track approach indicators - list of (box_index, color, target_time, approach_duration, event_index, side)
    approach_indicators = []
    # Track fading tiles for missed notes - list of (box_index, color, x, y, start_time)
    fading_tiles = []

    # Load and scale box image
    box_image = pygame.image.load(resource_path("assets/box.jpg")).convert()
    box_image = pygame.transform.scale(box_image, (square_size, square_size))

    box_red_image = pygame.image.load(resource_path("assets/boxred.jpg")).convert()
    box_red_image = pygame.transform.scale(box_red_image, (square_size, square_size))
    box_blue_image = pygame.image.load(resource_path("assets/boxblue.jpg")).convert()
    box_blue_image = pygame.transform.scale(box_blue_image, (square_size, square_size))

    dot_image = pygame.image.load(resource_path("assets/dot.jpg")).convert()
    dot_image = pygame.transform.scale(dot_image, (35, 35))
    dot2_image = pygame.image.load(resource_path("assets/dot2.jpg")).convert()
    dot2_image = pygame.transform.scale(dot2_image, (35, 35))

    # Load background music using AudioFilename from .osu if available
    audio_path = None
    audio_extensions = ['.mp3', '.ogg', '.wav', '.flac', '.aac', '.m4a']
    osu_audio_filename = None
    try:
        # Try to find the .osu file matching the level
        level_base = os.path.splitext(os.path.basename(level_json))[0]
        # Remove difficulty suffix (after last underscore)
        if '_' in level_base:
            base_name = level_base.rsplit('_', 1)[0]
        else:
            base_name = level_base
        # Find .osu file in audio_dir that matches base_name
        osu_file = None
        for file in os.listdir(resource_path(audio_dir)):
            if file.lower().endswith('.osu') and base_name.lower() in file.lower():
                osu_file = os.path.join(audio_dir, file)
                break
        # Parse AudioFilename from .osu file
        if osu_file and os.path.exists(resource_path(osu_file)):
            with open(resource_path(osu_file), 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip().lower().startswith('audiofilename:'):
                        osu_audio_filename = line.strip().split(':', 1)[1].strip()
                        break
        # If found, use it
        if osu_audio_filename:
            candidate = os.path.join(audio_dir, osu_audio_filename)
            if os.path.exists(resource_path(candidate)):
                audio_path = candidate
        # Fallback: search for any audio file
        if audio_path is None:
            files = os.listdir(resource_path(audio_dir))
            for ext in audio_extensions:
                for file in files:
                    if file.lower().endswith(ext):
                        audio_path = os.path.join(audio_dir, file)
                        break
                if audio_path:
                    break
        if audio_path is None:
            raise FileNotFoundError(f"No audio file ({', '.join(audio_extensions)}) found in audio directory")
    except Exception as e:
        print(f"Error finding audio file: {e}")
        audio_path = os.path.join(audio_dir, "audio.mp3")

    # Load music with error handling
    try:
        full_audio_path = resource_path(audio_path)
        print(f"Loading music from: {full_audio_path}")
        if not os.path.exists(full_audio_path):
            print(f"WARNING: Audio file not found: {full_audio_path}")
            print(f"Audio directory contents: {os.listdir(resource_path(audio_dir)) if os.path.exists(resource_path(audio_dir)) else 'Directory not found'}")
        pygame.mixer.music.load(full_audio_path)
        pygame.mixer.music.set_volume(game_settings.get('music_volume', 0.7))
        print(f"Music loaded successfully: {audio_path}")
    except Exception as e:
        print(f"ERROR loading music: {e}")
        print(f"Attempted to load from: {resource_path(audio_path)}")
    music_start_time = None

    # Load hitsounds
    hitsounds = {}
    hitsound_extensions = ['.wav', '.ogg', '.mp3', '.flac', '.aac', '.m4a']
    
    # Load default hitsound from assets
    default_hitsound = None
    try:
        default_hit_path = resource_path('assets/hit.wav')
        if os.path.exists(default_hit_path):
            default_hitsound = pygame.mixer.Sound(default_hit_path)
            default_hitsound.set_volume(game_settings.get('hitsound_volume', 0.3))
    except Exception as e:
        print(f"Could not load default hitsound: {e}")
    
    try:
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = None
            # Try to load from beatmap folder first
            for prefix in ['normal', 'soft', 'drum']:
                for ext in hitsound_extensions:
                    sound_file = f"{prefix}-hit{sound_name}{ext}"
                    sound_path = os.path.join(audio_dir, sound_file)
                    if os.path.exists(resource_path(sound_path)):
                        sound = pygame.mixer.Sound(resource_path(sound_path))
                        break
                if sound:
                    break
            
            # If not found, use default hitsound from assets
            if sound is None and default_hitsound is not None:
                sound = default_hitsound
            elif sound is None:
                # Last resort: silent sound
                sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            
            sound.set_volume(game_settings.get('hitsound_volume', 0.3))
            hitsounds[sound_name] = sound
    except Exception as e:
        print(f"Could not load hitsounds: {e}")
        # Fallback to default or silent sounds
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            if default_hitsound is not None:
                sound = default_hitsound
            else:
                sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(game_settings.get('hitsound_volume', 0.3))
            hitsounds[sound_name] = sound

    # Load beatmap background image if available
    beatmap_bg_image = None
    gameplay_bg_image = None  # Full screen background for gameplay
    
    try:
        # First check if level JSON has a background_file in metadata (from song packs)
        bg_file_from_meta = level_data.get('meta', {}).get('background_file')
        
        if bg_file_from_meta and os.path.exists(bg_file_from_meta):
            # Load the BG.png from song pack
            gameplay_bg = pygame.image.load(bg_file_from_meta)
            # Scale to full screen
            gameplay_bg_image = pygame.transform.scale(gameplay_bg, (screen_width, screen_height))
            # Create dark overlay
            dark_overlay = pygame.Surface((screen_width, screen_height))
            dark_overlay.set_alpha(180)  # Adjust darkness (0-255)
            dark_overlay.fill((0, 0, 0))
            # Apply overlay to gameplay background
            gameplay_bg_image.blit(dark_overlay, (0, 0))
            
            # Also use for small thumbnail
            beatmap_bg_image = pygame.transform.scale(gameplay_bg, (200, 150))
        else:
            # Fallback to finding images in audio_dir
            for file in os.listdir(resource_path(audio_dir)):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    bg_path = os.path.join(audio_dir, file)
                    bg_img = pygame.image.load(resource_path(bg_path))
                    
                    # Check if this is BG.png (for full screen gameplay background)
                    if file.lower().startswith('bg'):
                        gameplay_bg = bg_img.copy()
                        gameplay_bg_image = pygame.transform.scale(gameplay_bg, (screen_width, screen_height))
                        dark_overlay = pygame.Surface((screen_width, screen_height))
                        dark_overlay.set_alpha(180)
                        dark_overlay.fill((0, 0, 0))
                        gameplay_bg_image.blit(dark_overlay, (0, 0))
                    
                    # Create thumbnail version
                    original_width, original_height = bg_img.get_size()
                    target_height = 150
                    aspect_ratio = original_width / original_height
                    target_width = int(target_height * aspect_ratio)
                    beatmap_bg_image = pygame.transform.scale(bg_img, (target_width, target_height))
                    break
    except Exception as e:
        print(f"Could not load beatmap background: {e}")
        beatmap_bg_image = None
        gameplay_bg_image = None

    def create_rounded_image(image, radius):
        """Create an image with rounded corners"""
        size = image.get_size()
        rounded_image = pygame.Surface(size, pygame.SRCALPHA)
        rounded_image.blit(image, (0, 0))
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size[0], size[1]), 0, radius)
        rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return rounded_image.convert_alpha()

    box_image_rounded = create_rounded_image(box_image, 8)
    box_red_rounded = create_rounded_image(box_red_image, 8)
    box_blue_rounded = create_rounded_image(box_blue_image, 8)
    
    # Pre-cache gradient surfaces for edge flashes
    gradient_cache = {}
    def get_cached_gradient(direction, length, height, color, max_alpha):
        """Get or create a cached gradient surface"""
        key = (direction, length, height, color, max_alpha)
        if key not in gradient_cache:
            gradient_surface = pygame.Surface((length, height), pygame.SRCALPHA)
            for i in range(length):
                progress = i / length
                if direction == 'left':
                    alpha = int(max_alpha * progress)
                else:  # right
                    alpha = int(max_alpha * (1 - progress))
                pygame.draw.line(gradient_surface, (*color, alpha), (i, 0), (i, height))
            gradient_cache[key] = gradient_surface.convert_alpha()
        return gradient_cache[key]
    
    # Pre-render common text surfaces
    text_cache = {}
    def get_cached_text(font, text, color):
        """Get or create cached text surface"""
        key = (id(font), text, color)
        if key not in text_cache:
            text_cache[key] = font.render(text, True, color)
        return text_cache[key]

    dot_radius = 10
    move_time = 0

    def get_dot_positions(cx, cy, size, sp):
        """Dot positions on the INNER sides (toward the middle gap)."""
        inset = 35
        top_y    = cy - size - sp
        bottom_y = cy + sp
        left_x   = cx - size - sp
        right_x  = cx + sp

        top_inner_edge_y    = top_y + size
        bottom_inner_edge_y = bottom_y
        left_inner_edge_x   = left_x + size
        right_inner_edge_x  = right_x

        return [
            (cx, top_inner_edge_y + inset),
            (right_inner_edge_x - inset, cy),
            (cx, bottom_inner_edge_y - inset),
            (left_inner_edge_x + inset, cy),
        ]

    dot_positions = get_dot_positions(center_x, center_y, square_size, spacing)

    font_countdown = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 100)
    font_judgment = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 32)
    font_stats = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 28)
    font_metadata = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 20)
    font_combo = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'segoeui', 'arial'], 48)

    count_fantastic = 0
    count_perfect = 0
    count_great = 0
    count_cool = 0
    count_bad = 0
    count_miss = 0
    
    # Health system
    max_health = 75.0
    current_health = 75.0
    target_health = 75.0  # Animated health bar target
    displayed_health = 75.0  # Current animated health
    lost_health_bars = []  # [(width, alpha, timestamp)] - white bars showing health loss
    judgment_displays = []

    combo = 0
    combo_pop_time = 0
    combo_animation_duration = 0.08

    # Track events that have already shown "tile reached box" shake
    reached_shake_events = set()
    resolved_events = set()

    paused = False
    pause_start_time = 0
    total_pause_duration = 0
    paused_elapsed_time = 0

    fade_in_alpha = 255
    fade_in_duration = 1.0
    fade_in_delay = 0.3

    # ===== Arrival flash settings (THIS is the "flash once when tile arrives") =====
    arrival_flash_duration = 0.18   # total flash time
    arrival_flash_sustain = 0.03    # full-bright time at the start
    arrival_flash_index = 0         # moving pointer for efficient scanning
    arrival_shake_index = 0  # NEW: drives arrival shake purely by level timing

    # ======= Hitcheck helpers =======
    
    # Key mappings for 8-key system - built from settings
    # Since users might map multiple actions to the same key, we store a list of (color, box) per key
    keybinds = game_settings.get('keybinds')
    KEY_MAPPINGS = {}
    
    # Add all keybinds, allowing multiple mappings per key
    key_mapping_list = [
        (keybinds['red_top'], 'red', 0),
        (keybinds['red_right'], 'red', 1),
        (keybinds['red_bottom'], 'red', 2),
        (keybinds['red_left'], 'red', 3),
        (keybinds['blue_top'], 'blue', 0),
        (keybinds['blue_right'], 'blue', 1),
        (keybinds['blue_bottom'], 'blue', 2),
        (keybinds['blue_left'], 'blue', 3)
    ]
    
    for key, color, box_idx in key_mapping_list:
        if key not in KEY_MAPPINGS:
            KEY_MAPPINGS[key] = []
        KEY_MAPPINGS[key].append((color, box_idx))
    
    # Track which keys are currently pressed
    keys_pressed = set()

    # New 5-tier judgment system with symmetric timing windows
    # Timing windows (in seconds from perfect time):
    # bad: 0.150 - 0.100
    # cool: 0.100 - 0.060
    # great: 0.060 - 0.030
    # perfect: 0.030 - 0.015
    # fantastic: 0.015 - 0.000 (closest to exact time)
    # Then symmetric on the other side
    
    TIMING_WINDOWS = [
        (0.0225, 'fantastic', 500, 0.5),   # fantastic: ±15ms, score 500, health +0.5
        (0.045, 'perfect', 400, 1.0),     # perfect: ±30ms, score 400, health +1
        (0.090, 'great', 300, 0.5),       # great: ±60ms, score 300, health +0.5
        (0.135, 'cool', 100, 0.0),        # cool: ±100ms, score 100, health 0
        (0.180, 'bad', 50, -1.0),         # bad: ±150ms, score 50, health -1
    ]
    
    # Maximum timing window (for miss detection)
    MAX_TIMING_WINDOW = 0.180

    def judgment_from_timing(elapsed_time, note_time):
        """Get judgment based on timing difference (can be early or late)"""
        timing_diff = abs(elapsed_time - note_time)
        
        # Check each timing window from tightest to loosest
        for window, name, score, health_change in TIMING_WINDOWS:
            if timing_diff <= window:
                return name, score, health_change
        
        # Outside all windows = miss
        return None, None, None

    def box_centers_display():
        return [
            (center_x, center_y - square_size // 2 - spacing),
            (center_x + square_size // 2 + spacing, center_y),
            (center_x, center_y + square_size // 2 + spacing),
            (center_x - square_size // 2 - spacing, center_y),
        ]

    def add_judgment_text(text, box_idx):
        import random
        cx, cy = box_centers_display()[box_idx]
        side = random.choice([-1, 1])
        judgment_displays.append((text, cx, cy, time.time(), box_idx, side))

    def trigger_box_shake(box_idx, intensity=9):
        nonlocal shake_time, shake_intensity, shake_box
        shake_time = time.time()
        shake_intensity = intensity
        shake_box = box_idx

    def resolve_miss(evt_idx, miss_box_idx):
        nonlocal count_miss, total_notes, combo, current_event_index, current_health, lost_health_bars
        nonlocal fading_tiles, approach_indicators
        count_miss += 1
        total_notes += 1
        combo = 0
        # Track old health for animation
        old_health = current_health
        # Misses decrease health by 2
        current_health = max(0, current_health - 2.0)
        # Don't update target_health here - let it animate smoothly down
        # Record health loss for white bar animation
        if old_health > current_health:
            health_bar_width = int(screen_width * 0.3)
            old_width = int(health_bar_width * (old_health / max_health))
            lost_health_bars.append((old_width, 255, time.time()))
        add_judgment_text("miss", miss_box_idx)
        
        resolved_events.add(evt_idx)
        current_event_index += 1

    def resolve_hit(evt_idx, hit_box_idx, judgment_name, judgment_score, health_change):
        nonlocal score, total_hits, total_notes, combo, combo_pop_time, current_event_index
        nonlocal count_fantastic, count_perfect, count_great, count_cool, count_bad, current_health
        nonlocal particles, hit_glows, impact_waves, screen_flash_time, screen_flash_alpha
        nonlocal lost_health_bars, fading_tiles, approach_indicators, game_over
        
        # Track old health for animation
        old_health = current_health
        # Apply health change
        current_health = max(0, min(max_health, current_health + health_change))
        # Don't update target_health here - let displayed_health animate to current_health
        # Record health loss for white bar animation (only on damage)
        if old_health > current_health:
            health_bar_width = int(screen_width * 0.3)
            old_width = int(health_bar_width * (old_health / max_health))
            lost_health_bars.append((old_width, 255, time.time()))

        score += judgment_score
        total_hits += 1
        total_notes += 1
        combo += 1
        combo_pop_time = time.time()

        # Update judgment counts
        if judgment_name == 'fantastic':
            count_fantastic += 1
        elif judgment_name == 'perfect':
            count_perfect += 1
        elif judgment_name == 'great':
            count_great += 1
        elif judgment_name == 'cool':
            count_cool += 1
        elif judgment_name == 'bad':
            count_bad += 1

        add_judgment_text(judgment_name, hit_box_idx)
        if not game_over:
            trigger_box_shake(hit_box_idx, intensity=9)
        if game_settings.get('hitsounds_enabled', True):
            hitsounds['normal'].play()

        # ===== ADD FLASHY EFFECTS =====
        # Get box center for effects
        box_centers = box_centers_display()
        hit_x, hit_y = box_centers[hit_box_idx]
        current_time = time.time()
        
        # Determine effect color based on judgment
        if judgment_name == 'fantastic':
            # Fantastic - bright cyan particles
            particle_color = (0, 255, 255)  # Cyan
            particle_count = 30
            glow_intensity = 2.0
        elif judgment_name == 'perfect':
            # Perfect - gold particles
            particle_color = (255, 215, 0)  # Gold
            particle_count = 25
            glow_intensity = 1.5
        elif judgment_name == 'great':
            # Great - white particles
            particle_color = (255, 255, 255)  # White
            particle_count = 20
            glow_intensity = 1.2
        elif judgment_name == 'cool':
            # Cool - light blue particles
            particle_color = (180, 220, 255)
            particle_count = 15
            glow_intensity = 0.8
        else:  # bad
            # Bad - gray particles
            particle_color = (150, 150, 150)
            particle_count = 10
            glow_intensity = 0.5
        
        # Create particle burst
        import random
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.uniform(3, 7)
            particles.append((hit_x, hit_y, vx, vy, particle_color, size, current_time))
        
        # Add hit glow effect
        hit_glows.append((hit_box_idx, current_time, glow_intensity))
        
        # Add impact wave
        impact_waves.append((hit_x, hit_y, current_time, particle_color))

        resolved_events.add(evt_idx)
        current_event_index += 1

    def handle_click(button_name, elapsed_time_local, evt_idx):
        if evt_idx >= len(level):
            return False

        evt_time, evt_box, evt_color, evt_hitsound = level[evt_idx]

        # Check if the pressed key matches the note (both color and box position)
        if button_name != evt_color:
            return False

        # Get judgment based on timing
        judgment_name, judgment_score, health_change = judgment_from_timing(elapsed_time_local, evt_time)
        
        # If outside all timing windows, don't register hit
        if judgment_name is None:
            return False
        
        resolve_hit(evt_idx, evt_box, judgment_name, judgment_score, health_change)
        return True


    running = True

    # ===== End-of-level handling (2s delay, 3s music fade, then return to level selector) =====
    level_end_elapsed = None
    music_fade_started = False
    music_fade_start_elapsed = None
    POST_LEVEL_DELAY = 3.0
    POST_LEVEL_MUSIC_FADE = 3.0
    
    # Game over on HP = 0
    game_over = False
    game_over_time = None

    while running:
        elapsed_time = time.time() - game_start_time - total_pause_duration

        if game_settings.get('fade_effects', True):
            if elapsed_time < fade_in_delay:
                fade_in_alpha = 255
            elif elapsed_time < fade_in_delay + fade_in_duration:
                fade_progress = (elapsed_time - fade_in_delay) / fade_in_duration
                fade_in_alpha = int(255 * (1 - fade_progress))
            else:
                fade_in_alpha = 0
        else:
            fade_in_alpha = 0

        display_time = paused_elapsed_time if paused else elapsed_time

        if music_start_time is None and elapsed_time >= music_offset_adjustment and not paused:
            # For SM charts with negative times, seek to the calculated position
            if audio_start_position > 0:
                pygame.mixer.music.play(start=audio_start_position)
            else:
                pygame.mixer.music.play()
            music_start_time = time.time()

        if current_event_index < len(level):
            target_time, target_box, target_color, target_hitsound = level[current_event_index]
        
        # Autoplay
        if autoplay_enabled and not paused and current_event_index < len(level):
            if elapsed_time >= target_time:
                score += 500  # Fantastic score
                total_hits += 1
                total_notes += 1
                combo += 1
                combo_pop_time = time.time()
                count_fantastic += 1
                # Autoplay always gets perfect timing, so health +0.5
                current_health = min(max_health, current_health + 0.5)

                add_judgment_text("fantastic", target_box)
                resolved_events.add(current_event_index)
                if not game_over:
                    trigger_box_shake(target_box, intensity=9)

                # Play hitsounds during autoplay
                if game_settings.get('hitsounds_enabled', True):
                    hitsounds['normal'].play()
                
                # ===== ADD FANCY EFFECTS TO AUTOPLAY =====
                # Get box center for effects
                box_centers = box_centers_display()
                hit_x, hit_y = box_centers[target_box]
                current_time = time.time()
                
                # Perfect autoplay always gets gold effects
                particle_color = (255, 215, 0)  # Gold
                particle_count = 25
                glow_intensity = 1.5
                
                # Create particle burst
                import random
                for _ in range(particle_count):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(100, 300)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    size = random.uniform(3, 7)
                    particles.append((hit_x, hit_y, vx, vy, particle_color, size, current_time))
                
                # Add hit glow effect
                hit_glows.append((target_box, current_time, glow_intensity))
                
                # Add impact wave
                impact_waves.append((hit_x, hit_y, current_time, particle_color))
                
                # Trigger dot animation for autoplay
                if target_box not in last_active_dots:
                    dot_pulse_times[target_box] = current_time
                    dot_switch_ripples.append((target_box, current_time))
                    last_active_dots.add(target_box)
                
                current_event_index += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                # Check for Ctrl+P to toggle autoplay (debug feature)
                keys_held = pygame.key.get_pressed()
                if event.key == pygame.K_p and (keys_held[pygame.K_LCTRL] or keys_held[pygame.K_RCTRL]):
                    autoplay_enabled = not autoplay_enabled
                    game_settings.set('autoplay_enabled', autoplay_enabled)
                    print(f"Autoplay {'enabled' if autoplay_enabled else 'disabled'}")
                
                if event.key == pygame.K_ESCAPE:
                    # Pause and show settings menu
                    paused = True
                    pause_start_time = time.time()
                    paused_elapsed_time = elapsed_time
                    pygame.mixer.music.pause()
                    
                    # Show settings menu
                    settings_result = show_settings_menu(from_game=True)
                    
                    if settings_result == 'BACK':
                        # Resume game
                        paused = False
                        total_pause_duration += time.time() - pause_start_time
                        pygame.mixer.music.unpause()
                        # Update volumes in case they changed
                        pygame.mixer.music.set_volume(game_settings.get('music_volume', 0.7))
                        for sound in hitsounds.values():
                            sound.set_volume(game_settings.get('hitsound_volume', 0.3))
                    elif settings_result == 'QUIT_MENU':
                        # Quit to menu
                        pygame.mixer.music.stop()
                        if game_settings.get('fade_effects', True):
                            fade_out(screen, duration=0.7)
                        return 'RESTART'
                    elif settings_result == 'RESTART_LEVEL':
                        # Restart the current level
                        pygame.mixer.music.stop()
                        if game_settings.get('fade_effects', True):
                            fade_out(screen, duration=0.3)
                        return ('RESTART_LEVEL', level_json)
                    elif settings_result == 'QUIT':
                        # Quit game completely
                        pygame.mixer.music.stop()
                        if game_settings.get('fade_effects', True):
                            fade_out(screen, duration=0.7)
                        pygame.quit()
                        sys.exit()

                # Handle gameplay keys (WASD and Arrows) - 8 key system
                if not paused and display_time >= 3.0 and not game_over:
                    if event.key in KEY_MAPPINGS:
                        keys_pressed.add(event.key)
                        
                        # A key can map to multiple (color, box) pairs - check all of them
                        elapsed_time = time.time() - game_start_time - total_pause_duration
                        for color, box_idx in KEY_MAPPINGS[event.key]:
                            # Check all unhit notes within timing window for this color and box
                            for check_idx in range(current_event_index, len(level)):
                                if check_idx not in resolved_events:
                                    evt_time, evt_box, evt_color, evt_hitsound = level[check_idx]
                                    # Only check notes that match the pressed key's color and box
                                    if evt_color == color and evt_box == box_idx:
                                        if handle_click(color, elapsed_time, check_idx):
                                            # Add input flash (only if not game over)
                                            if not game_over:
                                                input_flashes[box_idx] = (time.time(), color)
                                            break
            
            if event.type == pygame.KEYUP:
                # Remove key from pressed set
                if event.key in KEY_MAPPINGS:
                    keys_pressed.discard(event.key)

        # Auto-miss past window
        if not paused and not game_over:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            
            # Check for game over (HP = 0 or below)
            if current_health <= 0.01 and not game_over:  # Use 0.01 to handle floating point precision
                game_over = True
                game_over_time = elapsed_time
                print(f"Game over! Health: {current_health}")
                # Start fading music immediately
                pygame.mixer.music.fadeout(3000)  # 3 second fade
                
                # Clear input flashes so boxes don't flash after game over
                input_flashes.clear()
                
                # Fade out all tiles currently on screen
                box_centers = [
                    (center_x, center_y - square_size // 2 - spacing),
                    (center_x + square_size // 2 + spacing, center_y),
                    (center_x, center_y + square_size // 2 + spacing),
                    (center_x - square_size // 2 - spacing, center_y),
                ]
                for box_idx, color, t_time, duration, evt_idx, side in approach_indicators:
                    # Calculate current position of the tile
                    approach_start_time = t_time - duration
                    progress = (elapsed_time - approach_start_time) / duration
                    progress = max(0.0, min(1.0, progress))
                    
                    travel_distance = screen_width // 2
                    target_x, target_y = box_centers[box_idx]
                    if box_idx == 0:
                        start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                        start_y = target_y
                    elif box_idx == 1:
                        start_x = target_x + travel_distance
                        start_y = target_y
                    elif box_idx == 2:
                        start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                        start_y = target_y
                    else:
                        start_x = target_x - travel_distance
                        start_y = target_y
                    
                    current_x = start_x + (target_x - start_x) * progress
                    current_y = start_y + (target_y - start_y) * progress
                    
                    # Add tile to fading list at its current position
                    fading_tiles.append((box_idx, color, current_x, current_y, elapsed_time))
                
                # Clear approach_indicators since all tiles are now fading
                approach_indicators = []
            
            while current_event_index < len(level) and elapsed_time > level[current_event_index][0] + MAX_TIMING_WINDOW:
                missed_time, missed_box, missed_color, missed_hitsound = level[current_event_index]
                if current_event_index not in resolved_events:
                    resolve_miss(current_event_index, missed_box)
                else:
                    current_event_index += 1

            if current_event_index < len(level):
                target_time, target_box, target_color, target_hitsound = level[current_event_index]

            # Maintain approach indicators - remove tiles that have been resolved or passed timing window
            approach_indicators = [
                (box_idx, color, t_time, duration, evt_idx, side)
                for box_idx, color, t_time, duration, evt_idx, side in approach_indicators
                if evt_idx not in resolved_events and elapsed_time <= t_time + MAX_TIMING_WINDOW
            ]

            existing_events = {evt_idx for _, _, _, _, evt_idx, _ in approach_indicators}
            JUDGE_DELAY_AFTER_SPAWN = 0.1

            # Use the pre-calculated constant approach duration for all tiles
            approach_duration = APPROACH_DURATION
            
            # Dynamic lookahead based on approach duration to show all visible notes
            # lookahead time = approach_duration + small buffer
            lookahead_time = approach_duration + 0.2
            lookahead = 0
            for i in range(current_event_index, len(level)):
                if level[i][0] <= elapsed_time + lookahead_time:
                    lookahead += 1
                else:
                    break
            
            # Cap lookahead for performance
            lookahead = min(lookahead, 50)
            
            lookback = 5
            start_scan = max(0, current_event_index - lookback)
            
            # Only spawn new tiles if not game over
            if not game_over:
                for i in range(start_scan, min(current_event_index + lookahead, len(level))):
                    if i not in existing_events:
                        evt_time, evt_box, evt_color, evt_hitsound = level[i]
                        # Only spawn if within approach window
                        if elapsed_time <= evt_time <= elapsed_time + approach_duration:
                            if evt_box == 0:
                                approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'left'))
                            elif evt_box == 2:
                                approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'right'))
                            else:
                                approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, None))

            # One-time shake exactly when tile reaches box (TRULY timing-driven; independent of input)
            # Don't shake boxes during game over
            if not game_over:
                while arrival_shake_index < len(level) and elapsed_time >= level[arrival_shake_index][0]:
                    t_note, box_idx, color, hs = level[arrival_shake_index]
                    if arrival_shake_index not in reached_shake_events:
                        reached_shake_events.add(arrival_shake_index)
                        trigger_box_shake(box_idx, intensity=9)
                    arrival_shake_index += 1
        
        # ===== Game over handling (HP = 0) - outside paused/game_over check so it can execute =====
        if game_over and game_over_time is not None:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            # After 2.5 seconds, return to level selector
            if (elapsed_time - game_over_time) >= 2.5:
                print("Returning to level selector after game over")
                if game_settings.get('fade_effects', True):
                    fade_out(screen, duration=0.5)
                return 'RESTART'
        
        # ===== End-of-level flow (NO freezing; let visuals keep running) =====
        # Mark end-of-level once ALL notes are resolved (hit or miss)
        if current_event_index >= len(level) and level_end_elapsed is None and not game_over:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            level_end_elapsed = elapsed_time

        # After 2s delay, fade music for 3s, then fade screen and return to selector
        if level_end_elapsed is not None and not game_over:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            if (elapsed_time - level_end_elapsed) >= POST_LEVEL_DELAY and not music_fade_started:
                pygame.mixer.music.fadeout(int(POST_LEVEL_MUSIC_FADE * 1000))
                music_fade_started = True
                music_fade_start_elapsed = elapsed_time

            if music_fade_started and (elapsed_time - music_fade_start_elapsed) >= POST_LEVEL_MUSIC_FADE:
                if game_settings.get('fade_effects', True):
                    fade_out(screen, duration=0.7)
                return 'RESTART'

        # Draw background (either gameplay bg image or white)
        if gameplay_bg_image:
            screen.blit(gameplay_bg_image, (0, 0))
        else:
            screen.fill(WHITE)

        # Draw health bar at top of screen (30% width, centered) with animations
        health_bar_width = int(screen_width * 0.3)
        health_bar_x = (screen_width - health_bar_width) // 2
        health_bar_y = 60
        health_bar_thickness = 12  # Decreased from 20
        
        # Update displayed_health: snap down immediately on loss, animate up on gain
        if current_health < displayed_health:
            # Health loss - snap immediately, no animation
            displayed_health = current_health
        elif current_health > displayed_health:
            # Health gain - smooth animation
            health_diff = current_health - displayed_health
            if abs(health_diff) > 0.01:
                displayed_health += health_diff * 0.15
            else:
                displayed_health = current_health
        # If equal, no change needed
        
        health_percentage = displayed_health / max_health
        
        # Create semi-transparent surface for health bar
        health_surface = pygame.Surface((health_bar_width, health_bar_thickness), pygame.SRCALPHA)
        
        # Background bar (dark gray, semi-transparent)
        pygame.draw.rect(health_surface, (50, 50, 50, 180), (0, 0, health_bar_width, health_bar_thickness))
        
        # Draw fading white bars showing health loss
        current_time = time.time()
        expired_bars = []
        for i, (bar_width, alpha, timestamp) in enumerate(lost_health_bars):
            time_since = current_time - timestamp
            if time_since < 0.8:  # Fade over 0.8 seconds
                fade_alpha = int(255 * (1 - time_since / 0.8))  # Keep white color, just fade alpha
                pygame.draw.rect(health_surface, (255, 255, 255, fade_alpha), (0, 0, bar_width, health_bar_thickness))
            else:
                expired_bars.append(i)
        # Remove expired bars
        for i in reversed(expired_bars):
            lost_health_bars.pop(i)
        
        # Foreground bar (colored based on health percentage, semi-transparent)
        current_bar_width = int(health_bar_width * health_percentage)
        if health_percentage > 0.7:
            health_color = (0, 255, 0, 200)  # Green
        elif health_percentage > 0.4:
            health_color = (255, 255, 0, 200)  # Yellow
        elif health_percentage > 0.2:
            health_color = (255, 165, 0, 200)  # Orange
        else:
            health_color = (255, 0, 0, 200)  # Red
        
        if current_bar_width > 0:
            pygame.draw.rect(health_surface, health_color, (0, 0, current_bar_width, health_bar_thickness))
        
        screen.blit(health_surface, (health_bar_x, health_bar_y))

        # Screen shake offset
        shake_x, shake_y = 0, 0
        if shake_time > 0:
            time_since_shake = time.time() - shake_time
            if time_since_shake < 0.15:
                decay = 1 - (time_since_shake / 0.15)
                import random
                shake_x = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
                shake_y = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
            else:
                shake_time = 0
                shake_intensity = 0
                shake_box = None

        # Draw 4 boxes
        top_shake_x = shake_x if shake_box == 0 else 0
        top_shake_y = shake_y if shake_box == 0 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + top_shake_x, center_y - square_size - spacing + top_shake_y))

        right_shake_x = shake_x if shake_box == 1 else 0
        right_shake_y = shake_y if shake_box == 1 else 0
        screen.blit(box_image_rounded, (center_x + spacing + right_shake_x, center_y - square_size // 2 + right_shake_y))

        bottom_shake_x = shake_x if shake_box == 2 else 0
        bottom_shake_y = shake_y if shake_box == 2 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + bottom_shake_x, center_y + spacing + bottom_shake_y))

        left_shake_x = shake_x if shake_box == 3 else 0
        left_shake_y = shake_y if shake_box == 3 else 0
        screen.blit(box_image_rounded, (center_x - square_size - spacing + left_shake_x, center_y - square_size // 2 + left_shake_y))

        # Use frozen time for rendering when paused
        render_time = display_time

        # Big box positions for overlays (no shake here; shake is already on base image)
        big_box_positions = [
            (center_x - square_size // 2, center_y - square_size - spacing),  # Top
            (center_x + spacing, center_y - square_size // 2),                # Right
            (center_x - square_size // 2, center_y + spacing),                # Bottom
            (center_x - square_size - spacing, center_y - square_size // 2),  # Left
        ]

        # ===== Arrival flash overlay (timing-driven; works even if you miss) =====
        # Only render arrival flashes if not game over
        if not game_over:
            # Move pointer forward past old flashes
            while arrival_flash_index < len(level) and render_time > level[arrival_flash_index][0] + arrival_flash_duration:
                arrival_flash_index += 1

            # For each box, keep the strongest flash currently active
            best_flash_alpha = [0, 0, 0, 0]
            best_flash_color = [None, None, None, None]

            j = arrival_flash_index
            # Scan forward only a small window around "now"
            while j < len(level) and level[j][0] <= render_time + arrival_flash_duration:
                t_note, box_idx, color, hs = level[j]
                dt = render_time - t_note
                if 0 <= dt <= arrival_flash_duration:
                    if dt <= arrival_flash_sustain:
                        alpha = 255
                    else:
                        # linear fade out after sustain
                        fade_t = (dt - arrival_flash_sustain) / (arrival_flash_duration - arrival_flash_sustain)
                        alpha = max(0, int(255 * (1 - fade_t)))

                    if alpha > best_flash_alpha[box_idx]:
                        best_flash_alpha[box_idx] = alpha
                        best_flash_color[box_idx] = color
                j += 1

            # Draw the flashes (move WITH the box shake so it doesn't look like the tile shakes)
            for box_idx in range(4):
                alpha = best_flash_alpha[box_idx]
                color = best_flash_color[box_idx]
                if alpha > 0 and color is not None:
                    overlay_img = box_red_rounded if color == 'red' else box_blue_rounded
                    overlay_surface = overlay_img.copy()
                    overlay_surface.set_alpha(alpha)

                    bx, by = big_box_positions[box_idx]

                    # If this is the currently-shaken box, apply the same shake offset
                    if shake_box == box_idx:
                        bx += shake_x
                        by += shake_y

                    screen.blit(overlay_surface, (bx, by))

        # ===== Input flash overlay (shows taps even when nothing is hit) =====
        input_flash_duration = 0.25
        current_time = time.time()
        
        # Clean up old input flashes and render active ones
        expired_boxes = []
        for box_idx, (flash_time, flash_color) in input_flashes.items():
            dt = current_time - flash_time
            if dt > input_flash_duration:
                expired_boxes.append(box_idx)
            else:
                # Calculate fade alpha
                if dt <= 0.05:  # Quick bright flash
                    alpha = 255
                else:
                    # Fade out
                    fade_t = (dt - 0.05) / (input_flash_duration - 0.05)
                    alpha = max(0, int(255 * (1 - fade_t)))
                
                if alpha > 0:
                    overlay_img = box_red_rounded if flash_color == 'red' else box_blue_rounded
                    overlay_surface = overlay_img.copy()
                    overlay_surface.set_alpha(alpha)
                    
                    bx, by = big_box_positions[box_idx]
                    
                    # Apply shake if this is the currently-shaken box
                    if shake_box == box_idx:
                        bx += shake_x
                        by += shake_y
                    
                    screen.blit(overlay_surface, (bx, by))
        
        # Remove expired flashes
        for box_idx in expired_boxes:
            del input_flashes[box_idx]


        # Edge flash indicators
        edge_flash_height = square_size // 2 + spacing - 10
        edge_flash_duration = 0.25
        edge_offset = 0

        # Only render edge flashes if not game over
        if not game_over:
            for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
                approach_start_time = target_time - approach_duration
                time_until_start = approach_start_time - render_time

                if 0 <= time_until_start <= edge_flash_duration:
                    flash_progress = 1 - (time_until_start / edge_flash_duration)

                    if flash_progress < 0.3:
                        alpha = int(255 * (flash_progress / 0.3))
                    else:
                        alpha = int(255 * (1 - (flash_progress - 0.3) / 0.7))

                    box_centers = [
                        (center_x, center_y - square_size // 2 - spacing),
                        (center_x + square_size // 2 + spacing, center_y),
                        (center_x, center_y + square_size // 2 + spacing),
                        (center_x - square_size // 2 - spacing, center_y),
                    ]

                    target_x, target_y = box_centers[box_idx]

                    if box_idx == 0:
                        gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                        edge_y = target_y - edge_flash_height // 2
                        is_left = (side == 'left')
                    elif box_idx == 1:
                        gradient_x = screen_width - edge_offset
                        edge_y = target_y - edge_flash_height // 2
                        is_left = False
                    elif box_idx == 2:
                        gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                        edge_y = target_y - edge_flash_height // 2
                        is_left = (side == 'left')
                    else:
                        gradient_x = edge_offset
                        edge_y = target_y - edge_flash_height // 2
                        is_left = True

                    flash_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
                    gradient_length = 175
                    max_gradient_alpha = 85

                    gradient_surface = pygame.Surface((gradient_length, edge_flash_height), pygame.SRCALPHA)
                    for i in range(gradient_length):
                        if is_left:
                            gradient_alpha = int(max_gradient_alpha * (1 - i / gradient_length) * (alpha / 255))
                        else:
                            gradient_alpha = int(max_gradient_alpha * (i / gradient_length) * (alpha / 255))
                        gradient_color = (*flash_color, gradient_alpha)
                        pygame.draw.rect(gradient_surface, gradient_color, (i, 0, 1, edge_flash_height))

                    final_gradient_x = gradient_x if is_left else gradient_x - gradient_length
                    screen.blit(gradient_surface, (int(final_gradient_x), int(edge_y)))

        # Approach indicators
        indicator_size = 65
        for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
            approach_start_time = target_time - approach_duration
            progress = (render_time - approach_start_time) / approach_duration
            progress = max(0.0, min(1.0, progress))

            box_centers = [
                (center_x, center_y - square_size // 2 - spacing),
                (center_x + square_size // 2 + spacing, center_y),
                (center_x, center_y + square_size // 2 + spacing),
                (center_x - square_size // 2 - spacing, center_y),
            ]

            travel_distance = screen_width // 2
            target_x, target_y = box_centers[box_idx]
            if box_idx == 0:
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            elif box_idx == 1:
                start_x = target_x + travel_distance
                start_y = target_y
            elif box_idx == 2:
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            else:
                start_x = target_x - travel_distance
                start_y = target_y

            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress

            # Tiles start fading when they reach target (progress >= 1.0)
            if progress >= 1.0 and event_idx not in resolved_events:
                # Tile has reached the box - start fading
                time_since_arrival = render_time - target_time
                fade_duration_here = 0.15
                if time_since_arrival < fade_duration_here:
                    fade_progress = time_since_arrival / fade_duration_here
                    alpha = int(245 * (1 - fade_progress))
                else:
                    alpha = 0  # Fully faded
            else:
                # Tile is still traveling - normal fade-in
                if progress < 0.15:
                    alpha = int(245 * (progress / 0.15))
                else:
                    alpha = 245
            
            if alpha > 0:
                indicator_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
                indicator_surface = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
                # Draw black border first
                pygame.draw.rect(indicator_surface, (0, 0, 0, alpha), (0, 0, indicator_size, indicator_size), 0, 8)
                # Draw colored fill slightly smaller to create border effect
                pygame.draw.rect(indicator_surface, (*indicator_color, alpha), (3, 3, indicator_size - 6, indicator_size - 6), 0, 6)
                screen.blit(indicator_surface, (int(current_x - indicator_size // 2), int(current_y - indicator_size // 2)))

        # Draw fading tiles (missed notes)
        fade_duration = 0.15  # 0.15 seconds fade
        active_fading_tiles = []
        for box_idx, color, x, y, fade_start_time in fading_tiles:
            time_since_fade = elapsed_time - fade_start_time
            if time_since_fade < fade_duration:
                # Calculate fade alpha (245 -> 0)
                fade_progress = time_since_fade / fade_duration
                alpha = int(245 * (1 - fade_progress))
                
                indicator_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
                indicator_surface = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
                # Draw black border first
                pygame.draw.rect(indicator_surface, (0, 0, 0, alpha), (0, 0, indicator_size, indicator_size), 0, 8)
                # Draw colored fill slightly smaller to create border effect
                pygame.draw.rect(indicator_surface, (*indicator_color, alpha), (3, 3, indicator_size - 6, indicator_size - 6), 0, 6)
                screen.blit(indicator_surface, (int(x - indicator_size // 2), int(y - indicator_size // 2)))
                active_fading_tiles.append((box_idx, color, x, y, fade_start_time))
        fading_tiles = active_fading_tiles

        # ===== RENDER PARTICLE EFFECTS (drawn on top of boxes) =====
        current_time = time.time()
        particle_lifetime = 0.6
        
        # Update and render particles
        active_particles = []
        for px, py, vx, vy, color, size, birth_time in particles:
            age = current_time - birth_time
            if age < particle_lifetime:
                # Update position
                new_px = px + vx * age
                new_py = py + vy * age + 200 * age * age  # Gravity
                
                # Calculate alpha fade
                alpha = int(255 * (1 - age / particle_lifetime))
                
                # Draw particle
                if alpha > 0:
                    particle_surface = pygame.Surface((int(size * 2), int(size * 2)), pygame.SRCALPHA)
                    pygame.draw.circle(particle_surface, (*color, alpha), (int(size), int(size)), int(size))
                    screen.blit(particle_surface, (int(new_px - size), int(new_py - size)))
                    active_particles.append((px, py, vx, vy, color, size, birth_time))
        particles = active_particles
        
        # ===== RENDER HIT GLOW EFFECTS =====
        glow_duration = 0.35
        active_glows = []
        for glow_box_idx, glow_start_time, intensity in hit_glows:
            glow_age = current_time - glow_start_time
            if glow_age < glow_duration:
                # Calculate glow properties
                progress = glow_age / glow_duration
                max_radius = 80 * intensity
                current_radius = max_radius * progress
                alpha = int(180 * (1 - progress) * intensity)
                
                if alpha > 0:
                    # Get box center
                    box_centers = [
                        (center_x, center_y - square_size // 2 - spacing),
                        (center_x + square_size // 2 + spacing, center_y),
                        (center_x, center_y + square_size // 2 + spacing),
                        (center_x - square_size // 2 - spacing, center_y),
                    ]
                    glow_x, glow_y = box_centers[glow_box_idx]
                    
                    # Apply shake offset if this box is shaking
                    if shake_box == glow_box_idx:
                        glow_x += shake_x
                        glow_y += shake_y
                    
                    # Draw radial glow (multiple circles for soft glow effect)
                    for i in range(3):
                        radius = int(current_radius - i * 10)
                        if radius > 0:
                            glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                            layer_alpha = max(0, min(255, int(alpha / (i + 1))))
                            pygame.draw.circle(glow_surface, (255, 255, 255, layer_alpha), (radius, radius), radius)
                            screen.blit(glow_surface, (int(glow_x - radius), int(glow_y - radius)))
                    
                    active_glows.append((glow_box_idx, glow_start_time, intensity))
        hit_glows = active_glows
        
        # ===== RENDER IMPACT WAVES =====
        wave_duration = 0.4
        active_waves = []
        for wave_x, wave_y, wave_start_time, wave_color in impact_waves:
            wave_age = current_time - wave_start_time
            if wave_age < wave_duration:
                progress = wave_age / wave_duration
                wave_radius = int(50 + progress * 70)
                wave_alpha = int(200 * (1 - progress))
                wave_thickness = max(1, int(4 * (1 - progress)))
                
                if wave_alpha > 0:
                    wave_surface = pygame.Surface((wave_radius * 2 + 10, wave_radius * 2 + 10), pygame.SRCALPHA)
                    pygame.draw.circle(wave_surface, (*wave_color, wave_alpha), 
                                     (wave_radius + 5, wave_radius + 5), wave_radius, wave_thickness)
                    screen.blit(wave_surface, (int(wave_x - wave_radius - 5), int(wave_y - wave_radius - 5)))
                    active_waves.append((wave_x, wave_y, wave_start_time, wave_color))
        impact_waves = active_waves

        # Judgments
        active_judgments = []
        for judgment_text, jx, jy, start_time, box_idx, side in judgment_displays:
            time_elapsed = current_time - start_time
            fade_duration = 0.4
            if time_elapsed < fade_duration:
                alpha = int(255 * (1 - time_elapsed / fade_duration))
                offset_move = time_elapsed * 20

                if box_idx == 0:
                    display_x = jx
                    display_y = jy - 80 - offset_move
                elif box_idx == 1:
                    display_x = jx
                    display_y = jy - 80 - offset_move
                elif box_idx == 2:
                    display_x = jx
                    display_y = jy + 100 - offset_move
                else:
                    display_x = jx
                    display_y = jy + 100 - offset_move

                judgment_surface = font_judgment.render(judgment_text, True, WHITE)
                judgment_surface.set_alpha(alpha)
                text_rect = judgment_surface.get_rect(center=(int(display_x), int(display_y)))
                screen.blit(judgment_surface, text_rect)
                active_judgments.append((judgment_text, jx, jy, start_time, box_idx, side))
        judgment_displays = active_judgments

        # Combo
        combo_text_str = f"{combo}x"
        combo_surface = font_combo.render(combo_text_str, True, WHITE)

        if combo > 0:
            time_since_pop = time.time() - combo_pop_time
            if time_since_pop < combo_animation_duration:
                anim_progress = time_since_pop / combo_animation_duration
                ease = 1 - (1 - anim_progress) ** 2
                scale = 1.0 + (0.3 * (1 - abs(anim_progress * 2 - 1)))
                scaled_width = int(combo_surface.get_width() * scale)
                scaled_height = int(combo_surface.get_height() * scale)
                combo_surface = pygame.transform.scale(combo_surface, (scaled_width, scaled_height))
                shake_angle = (1 - ease) * 3 * (1 if combo % 2 == 0 else -1)
                rotation_angle = 0 + shake_angle
            else:
                rotation_angle = 0
        else:
            rotation_angle = 0

        rotated_combo = pygame.transform.rotate(combo_surface, rotation_angle)
        combo_rect = rotated_combo.get_rect(bottomleft=(35, screen_height - 155))
        screen.blit(rotated_combo, combo_rect)

        # Metadata + image
        stats_start_y = 20
        right_margin = 20

        if 'meta' in level_data and any(k in level_data['meta'] for k in ['title', 'artist', 'creator', 'version']):
            meta = level_data['meta']
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown')
            creator = meta.get('creator', 'Unknown')
            version = meta.get('version', 'Unknown')
            
            # Determine difficulty color based on version name (matching level selector colors)
            version_lower = version.lower()
            if 'easy' in version_lower or 'beginner' in version_lower:
                diff_color = (100, 200, 255)  # Light blue
            elif 'medium' in version_lower or 'platter' in version_lower:
                diff_color = (150, 220, 150)  # Medium light green
            elif 'normal' in version_lower or 'basic' in version_lower:
                diff_color = (100, 255, 100)  # Green
            elif 'hard' in version_lower or 'advanced' in version_lower:
                diff_color = (255, 200, 100)  # Orange
            elif 'expert' in version_lower or 'insane' in version_lower:
                diff_color = (255, 100, 100)  # Red
            elif 'extra' in version_lower or 'challenge' in version_lower or 'master' in version_lower:
                diff_color = (200, 100, 255)  # Purple
            else:
                diff_color = (200, 200, 200)  # Gray (default)

            metadata_lines = [
                (f"{title} - {artist}", (255, 255, 255)),
                (f"[{version}] by {creator}", diff_color)
            ]

            for i, (line, color) in enumerate(metadata_lines):
                meta_text = font_metadata.render(line, True, color)
                meta_rect = meta_text.get_rect(right=screen_width - right_margin, top=stats_start_y + i * 25)
                screen.blit(meta_text, meta_rect)
            
            stats_start_y += len(metadata_lines) * 25 + 5
        
        # Autoplay indicator below title/charter
        if autoplay_enabled:
            autoplay_text = font_metadata.render("AUTOPLAY", True, (255, 100, 100))
            autoplay_rect = autoplay_text.get_rect(right=screen_width - right_margin, top=stats_start_y)
            screen.blit(autoplay_text, autoplay_rect)
            stats_start_y += 30

            stats_start_y += len(metadata_lines) * 25 + 10

        # Stats
        total_possible = total_notes * 500  # Max score is 500 (fantastic)
        accuracy = (score / total_possible * 100) if total_possible > 0 else 100.0
        completion = (current_event_index / len(level) * 100) if len(level) > 0 else 0

        stats_data = [
            (f"{score}", "Score"),
            (f"{accuracy:.1f}%", "Accuracy"),
            (f"{completion:.1f}%", "Progress")
        ]

        left_margin = 20
        stats_bottom_y = screen_height - 20

        for i, (number, label) in enumerate(reversed(stats_data)):
            y_pos = stats_bottom_y - (i + 1) * 40
            label_text = font_stats.render(label, True, WHITE)
            label_rect = label_text.get_rect(left=left_margin, top=y_pos)
            screen.blit(label_text, label_rect)

            number_text = font_stats.render(number, True, WHITE)
            number_rect = number_text.get_rect(left=left_margin + 140, top=y_pos)
            screen.blit(number_text, number_rect)

        # Dots
        dot_size = 35
        
        # Determine which boxes have active keys pressed (from 8-key system)
        active_boxes = set()
        for key in keys_pressed:
            if key in KEY_MAPPINGS:
                # A key can map to multiple (color, box) pairs
                for color, box_idx in KEY_MAPPINGS[key]:
                    active_boxes.add(box_idx)
        
        # Detect newly activated dots and trigger animations for all of them
        newly_active = active_boxes - last_active_dots
        for dot_idx in newly_active:
            current_time_local = time.time()
            dot_pulse_times[dot_idx] = current_time_local
            dot_switch_ripples.append((dot_idx, current_time_local))
        
        # Update last active dots
        last_active_dots = active_boxes.copy()
        
        # Draw dots FIRST (underneath everything)
        for i, (dot_x, dot_y) in enumerate(dot_positions):
            is_active = i in active_boxes
            current_dot = dot2_image if is_active else dot_image
            # Draw black border circle first
            pygame.draw.circle(screen, (0, 0, 0), (int(dot_x), int(dot_y)), dot_size // 2 + 2)
            # Then draw the dot image
            screen.blit(current_dot, (int(dot_x - dot_size // 2), int(dot_y - dot_size // 2)))
        
        # Render pulse animation on top of dots
        for i, (dot_x, dot_y) in enumerate(dot_positions):
            is_active = i in active_boxes
            
            # Check if this dot has an active pulse animation
            if i in dot_pulse_times:
                switch_age = current_time - dot_pulse_times[i]
                pulse_duration = 0.2
                if switch_age < pulse_duration:
                    pulse_progress = switch_age / pulse_duration
                    # Ease-out cubic for smooth deceleration
                    ease = 1 - pow(1 - pulse_progress, 3)
                    scale = 1.0 + (0.3 * (1 - ease))
                    # Draw a transparent glow circle for pulse effect
                    pulse_radius = int(dot_size // 2 * scale)
                    pulse_alpha = int(150 * (1 - ease))
                    if pulse_alpha > 0:
                        pulse_surface = pygame.Surface((pulse_radius * 2, pulse_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(pulse_surface, (255, 100, 100, pulse_alpha), 
                                         (pulse_radius, pulse_radius), pulse_radius)
                        screen.blit(pulse_surface, (int(dot_x - pulse_radius), int(dot_y - pulse_radius)))
                else:
                    # Clean up finished pulse
                    del dot_pulse_times[i]
        
        # Render dot switch ripples (ON TOP of everything)
        ripple_duration = 0.3
        active_ripples = []
        for ripple_idx, ripple_start_time in dot_switch_ripples:
            ripple_age = current_time - ripple_start_time
            if ripple_age < ripple_duration:
                progress = ripple_age / ripple_duration
                ripple_radius = int(15 + progress * 20)
                ripple_alpha = int(180 * (1 - progress))
                
                if ripple_alpha > 0:
                    ripple_x, ripple_y = dot_positions[ripple_idx]
                    ripple_surface = pygame.Surface((ripple_radius * 2 + 10, ripple_radius * 2 + 10), pygame.SRCALPHA)
                    pygame.draw.circle(ripple_surface, (255, 50, 50, ripple_alpha),
                                     (ripple_radius + 5, ripple_radius + 5), ripple_radius, 3)
                    screen.blit(ripple_surface, (int(ripple_x - ripple_radius - 5), int(ripple_y - ripple_radius - 5)))
                    active_ripples.append((ripple_idx, ripple_start_time))
        dot_switch_ripples = active_ripples

        # Countdown - positioned above play area, below HP bar
        if display_time < 3.0:
            if display_time < 1.0:
                countdown_text = "3"
            elif display_time < 2.0:
                countdown_text = "2"
            else:
                countdown_text = "1"

            flash_cycle = (display_time % 1.0)
            if flash_cycle < 0.15:
                alpha = int(255 * (flash_cycle / 0.15))
            else:
                alpha = int(255 * (1 - (flash_cycle - 0.15) / 0.85))

            countdown_surface = font_countdown.render(countdown_text, True, (255, 255, 255))
            countdown_surface.set_alpha(alpha)
            # Position below health bar (health_bar_y + health_bar_thickness + margin)
            countdown_y = health_bar_y + health_bar_thickness + 80
            countdown_rect = countdown_surface.get_rect(center=(center_x, countdown_y))
            screen.blit(countdown_surface, countdown_rect)

        # Fade-in overlay
        if fade_in_alpha > 0:
            fade_overlay = pygame.Surface((screen_width, screen_height))
            fade_overlay.fill((0, 0, 0))
            fade_overlay.set_alpha(fade_in_alpha)
            screen.blit(fade_overlay, (0, 0))

        # ===== RENDER SCREEN FLASH (for perfect hits) - render last so it's on top =====
        if screen_flash_alpha > 0:
            flash_age = current_time - screen_flash_time
            flash_duration = 0.15
            if flash_age < flash_duration:
                current_flash_alpha = int(screen_flash_alpha * (1 - flash_age / flash_duration))
                if current_flash_alpha > 0:
                    flash_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    flash_surface.fill((255, 255, 255, current_flash_alpha))
                    screen.blit(flash_surface, (0, 0))
            else:
                screen_flash_alpha = 0

        pygame.display.flip()
        clock.tick(60)

    pygame.mixer.music.stop()
    return None

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # No longer initializing OSU levels - using song packs only
    # initialize_levels_from_osz()

    preloaded_metadata = show_loading_screen()

    if preloaded_metadata is None:
        preloaded_metadata = []  # Empty list is fine now

    returning = False
    last_level = None
    while True:
        result = main(level_json=last_level, returning_from_game=returning, preloaded_metadata=preloaded_metadata)
        if result is None:
            break
        elif isinstance(result, tuple) and result[0] == 'RESTART_LEVEL':
            # Restart the same level
            last_level = result[1]
            returning = True
        elif result == 'RESTART':
            # Go back to level selector
            last_level = None
            returning = True
        else:
            break

    pygame.display.quit()
    pygame.quit()
    sys.exit()
