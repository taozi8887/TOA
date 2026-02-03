"""
TOA Game Launcher with Auto-Update
This launcher checks for and applies code updates before running the game.
"""

import os
import sys
import subprocess
import json

# Determine the actual directory where the exe/script is running from
if getattr(sys, 'frozen', False):
    # Running as compiled exe - use the directory where exe is located
    application_path = os.path.dirname(sys.executable)
    
    # Extract bundled config file to .toa folder if it doesn't exist
    toa_folder = os.path.join(application_path, '.toa')
    config_path = os.path.join(toa_folder, 'update_config.json')
    if not os.path.exists(config_path):
        os.makedirs(toa_folder, exist_ok=True)
        import shutil
        bundled_config = os.path.join(sys._MEIPASS, 'update_config.json')
        if os.path.exists(bundled_config):
            shutil.copy2(bundled_config, config_path)
            print("Extracted update_config.json")
else:
    # Running as script - use script directory
    application_path = os.path.dirname(os.path.abspath(__file__))

# Change to application directory and add to path FIRST
os.chdir(application_path)

def show_installer_window(updater, all_files, is_first_run=True):
    """Show GUI installer window with download progress"""
    import pygame
    
    pygame.init()
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("TOA Installer")
    clock = pygame.time.Clock()
    
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 32)
    font_small = pygame.font.Font(None, 24)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (100, 150, 255)
    GRAY = (200, 200, 200)
    
    # Calculate total size (rough estimate)
    total_files = len(all_files)
    estimated_mb = total_files * 0.5  # Rough estimate
    
    downloaded = [0]  # Use list to allow modification in nested function
    current_file_info = {'name': '', 'downloaded': 0, 'total': 0, 'start_time': 0}
    import time
    
    def progress_callback(current, total, filename, file_downloaded, file_total):
        downloaded[0] = current
        
        # Update current file info
        if filename != current_file_info['name']:
            current_file_info['name'] = filename or ''
            current_file_info['downloaded'] = 0
            current_file_info['total'] = file_total
            current_file_info['start_time'] = time.time()
        else:
            current_file_info['downloaded'] = file_downloaded
            current_file_info['total'] = file_total
        
        # Draw window
        screen.fill(WHITE)
        
        # Title
        title = "Installing TOA..." if is_first_run else "Updating TOA..."
        title_text = font_large.render(title, True, BLACK)
        title_rect = title_text.get_rect(center=(300, 60))
        screen.blit(title_text, title_rect)
        
        # Progress text
        progress_text = font_medium.render(f"{current}/{total} files", True, BLACK)
        progress_rect = progress_text.get_rect(center=(300, 140))
        screen.blit(progress_text, progress_rect)
        
        # Current file progress
        if file_total > 0:
            file_mb = file_downloaded / 1024 / 1024
            total_file_mb = file_total / 1024 / 1024
            
            # Calculate download speed
            elapsed = time.time() - current_file_info['start_time']
            speed_text = ""
            if elapsed > 0 and file_downloaded > 0:
                speed = file_downloaded / elapsed / 1024  # KB/s
                if speed > 1024:
                    speed_text = f" ({speed/1024:.1f} MB/s)"
                else:
                    speed_text = f" ({speed:.0f} KB/s)"
            
            file_text = font_small.render(f"{file_mb:.1f}/{total_file_mb:.1f} MB{speed_text}", True, GRAY)
            file_rect = file_text.get_rect(center=(300, 180))
            screen.blit(file_text, file_rect)
        
        # Progress bar
        bar_width = 500
        bar_height = 30
        bar_x = 50
        bar_y = 220
        
        # Background
        pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_width, bar_height), border_radius=15)
        
        # Fill
        fill_width = int((current / total) * bar_width)
        if fill_width > 0:
            pygame.draw.rect(screen, BLUE, (bar_x, bar_y, fill_width, bar_height), border_radius=15)
        
        # Percentage
        percentage = int((current / total) * 100)
        percent_text = font_small.render(f"{percentage}%", True, BLACK)
        percent_rect = percent_text.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))
        screen.blit(percent_text, percent_rect)
        
        # Status
        status_text = font_small.render("Downloading from GitHub...", True, GRAY)
        status_rect = status_text.get_rect(center=(300, 330))
        screen.blit(status_text, status_rect)
        
        pygame.display.flip()
        pygame.event.pump()  # Keep window responsive
        clock.tick(60)
    
    # Start download
    success = updater.download_updates(all_files, progress_callback=progress_callback, is_initial_download=is_first_run)
    
    if success:
        # Show completion message
        screen.fill(WHITE)
        complete_text = font_large.render("Complete!", True, BLUE)
        complete_rect = complete_text.get_rect(center=(300, 180))
        screen.blit(complete_text, complete_rect)
        
        status_text = font_medium.render("Restarting game...", True, BLACK)
        status_rect = status_text.get_rect(center=(300, 240))
        screen.blit(status_text, status_rect)
        
        pygame.display.flip()
        pygame.time.wait(1000)
    
    pygame.quit()
    return success

# Change to application directory and add to path FIRST
os.chdir(application_path)

# CRITICAL: When running as exe, check if launcher.py/auto_updater.py need to be downloaded to .toa
if getattr(sys, 'frozen', False):
    toa_path = os.path.join(application_path, '.toa')
    launcher_in_toa = os.path.join(toa_path, 'launcher.py')
    updater_in_toa = os.path.join(toa_path, 'auto_updater.py')
    
    # If these files don't exist in .toa, extract from bundled versions
    # (They'll be updated later by the update system)
    if not os.path.exists(launcher_in_toa) or not os.path.exists(updater_in_toa):
        os.makedirs(toa_path, exist_ok=True)
        # The bundled versions will be used first time, then GitHub versions after
        # Note: This only happens on very first run - updates will replace these
    
    # Always prioritize .toa folder for imports (where updates are stored)
    if os.path.exists(toa_path):
        sys.path.insert(0, toa_path)  # .toa folder has highest priority
    sys.path.insert(0, application_path)
else:
    sys.path.insert(0, application_path)

def check_and_update():
    """Check for updates and download if available"""
    try:
        from auto_updater import AutoUpdater
        import requests
        
        # Load configuration
        try:
            config_path = os.path.join('.toa', 'update_config.json') if getattr(sys, 'frozen', False) else 'update_config.json'
            print(f"Looking for config at: {config_path}")
            with open(config_path, 'r') as f:
                config = json.load(f).get('auto_update', {})
            print(f"Config loaded. Enabled: {config.get('enabled', False)}")
        except Exception as e:
            print(f"Could not load update config: {e}")
            return False
        
        if not config.get('enabled', False):
            print("Auto-update is disabled in config")
            return False
        
        # Initialize updater
        updater = AutoUpdater(
            config.get('github_username', ''),
            config.get('repository_name', ''),
            config.get('branch', 'main')
        )
        
        # Check if this is first run (no files downloaded yet)
        if updater.is_first_run():
            # Get all files from remote
            all_files = updater.get_all_remote_files()
            
            if not all_files:
                return False
            
            # Show GUI installer
            success = show_installer_window(updater, all_files, is_first_run=True)
            
            # Hide .toa folder on Windows with system + hidden attributes
            if sys.platform == 'win32':
                import subprocess
                toa_path = os.path.join(application_path, '.toa')
                # Set as hidden + system to make it truly inaccessible
                subprocess.run(['attrib', '+H', '+S', toa_path], shell=True, capture_output=True)
            
            return False  # Don't restart - this was initial download, not an update
        
        # Normal update check
        print("Checking for updates...")
        directories = config.get('directories_to_sync', ['levels', 'beatmaps'])
        has_updates, files_to_update, update_info = updater.check_for_updates(directories, include_code=True)
        
        print(f"Update check result: has_updates={has_updates}, files_count={len(files_to_update)}")
        if update_info:
            print(f"Local: v{update_info.get('from_version', 'unknown')} -> Remote: v{update_info.get('to_version', 'unknown')}")
        
        if has_updates and len(files_to_update) > 0:
            # Print update info
            print(f"\nUpdate available: v{update_info.get('to_version', 'unknown')}")
            if update_info.get('release_date'):
                print(f"Released: {update_info['release_date']}")
            print(f"Files to update: {len(files_to_update)}")
            
            # Show GUI for updates
            success = show_installer_window(updater, files_to_update, is_first_run=False)
            # Return True if update was successful so main() can restart
            return success
        else:
            return False
    
    except ImportError:
        print("Auto-update not available (missing dependencies)")
        return False
    except Exception as e:
        print(f"Error during update check: {e}")
        return False

def main():
    """Main launcher function"""
    # CRITICAL: Pre-load pygame AND all its submodules FIRST before anything else when running as exe
    # This must happen before check_and_update() to avoid DLL path issues
    if getattr(sys, 'frozen', False):
        try:
            import pygame
            import pygame.gfxdraw  # CRITICAL: Import submodule so it's available
            # Keep pygame in sys.modules so main.py can use it
            print(f"Pre-loaded pygame from bundled location")
        except Exception as e:
            print(f"Warning: Could not pre-load pygame: {e}")
            import traceback
            traceback.print_exc()
    
    # Check for updates
    code_was_updated = check_and_update()
    
    if code_was_updated:
        print("Code was updated! Restarting...")
        # Restart by running the exe again (not Python directly)
        import time
        time.sleep(1)  # Brief pause to ensure files are released
        
        if getattr(sys, 'frozen', False):
            # Running as exe - restart the exe
            exe_path = sys.executable
            os.execv(exe_path, [exe_path] + sys.argv[1:])
        else:
            # Running as script - restart Python
            python = sys.executable
            os.execv(python, [python] + sys.argv)
    
    # CRITICAL: Remove any cached/bundled modules before importing
    # This ensures we load the downloaded files, not bundled ones
    # DO NOT remove pygame - we need to keep it loaded!
    modules_to_reload = ['main', 'osu_to_level', 'unzip', 'auto_updater', 'batch_process_osz']
    for module in modules_to_reload:
        if module in sys.modules:
            del sys.modules[module]
    
    # Clear importlib caches to ensure fresh imports
    import importlib
    importlib.invalidate_caches()
    
    # Import and run the game
    print("Starting TOA...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")  # Show first 3 paths
    
    try:
        # When running as exe, ALWAYS load from .toa folder
        if getattr(sys, 'frozen', False):
            toa_main_path = os.path.join('.toa', 'main.py')
            if os.path.exists(toa_main_path):
                import importlib.util
                
                # Read the main.py file content
                with open(toa_main_path, 'r', encoding='utf-8') as f:
                    main_code = f.read()
                
                # Create the module and inject bundled pygame before execution
                spec = importlib.util.spec_from_file_location("main", os.path.abspath(toa_main_path))
                game_main = importlib.util.module_from_spec(spec)
                
                # CRITICAL: Inject bundled pygame into main's namespace BEFORE executing
                # This ensures main.py uses the bundled pygame, not try to import a new one
                game_main.pygame = pygame
                
                sys.modules['main'] = game_main
                spec.loader.exec_module(game_main)
                print(f"Force-loaded main.py from: {os.path.abspath(toa_main_path)}")
            else:
                print("ERROR: Game files not found!")
                print("Please check your internet connection and restart the game.")
                sys.exit(1)
        else:
            # When running as script, load from current directory
            import main as game_main
            print(f"Script mode: loaded main.py from: {game_main.__file__}")
        
        print(f"Loaded main.py version: {game_main.__version__}")
        
        # Run the game's main entry point
        if hasattr(game_main, '__name__'):
            # Execute the if __name__ == "__main__" block
            import multiprocessing
            multiprocessing.freeze_support()
            
            # Initialize levels/beatmaps from .osz files if needed
            game_main.initialize_levels_from_osz()
            
            game_main.REGENERATE_LEVEL = False
            
            preloaded_metadata = game_main.show_loading_screen()
            
            if preloaded_metadata is None:
                print("Failed to load assets. Exiting...")
                sys.exit()
            
            returning = False
            while True:
                result = game_main.main(returning_from_game=returning, preloaded_metadata=preloaded_metadata)
                if result != 'RESTART':
                    break
                returning = True
            
            # Pygame cleanup
            if 'pygame' in sys.modules:
                pygame.display.quit()
                pygame.quit()
            sys.exit()
    
    except Exception as e:
        print(f"Error starting game: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
