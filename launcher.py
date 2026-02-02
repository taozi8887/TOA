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

# When running as exe, prioritize .toa folder for module imports
if getattr(sys, 'frozen', False):
    toa_path = os.path.join(application_path, '.toa')
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
            with open(config_path, 'r') as f:
                config = json.load(f).get('auto_update', {})
        except:
            print("Could not load update config, skipping auto-update")
            return False
        
        if not config.get('enabled', False):
            return False
        
        # Initialize updater
        updater = AutoUpdater(
            config.get('github_username', ''),
            config.get('repository_name', ''),
            config.get('branch', 'main')
        )
        
        # Check if this is first run (no files downloaded yet)
        if updater.is_first_run():
            print("=" * 60)
            print("FIRST RUN DETECTED")
            print("Downloading all game files from GitHub...")
            print("This may take a few minutes...")
            print("=" * 60)
            
            # Get all files from remote
            all_files = updater.get_all_remote_files()
            
            if not all_files:
                print("ERROR: Could not retrieve file list from GitHub")
                print("Please check your internet connection")
                return False
            
            print(f"Downloading {len(all_files)} files...")
            
            # Define progress callback
            def progress(current, total, filename):
                print(f"[{current}/{total}] {filename}")
            
            # Download all files
            success = updater.download_updates(all_files, progress_callback=progress, is_initial_download=True)
            
            if success:
                print("=" * 60)
                print("DOWNLOAD COMPLETE!")
                print("Starting game...")
                print("=" * 60)
                return False  # Don't restart - this was initial download, not an update
            else:
                print("ERROR: Failed to download game files")
                return False
        
        # Normal update check
        print("Checking for updates...")
        
        # Check for updates (including code)
        directories = config.get('directories_to_sync', ['levels', 'beatmaps'])
        has_updates, files_to_update = updater.check_for_updates(directories, include_code=True)
        
        if has_updates:
            print(f"Found {len(files_to_update)} files to update")
            print("Downloading updates...")
            
            # Download updates
            success = updater.download_updates(files_to_update)
            
            if success:
                print("Updates downloaded successfully!")
                
                # Don't restart for normal updates - just continue to load the updated code
                return False
            else:
                print("Some updates failed to download")
                return False
        else:
            print("No updates available")
            return False
    
    except ImportError:
        print("Auto-update not available (missing dependencies)")
        return False
    except Exception as e:
        print(f"Error during update check: {e}")
        return False

def main():
    """Main launcher function"""
    # Check for updates
    code_was_updated = check_and_update()
    
    if code_was_updated:
        print("Code was updated! Restarting...")
        # Restart the launcher to use new code
        python = sys.executable
        os.execl(python, python, *sys.argv)
    
    # CRITICAL: Pre-load pygame BEFORE clearing cache to keep DLLs loaded
    if getattr(sys, 'frozen', False):
        try:
            import pygame
            print(f"Pre-loaded pygame from bundled location")
        except Exception as e:
            print(f"Warning: Could not pre-load pygame: {e}")
    
    # CRITICAL: Remove any cached/bundled modules before importing
    # This ensures we load the downloaded files, not bundled ones
    # DO NOT remove pygame - we need to keep it loaded!
    modules_to_reload = ['main', 'osu_to_level', 'unzip', 'auto_updater', 'batch_process_osz']
    for module in modules_to_reload:
        if module in sys.modules:
            del sys.modules[module]
    
    # Import and run the game
    print("Starting TOA...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Loading main.py from: {os.path.abspath('main.py')}")
    
    try:
        import main as game_main
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
