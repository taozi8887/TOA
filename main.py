import pygame
import pygame.gfxdraw
import sys
import os
import time
import math
import json
import subprocess
import threading
from unzip import read_osz_file
from osu_to_level import create_level_json
try:
    import requests
    from auto_updater import AutoUpdater
    AUTO_UPDATE_AVAILABLE = True
except ImportError:
    AUTO_UPDATE_AVAILABLE = False
    print("Auto-update not available: requests library not installed")

__version__ = "0.6.4"

# Settings management
class Settings:
    """Manages game settings with local storage"""
    
    DEFAULT_SETTINGS = {
        'music_volume': 0.7,
        'hitsound_volume': 0.3,
        'hitsounds_enabled': True,
        'scroll_speed': 75,
        'fade_effects': True,
        'keybinds': {
            'top': pygame.K_w,
            'right': pygame.K_d,
            'bottom': pygame.K_s,
            'left': pygame.K_a
        },
        'mouse_binds': {
            'red': 1,  # Left click
            'blue': 3  # Right click
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

    font_title = pygame.font.Font(None, 72)
    font_status = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)

    # Start with black screen
    screen.fill(BLACK)
    pygame.display.flip()

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

    # Verify file integrity (protect against tampering) with visual feedback
    if AUTO_UPDATE_AVAILABLE and getattr(sys, 'frozen', False):
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
                code_files = ['main.py', 'osu_to_level.py', 'unzip.py', 'auto_updater.py', 'batch_process_osz.py', 'launcher.py']
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

    # Get available level files
    levels_dir = "levels"
    level_files = []
    try:
        levels_path = resource_path(levels_dir)
        if os.path.exists(levels_path):
            level_files = [f for f in os.listdir(levels_path) if f.endswith('.json')]
            level_files.sort()
    except Exception as e:
        print(f"Error: Could not read levels directory: {levels_dir}")
        print(f"Full error: {e}")
        print(f"Tried path: {resource_path(levels_dir)}")
        return None

    if not level_files:
        print("Error: No level files found!")
        print(f"Checked directory: {resource_path(levels_dir)}")
        print("Make sure .osz files are in assets/osz/ directory")
        return None

    # Load metadata and background images for each level with progress bar
    level_metadata = []
    total_files = len(level_files)

    for idx, level_file in enumerate(level_files):
        # Update progress
        progress = (idx + 1) / total_files

        # Draw loading screen with progress
        screen.fill(BLACK)

        title_text = font_title.render("TOA", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        screen.blit(title_text, title_rect)

        status_text = font_status.render(f"Loading levels... {idx + 1}/{total_files}", True, WHITE)
        status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
        screen.blit(status_text, status_rect)

        # Draw progress bar
        bar_width = 400
        bar_height = 20
        bar_x = window_width // 2 - bar_width // 2
        bar_y = window_height // 2 + 100

        # Background bar
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
        # Progress bar
        filled_width = int(bar_width * progress)
        if filled_width > 0:
            pygame.draw.rect(screen, GREEN, (bar_x, bar_y, filled_width, bar_height), border_radius=10)

        pygame.display.flip()
        clock.tick(60)

        # Load level metadata
        try:
            with open(resource_path(os.path.join(levels_dir, level_file)), 'r') as f:
                data = json.load(f)
                title = data.get('meta', {}).get('title', 'Unknown')
                version = data.get('meta', {}).get('version', 'Unknown')
                artist = data.get('meta', {}).get('artist', 'Unknown')
                creator = data.get('meta', {}).get('creator', 'Unknown')

                # Find background image from beatmap directory
                beatmap_name = level_file.replace('.json', '').split('_')[0]
                beatmap_dir = f"beatmaps/{beatmap_name}"
                bg_image = None

                try:
                    # Look for image files in beatmap directory
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
            # If can't read metadata, use filename
            level_metadata.append((level_file, level_file.replace('.json', ''), '', 'Unknown', 'Unknown', None))

    # Show complete message briefly
    screen.fill(BLACK)
    title_text = font_title.render("TOA", True, WHITE)
    title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
    screen.blit(title_text, title_rect)

    status_text = font_status.render("Ready!", True, WHITE)
    status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
    screen.blit(status_text, status_rect)

    # Draw full progress bar
    bar_width = 400
    bar_height = 20
    bar_x = window_width // 2 - bar_width // 2
    bar_y = window_height // 2 + 100
    pygame.draw.rect(screen, GREEN, (bar_x, bar_y, bar_width, bar_height), border_radius=10)

    pygame.display.flip()
    time.sleep(0.3)  # Brief pause to show completion

    # Fade out loading screen
    if game_settings.get('fade_effects', True):
        fade_out(screen, duration=0.5)

    # Keep screen black for transition to level selector
    screen.fill((0, 0, 0))
    pygame.display.flip()

    return level_metadata

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

    font_title = pygame.font.Font(None, 48)
    font_item_title = pygame.font.Font(None, 32)
    font_item_version = pygame.font.Font(None, 22)
    font_hint = pygame.font.Font(None, 24)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)

    # Scrolling setup - pixel-based smooth scrolling
    scroll_offset = 0.0  # Current scroll position in pixels
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
                    scroll_offset = max(0, scroll_offset - scroll_speed)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + scroll_speed)

            if event.type == pygame.MOUSEWHEEL:
                scroll_offset = max(0, min(max_scroll, scroll_offset - event.y * scroll_speed))

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

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False

        # Handle continuous arrow key scrolling (when held down)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            scroll_offset = max(0, scroll_offset - scroll_speed / 6)  # Slower for held keys
        if keys[pygame.K_DOWN]:
            scroll_offset = min(max_scroll, scroll_offset + scroll_speed / 6)

        # Handle scrollbar dragging
        if scrollbar_dragging and total_content_height > available_height:
            scrollbar_track_height = list_end_y - list_start_y
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
            drag_delta_y = mouse_y - drag_start_y
            scroll_delta = (drag_delta_y / (scrollbar_track_height - thumb_height)) * max_scroll if max_scroll > 0 else 0
            scroll_offset = max(0, min(max_scroll, drag_start_scroll + scroll_delta))

        # Rendering
        screen.fill(WHITE)

        # Draw title
        title_text = font_title.render("Select a Level", True, BLACK)
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

            # Check if mouse is hovering
            is_hovered = item_rect.collidepoint(mouse_pos)
            if is_hovered:
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

        # Set cursor based on whether hovering over any item
        if hovered_index is not None:
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

            item_rect = pygame.Rect(50, int(item_y), window_width - 100, item_height - 5)

            # Get hover animation progress with ease-in curve
            hover_progress = hover_animations.get(i, 0.0)
            eased_progress = hover_progress * hover_progress  # Quadratic ease-in

            # Get metadata
            level_file, title, version, artist, creator, bg_image = level_metadata[i]

            # Draw background image if available (cover + center positioning)
            if bg_image is not None:
                # Calculate scaling to cover the rect while maintaining aspect ratio
                bg_width, bg_height = bg_image.get_size()
                rect_width, rect_height = item_rect.width, item_rect.height

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

                screen.blit(bg_surface, item_rect.topleft)

                # Draw black to transparent gradient overlay (left to right)
                gradient_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                for x in range(rect_width):
                    # Gradient from black (left) to transparent (right)
                    alpha = int(200 * (1 - x / rect_width))  # 200 max opacity at left, 0 at right
                    pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (x, 0), (x, rect_height))

                screen.blit(gradient_surface, item_rect.topleft)

                # Draw hover overlay with animation (dark overlay)
                if eased_progress > 0.0:
                    hover_alpha = int(100 * eased_progress)
                    hover_overlay = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_overlay, (0, 0, 0, hover_alpha), (0, 0, rect_width, rect_height), border_radius=15)
                    screen.blit(hover_overlay, item_rect.topleft)
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
                pygame.draw.rect(screen, item_color, item_rect, border_radius=15)

            # Draw title (larger)
            total_text_height = 40
            if version:
                total_text_height += 30
            if artist and artist != 'Unknown':
                total_text_height += 25
            if creator and creator != 'Unknown':
                total_text_height += 25

            text_start_y = item_rect.top + (item_rect.height - total_text_height) // 2

            text_color = (255, 255, 255) if bg_image is not None else (0, 0, 0)
            title_text = font_item_title.render(title, True, text_color)
            title_rect = title_text.get_rect(left=item_rect.left + 30, top=text_start_y)
            screen.blit(title_text, title_rect)

            current_y = text_start_y + 40

            if version:
                version_text = font_item_version.render(f"[{version}]", True, text_color)
                version_rect = version_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(version_text, version_rect)
                current_y += 30

            if artist and artist != 'Unknown':
                artist_text = font_hint.render(f"Artist: {artist}", True, text_color)
                artist_rect = artist_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(artist_text, artist_rect)
                current_y += 25

            if creator and creator != 'Unknown':
                creator_text = font_hint.render(f"Mapped by: {creator}", True, text_color)
                creator_rect = creator_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(creator_text, creator_rect)

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
        font_update_test = pygame.font.Font(None, 120)
        update_test_text = font_update_test.render("UPDATE TEST", True, (0, 100, 255))
        update_test_rect = update_test_text.get_rect(center=(window_width // 2, window_height // 2))
        screen.blit(update_test_text, update_test_rect)

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

def show_quit_confirmation():
    """Show yes/no confirmation for quitting game
    
    Returns:
        True if user confirms quit, False otherwise
    """
    screen = pygame.display.get_surface()
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    # Save current screen
    saved_screen = screen.copy()
    
    font_large = pygame.font.Font(None, 64)
    font_button = pygame.font.Font(None, 48)
    
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
        title_text = font_large.render("Quit Game?", True, BLACK)
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
    
    font_title = pygame.font.Font(None, 64)
    font_label = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)
    font_button = pygame.font.Font(None, 32)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    DARK_GRAY = (100, 100, 100)
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
    fade_effects = game_settings.get('fade_effects', True)
    
    # Keybind remapping state
    waiting_for_key = None  # Which keybind we're waiting to remap
    waiting_for_mouse = None  # Which mouse button we're waiting to remap
    
    # Slider dragging state
    dragging_slider = None
    
    running = True
    result = None
    
    def draw_slider(x, y, width, height, value, min_val, max_val, label):
        """Draw a horizontal slider"""
        # Label
        label_surface = font_label.render(label, True, BLACK)
        screen.blit(label_surface, (x, y - 35))
        
        # Track
        track_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, GRAY, track_rect, border_radius=4)
        
        # Filled portion
        filled_width = int((value - min_val) / (max_val - min_val) * width)
        filled_rect = pygame.Rect(x, y, filled_width, height)
        pygame.draw.rect(screen, GREEN, filled_rect, border_radius=4)
        
        # Knob
        knob_x = x + filled_width
        knob_y = y + height // 2
        pygame.draw.circle(screen, WHITE, (knob_x, knob_y), knob_radius)
        pygame.draw.circle(screen, BLACK, (knob_x, knob_y), knob_radius, 2)
        
        # Value display
        value_text = f"{int(value * 100) if min_val == 0 and max_val == 1 else int(value)}"
        if min_val == 0 and max_val == 1:
            value_text += "%"
        value_surface = font_small.render(value_text, True, BLACK)
        screen.blit(value_surface, (x + width + 15, y - 8))
        
        return track_rect
    
    def draw_toggle(x, y, enabled, label):
        """Draw a toggle switch"""
        toggle_width = 60
        toggle_height = 30
        
        # Label
        label_surface = font_label.render(label, True, BLACK)
        screen.blit(label_surface, (x, y - 35))
        
        # Toggle background
        bg_color = GREEN if enabled else GRAY
        toggle_rect = pygame.Rect(x, y, toggle_width, toggle_height)
        pygame.draw.rect(screen, bg_color, toggle_rect, border_radius=15)
        
        # Toggle knob
        knob_x = x + toggle_width - 18 if enabled else x + 18
        knob_y = y + toggle_height // 2
        pygame.draw.circle(screen, WHITE, (knob_x, knob_y), 12)
        pygame.draw.circle(screen, BLACK, (knob_x, knob_y), 12, 2)
        
        return toggle_rect
    
    def draw_button(x, y, width, height, text, color=GRAY):
        """Draw a button and return its rect"""
        button_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, color, button_rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, button_rect, 2, border_radius=8)
        
        text_surface = font_button.render(text, True, BLACK)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        
        return button_rect
    
    def get_key_name(key_code):
        """Get readable name for pygame key code"""
        return pygame.key.name(key_code).upper()
    
    def get_mouse_name(button):
        """Get readable name for mouse button or key"""
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
                    # Check if key is already bound
                    keybinds = game_settings.get('keybinds')
                    mouse_binds = game_settings.get('mouse_binds')
                    
                    # Check against other keybinds (excluding the one being remapped)
                    is_duplicate = False
                    for bind_name, bind_key in keybinds.items():
                        if bind_name != waiting_for_key and bind_key == event.key:
                            is_duplicate = True
                            break
                    
                    # Check against mouse binds
                    if event.key in mouse_binds.values():
                        is_duplicate = True
                    
                    if not is_duplicate:
                        keybinds[waiting_for_key] = event.key
                        game_settings.set('keybinds', keybinds)
                        waiting_for_key = None
                elif waiting_for_mouse:
                    # Check if key/button is already bound
                    keybinds = game_settings.get('keybinds')
                    mouse_binds = game_settings.get('mouse_binds')
                    
                    is_duplicate = False
                    # Check against keybinds
                    if event.key in keybinds.values():
                        is_duplicate = True
                    
                    # Check against other mouse binds (excluding the one being remapped)
                    for bind_name, bind_val in mouse_binds.items():
                        if bind_name != waiting_for_mouse and bind_val == event.key:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        mouse_binds[waiting_for_mouse] = event.key
                        game_settings.set('mouse_binds', mouse_binds)
                        waiting_for_mouse = None
                elif event.key == pygame.K_ESCAPE:
                    if from_game:
                        result = 'BACK'
                    elif from_selector:
                        result = 'BACK'
                    else:
                        result = 'QUIT'
                    running = False
                    
            if event.type == pygame.MOUSEBUTTONDOWN:
                if waiting_for_mouse:
                    # Check if button is already bound
                    keybinds = game_settings.get('keybinds')
                    mouse_binds = game_settings.get('mouse_binds')
                    
                    is_duplicate = False
                    # Check against keybinds
                    if event.button in keybinds.values():
                        is_duplicate = True
                    
                    # Check against other mouse binds (excluding the one being remapped)
                    for bind_name, bind_val in mouse_binds.items():
                        if bind_name != waiting_for_mouse and bind_val == event.button:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        mouse_binds[waiting_for_mouse] = event.button
                        game_settings.set('mouse_binds', mouse_binds)
                        waiting_for_mouse = None
                else:
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
                        if show_quit_confirmation():
                            result = 'QUIT_MENU'
                            running = False
                    elif quit_game_rect and quit_game_rect.collidepoint(mouse_pos):
                        # Show confirmation for quit game
                        if show_quit_confirmation():
                            result = 'QUIT'
                            running = False
                    # Check keybind buttons
                    elif keybind_top_rect.collidepoint(mouse_pos):
                        waiting_for_key = 'top'
                    elif keybind_right_rect.collidepoint(mouse_pos):
                        waiting_for_key = 'right'
                    elif keybind_bottom_rect.collidepoint(mouse_pos):
                        waiting_for_key = 'bottom'
                    elif keybind_left_rect.collidepoint(mouse_pos):
                        waiting_for_key = 'left'
                    elif mouse_red_rect.collidepoint(mouse_pos):
                        waiting_for_mouse = 'red'
                    elif mouse_blue_rect.collidepoint(mouse_pos):
                        waiting_for_mouse = 'blue'
                    elif reset_keybinds_rect.collidepoint(mouse_pos):
                        # Reset all keybinds to default
                        default_keybinds = {
                            'top': pygame.K_w,
                            'right': pygame.K_d,
                            'bottom': pygame.K_s,
                            'left': pygame.K_a
                        }
                        default_mouse_binds = {
                            'red': 1,
                            'blue': 3
                        }
                        game_settings.set('keybinds', default_keybinds)
                        game_settings.set('mouse_binds', default_mouse_binds)
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
        screen.fill(WHITE)
        
        # Title
        title_text = font_title.render("Settings", True, BLACK)
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
        mouse_binds = game_settings.get('mouse_binds')
        
        y_offset = 140
        keybind_label = font_label.render("Keybinds", True, BLACK)
        screen.blit(keybind_label, (right_col_x, y_offset - 35))
        
        button_width = 200
        button_height = 40
        button_spacing = 50
        
        # Top key
        if waiting_for_key == 'top':
            key_text = "Press a key..."
        else:
            key_text = f"Top: {get_key_name(keybinds['top'])}"
        color = BLUE if waiting_for_key == 'top' else GRAY
        keybind_top_rect = draw_button(right_col_x, y_offset, button_width, button_height, 
                                       key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'right':
            key_text = "Press a key..."
        else:
            key_text = f"Right: {get_key_name(keybinds['right'])}"
        color = BLUE if waiting_for_key == 'right' else GRAY
        keybind_right_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                         key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'bottom':
            key_text = "Press a key..."
        else:
            key_text = f"Bottom: {get_key_name(keybinds['bottom'])}"
        color = BLUE if waiting_for_key == 'bottom' else GRAY
        keybind_bottom_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                          key_text, color)
        
        y_offset += button_spacing
        if waiting_for_key == 'left':
            key_text = "Press a key..."
        else:
            key_text = f"Left: {get_key_name(keybinds['left'])}"
        color = BLUE if waiting_for_key == 'left' else GRAY
        keybind_left_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                        key_text, color)
        
        # Mouse binds
        y_offset += button_spacing + 20
        mouse_label = font_label.render("Mouse Buttons", True, BLACK)
        screen.blit(mouse_label, (right_col_x, y_offset - 15))
        
        y_offset += 30
        if waiting_for_mouse == 'red':
            mouse_text = "Press key/click..."
        else:
            mouse_text = f"Red: {get_mouse_name(mouse_binds['red'])}"
        color = RED if waiting_for_mouse == 'red' else GRAY
        mouse_red_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                     mouse_text, color)
        
        y_offset += button_spacing
        if waiting_for_mouse == 'blue':
            mouse_text = "Press key/click..."
        else:
            mouse_text = f"Blue: {get_mouse_name(mouse_binds['blue'])}"
        color = BLUE if waiting_for_mouse == 'blue' else GRAY
        mouse_blue_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                      mouse_text, color)
        
        # Reset button
        y_offset += button_spacing + 10
        reset_keybinds_rect = draw_button(right_col_x, y_offset, button_width, button_height,
                                         "Reset to Default", DARK_GRAY)
        
        # Bottom buttons
        button_y = window_height - 110
        if from_game:
            quit_menu_rect = draw_button(window_width // 2 - 210, button_y, 200, 50, "Quit to Menu", RED)
            quit_game_rect = draw_button(window_width // 2 + 10, button_y, 200, 50, "Quit Game", RED)
        elif from_selector:
            quit_menu_rect = None
            quit_game_rect = draw_button(window_width // 2 - 100, button_y, 200, 50, "Quit Game", RED)
        else:
            quit_menu_rect = None
            quit_game_rect = draw_button(window_width // 2 - 100, button_y, 200, 50, "Back", GRAY)
        
        # Hint text
        if from_selector or from_game:
            hint_text = "Press ESC to go back"
        else:
            hint_text = "Press ESC to go back"
        hint_surface = font_small.render(hint_text, True, DARK_GRAY)
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
        elif keybind_top_rect and keybind_top_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_right_rect and keybind_right_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_bottom_rect and keybind_bottom_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif keybind_left_rect and keybind_left_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif mouse_red_rect and mouse_red_rect.collidepoint(mouse_pos):
            hovering_button = True
        elif mouse_blue_rect and mouse_blue_rect.collidepoint(mouse_pos):
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

    font_large = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 48)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    def draw_autoplay_content(surf):
        surf.fill(WHITE)
        title_text = font_large.render("Enable Autoplay?", True, BLACK)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        surf.blit(title_text, title_rect)

        yes_text = font_small.render("Press Y for Yes", True, BLACK)
        yes_rect = yes_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
        surf.blit(yes_text, yes_rect)

        no_text = font_small.render("Press N for No", True, BLACK)
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
        level_json = show_level_select_popup(fade_in_start=returning_from_game, preloaded_metadata=preloaded_metadata)
        if level_json is None:
            print("No level selected. Exiting...")
            return

    if audio_dir is None:
        level_filename = os.path.basename(level_json)
        beatmap_name = level_filename.replace('.json', '').split('_')[0]
        audio_dir = f"beatmaps/{beatmap_name}"

    autoplay_enabled = show_autoplay_popup()

    if autoplay_enabled == 'BACK':
        screen = pygame.display.get_surface()
        if game_settings.get('fade_effects', True):
            fade_out(screen, duration=0.7)
        return 'RESTART'

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

    square_size = 100
    spacing = 105
    border_width = 3
    radius = 10

    active_key = None

    last_clicked_button = None
    click_time = 0
    shake_time = 0
    shake_intensity = 0
    shake_box = None

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

    # Offset all level timings by 3 seconds for music delay
    level = [(t + 3.0, box, color, hs) for t, box, color, hs in level]

    target_box = None
    target_color = None
    target_time = None
    target_hitsound = None

    # Track approach indicators - list of (box_index, color, target_time, approach_duration, event_index, side)
    approach_indicators = []

    # Load and scale box image
    box_image = pygame.image.load(resource_path("assets/box.jpg")).convert()
    box_image = pygame.transform.scale(box_image, (square_size, square_size))

    box_red_image = pygame.image.load(resource_path("assets/boxred.jpg")).convert()
    box_red_image = pygame.transform.scale(box_red_image, (square_size, square_size))
    box_blue_image = pygame.image.load(resource_path("assets/boxblue.jpg")).convert()
    box_blue_image = pygame.transform.scale(box_blue_image, (square_size, square_size))

    dot_image = pygame.image.load(resource_path("assets/dot.jpg")).convert()
    dot_image = pygame.transform.scale(dot_image, (50, 50))
    dot2_image = pygame.image.load(resource_path("assets/dot2.jpg")).convert()
    dot2_image = pygame.transform.scale(dot2_image, (50, 50))

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
    try:
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = None
            for prefix in ['normal', 'soft', 'drum']:
                for ext in hitsound_extensions:
                    sound_file = f"{prefix}-hit{sound_name}{ext}"
                    sound_path = os.path.join(audio_dir, sound_file)
                    if os.path.exists(resource_path(sound_path)):
                        sound = pygame.mixer.Sound(resource_path(sound_path))
                        break
                if sound:
                    break
            if sound is None:
                sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(game_settings.get('hitsound_volume', 0.3))
            hitsounds[sound_name] = sound
    except Exception as e:
        print(f"Could not load hitsounds: {e}")
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(game_settings.get('hitsound_volume', 0.3))
            hitsounds[sound_name] = sound

    # Load beatmap background image if available
    beatmap_bg_image = None
    try:
        for file in os.listdir(resource_path(audio_dir)):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                bg_path = os.path.join(audio_dir, file)
                bg_img = pygame.image.load(resource_path(bg_path))
                original_width, original_height = bg_img.get_size()
                target_height = 150
                aspect_ratio = original_width / original_height
                target_width = int(target_height * aspect_ratio)
                beatmap_bg_image = pygame.transform.scale(bg_img, (target_width, target_height))
                break
    except Exception as e:
        print(f"Could not load beatmap background: {e}")
        beatmap_bg_image = None

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

    font_countdown = pygame.font.Font(None, 120)
    font_judgment = pygame.font.Font(None, 36)
    font_stats = pygame.font.Font(None, 32)
    font_metadata = pygame.font.Font(None, 24)
    font_combo = pygame.font.Font(None, 92)

    count_300 = 0
    count_100 = 0
    count_50 = 0
    count_miss = 0
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
    
    # Get keybinds from settings
    keybinds = game_settings.get('keybinds')
    mouse_binds = game_settings.get('mouse_binds')

    def key_for_box(box_idx):
        key_map = ['top', 'right', 'bottom', 'left']
        return keybinds[key_map[box_idx]]

    def button_for_color(color):
        return mouse_binds[color]

    def compute_dynamic_window(evt_idx, base_window):
        if evt_idx >= len(level):
            return base_window
        t0 = level[evt_idx][0]
        t1 = level[evt_idx + 1][0] if evt_idx + 1 < len(level) else t0 + 10.0
        gap = t1 - t0
        return (gap / 2) if gap > 1.0 else base_window

    def judgment_from_error(timing_error):
        if timing_error <= 0.02:
            return 300, "300"
        if timing_error <= 0.0475:
            return 100, "100"
        if timing_error <= 0.075:
            return 50, "50"
        return None, None

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
        nonlocal count_miss, total_notes, combo, current_event_index
        count_miss += 1
        total_notes += 1
        combo = 0
        add_judgment_text("miss", miss_box_idx)
        resolved_events.add(evt_idx)
        current_event_index += 1

    def resolve_hit(evt_idx, hit_box_idx, timing_error):
        nonlocal score, total_hits, total_notes, combo, combo_pop_time, current_event_index
        nonlocal count_300, count_100, count_50
        judgment, text = judgment_from_error(timing_error)
        if judgment is None:
            resolve_miss(evt_idx, hit_box_idx)
            return

        score += judgment
        total_hits += 1
        total_notes += 1
        combo += 1
        combo_pop_time = time.time()

        if judgment == 300:
            count_300 += 1
        elif judgment == 100:
            count_100 += 1
        else:
            count_50 += 1

        add_judgment_text(text, hit_box_idx)
        trigger_box_shake(hit_box_idx, intensity=9)
        if game_settings.get('hitsounds_enabled', True):
            hitsounds['normal'].play()

        resolved_events.add(evt_idx)
        current_event_index += 1

    def handle_click(button_name, elapsed_time_local, evt_idx):
        if evt_idx >= len(level):
            return False

        evt_time, evt_box, evt_color, evt_hitsound = level[evt_idx]

        # NEW: cannot judge this note until 0.5s after it spawns on screen
        spawn_time = evt_time - APPROACH_DURATION
        if elapsed_time_local < spawn_time + JUDGE_DELAY_AFTER_SPAWN:
            return False

        dyn_window = compute_dynamic_window(evt_idx, accuracy_window)
        timing_error = abs(elapsed_time_local - evt_time)

        if timing_error > dyn_window:
            return False

        expected_key = key_for_box(evt_box)
        expected_button = button_for_color(evt_color)

        if button_name != expected_button or active_key != expected_key:
            resolve_miss(evt_idx, evt_box)
            return True

        resolve_hit(evt_idx, evt_box, timing_error)
        return True


    running = True

    # ===== End-of-level handling (2s delay, 3s music fade, then return to level selector) =====
    level_end_elapsed = None
    music_fade_started = False
    music_fade_start_elapsed = None
    POST_LEVEL_DELAY = 3.0
    POST_LEVEL_MUSIC_FADE = 3.0

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

        if music_start_time is None and elapsed_time >= 3.0 and not paused:
            pygame.mixer.music.play()
            music_start_time = time.time()

        if current_event_index < len(level):
            target_time, target_box, target_color, target_hitsound = level[current_event_index]
        
        # Autoplay
        if autoplay_enabled and not paused and current_event_index < len(level):
            if elapsed_time >= target_time:
                active_key = key_for_box(target_box)

                score += 300
                total_hits += 1
                total_notes += 1
                combo += 1
                combo_pop_time = time.time()
                count_300 += 1

                add_judgment_text("300", target_box)
                resolved_events.add(current_event_index)
                trigger_box_shake(target_box, intensity=9)

                # Play hitsounds during autoplay
                if game_settings.get('hitsounds_enabled', True):
                    hitsounds['normal'].play()
                current_event_index += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
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
                        # Reload keybinds
                        keybinds = game_settings.get('keybinds')
                        mouse_binds = game_settings.get('mouse_binds')
                    elif settings_result == 'QUIT_MENU':
                        # Quit to menu
                        pygame.mixer.music.stop()
                        if game_settings.get('fade_effects', True):
                            fade_out(screen, duration=0.7)
                        return 'RESTART'
                    elif settings_result == 'QUIT':
                        # Quit game completely
                        pygame.mixer.music.stop()
                        if game_settings.get('fade_effects', True):
                            fade_out(screen, duration=0.7)
                        pygame.quit()
                        sys.exit()

                if not paused:
                    # Check if any keybind was pressed
                    if event.key == keybinds['top']:
                        active_key = keybinds['top']
                    elif event.key == keybinds['right']:
                        active_key = keybinds['right']
                    elif event.key == keybinds['bottom']:
                        active_key = keybinds['bottom']
                    elif event.key == keybinds['left']:
                        active_key = keybinds['left']
                    
                    # Check if red/blue are mapped to keyboard keys
                    if display_time >= 3.0 and current_event_index < len(level):
                        if event.key == mouse_binds['red']:
                            handle_click(mouse_binds['red'], elapsed_time, current_event_index)
                        elif event.key == mouse_binds['blue']:
                            handle_click(mouse_binds['blue'], elapsed_time, current_event_index)

            if event.type == pygame.MOUSEBUTTONDOWN and not paused:
                if display_time < 3.0:
                    continue
                if current_event_index < len(level):
                    if event.button == mouse_binds['red']:
                        handle_click(mouse_binds['red'], elapsed_time, current_event_index)
                    elif event.button == mouse_binds['blue']:
                        handle_click(mouse_binds['blue'], elapsed_time, current_event_index)

        # Auto-miss past window
        if not paused:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            while current_event_index < len(level) and elapsed_time > level[current_event_index][0] + accuracy_window:
                missed_time, missed_box, missed_color, missed_hitsound = level[current_event_index]
                if current_event_index not in resolved_events:
                    resolve_miss(current_event_index, missed_box)
                else:
                    current_event_index += 1

            if current_event_index < len(level):
                target_time, target_box, target_color, target_hitsound = level[current_event_index]

            # Maintain approach indicators
            approach_indicators = [
                (box_idx, color, t_time, duration, evt_idx, side)
                for box_idx, color, t_time, duration, evt_idx, side in approach_indicators
                if elapsed_time <= t_time
            ]

            existing_events = {evt_idx for _, _, _, _, evt_idx, _ in approach_indicators}
            APPROACH_DURATION = 0.8
            JUDGE_DELAY_AFTER_SPAWN = 0.1

            approach_duration = APPROACH_DURATION
            lookahead = 10
            lookback = 5
            start_scan = max(0, current_event_index - lookback)
            for i in range(start_scan, min(current_event_index + lookahead, len(level))):
                if i not in existing_events:
                    evt_time, evt_box, evt_color, evt_hitsound = level[i]
                    if elapsed_time <= evt_time:
                        if evt_box == 0:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'left'))
                        elif evt_box == 2:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'right'))
                        else:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, None))

            # One-time shake exactly when tile reaches box (TRULY timing-driven; independent of input)
            while arrival_shake_index < len(level) and elapsed_time >= level[arrival_shake_index][0]:
                t_note, box_idx, color, hs = level[arrival_shake_index]
                if arrival_shake_index not in reached_shake_events:
                    reached_shake_events.add(arrival_shake_index)
                    trigger_box_shake(box_idx, intensity=9)
                arrival_shake_index += 1

            # ===== End-of-level flow (NO freezing; let visuals keep running) =====
            # Mark end-of-level once ALL notes are resolved (hit or miss)
            if current_event_index >= len(level) and level_end_elapsed is None:
                level_end_elapsed = elapsed_time

            # After 2s delay, fade music for 3s, then fade screen and return to selector
            if level_end_elapsed is not None:
                if (elapsed_time - level_end_elapsed) >= POST_LEVEL_DELAY and not music_fade_started:
                    pygame.mixer.music.fadeout(int(POST_LEVEL_MUSIC_FADE * 1000))
                    music_fade_started = True
                    music_fade_start_elapsed = elapsed_time

                if music_fade_started and (elapsed_time - music_fade_start_elapsed) >= POST_LEVEL_MUSIC_FADE:
                    if game_settings.get('fade_effects', True):
                        fade_out(screen, duration=0.7)
                    return 'RESTART'

        screen.fill(WHITE)

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


        # Edge flash indicators
        edge_flash_height = square_size // 2 + spacing - 10
        edge_flash_duration = 0.25
        edge_offset = 0

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
        indicator_size = 95
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

            alpha = int(245 * min(1.0, progress))
            indicator_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
            indicator_surface = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
            pygame.draw.rect(indicator_surface, (*indicator_color, alpha), (0, 0, indicator_size, indicator_size), 0, 8)
            screen.blit(indicator_surface, (int(current_x - indicator_size // 2), int(current_y - indicator_size // 2)))

        # Judgments
        current_time = time.time()
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

                judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                judgment_surface.set_alpha(alpha)
                text_rect = judgment_surface.get_rect(center=(int(display_x), int(display_y)))
                screen.blit(judgment_surface, text_rect)
                active_judgments.append((judgment_text, jx, jy, start_time, box_idx, side))
        judgment_displays = active_judgments

        # Combo
        combo_text_str = f"{combo}x"
        combo_surface = font_combo.render(combo_text_str, True, BLACK)

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
        combo_rect = rotated_combo.get_rect(bottomleft=(30, screen_height - 130))
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

            metadata_lines = [
                f"{title} - {artist}",
                f"[{version}] by {creator}"
            ]

            for i, line in enumerate(metadata_lines):
                meta_text = font_metadata.render(line, True, BLACK)
                meta_rect = meta_text.get_rect(right=screen_width - right_margin, top=stats_start_y + i * 25)
                screen.blit(meta_text, meta_rect)

            stats_start_y += len(metadata_lines) * 25 + 10

        if beatmap_bg_image:
            img_width = beatmap_bg_image.get_width()
            img_height = beatmap_bg_image.get_height()
            img_x = screen_width - img_width - right_margin
            screen.blit(beatmap_bg_image, (img_x, stats_start_y))
            stats_start_y += img_height + 10

        # Stats
        total_possible = total_notes * 300
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
            y_pos = stats_bottom_y - (i + 1) * 30
            label_text = font_stats.render(label, True, BLACK)
            label_rect = label_text.get_rect(left=left_margin, top=y_pos)
            screen.blit(label_text, label_rect)

            number_text = font_stats.render(number, True, BLACK)
            number_rect = number_text.get_rect(left=left_margin + 120, top=y_pos)
            screen.blit(number_text, number_rect)

        # Dots
        dot_size = 50
        for i, (dot_x, dot_y) in enumerate(dot_positions):
            is_active = False
            if i == 0 and active_key == keybinds['top']:
                is_active = True
            elif i == 1 and active_key == keybinds['right']:
                is_active = True
            elif i == 2 and active_key == keybinds['bottom']:
                is_active = True
            elif i == 3 and active_key == keybinds['left']:
                is_active = True

            current_dot = dot2_image if is_active else dot_image
            screen.blit(current_dot, (int(dot_x - dot_size // 2), int(dot_y - dot_size // 2)))

        # Countdown
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

            countdown_surface = font_countdown.render(countdown_text, True, BLACK)
            countdown_surface.set_alpha(alpha)
            countdown_rect = countdown_surface.get_rect(center=(center_x, center_y))
            screen.blit(countdown_surface, countdown_rect)

        # Fade-in overlay
        if fade_in_alpha > 0:
            fade_overlay = pygame.Surface((screen_width, screen_height))
            fade_overlay.fill((0, 0, 0))
            fade_overlay.set_alpha(fade_in_alpha)
            screen.blit(fade_overlay, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    pygame.mixer.music.stop()
    return None

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Initialize levels/beatmaps from .osz files if needed
    initialize_levels_from_osz()

    REGENERATE_LEVEL = False

    if REGENERATE_LEVEL:
        from batch_process_osz import process_osz_files
        print("Running batch processor to generate levels from .osz files...")
        process_osz_files()
    else:
        preloaded_metadata = show_loading_screen()

        if preloaded_metadata is None:
            print("Failed to load assets. Exiting...")
            sys.exit()

        returning = False
        while True:
            result = main(returning_from_game=returning, preloaded_metadata=preloaded_metadata)
            if result != 'RESTART':
                break
            returning = True

        pygame.display.quit()
        pygame.quit()
        sys.exit()
