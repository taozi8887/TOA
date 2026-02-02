"""
TOA Game Launcher with Auto-Update
This launcher checks for and applies code updates before running the game.
"""

import os
import sys
import subprocess
import json

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_and_update():
    """Check for updates and download if available"""
    try:
        from auto_updater import AutoUpdater
        import requests
        
        # Load configuration
        try:
            with open('update_config.json', 'r') as f:
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
                print("Saving version.json...")
                
                # Ensure version.json is saved
                try:
                    remote_version = updater._get_remote_version()
                    if remote_version:
                        with open('version.json', 'w') as f:
                            json.dump(remote_version, f, indent=2)
                        print("version.json saved successfully!")
                    else:
                        print("Warning: Could not fetch remote version to save")
                except Exception as e:
                    print(f"Error saving version.json: {e}")
                
                # Check if any code files were updated
                code_updated = any(f.endswith('.py') for f in files_to_update)
                return code_updated
            else:
                print("Some updates failed to download")
                return False
        else:
            print("No updates available")
            
            # Still save version.json if it doesn't exist
            if not os.path.exists('version.json'):
                print("Creating local version.json...")
                try:
                    print(f"Fetching from: {updater.raw_url}/version.json")
                    remote_version = updater._get_remote_version()
                    if remote_version:
                        print(f"Got remote version: {remote_version.get('version', 'unknown')}")
                        with open('version.json', 'w') as f:
                            json.dump(remote_version, f, indent=2)
                        print("version.json created!")
                    else:
                        print("ERROR: Could not fetch remote version.json from GitHub")
                except Exception as e:
                    print(f"Error creating version.json: {e}")
                    import traceback
                    traceback.print_exc()
            
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
    
    # Import and run the game
    print("Starting TOA...")
    try:
        import main as game_main
        
        # Run the game's main entry point
        if hasattr(game_main, '__name__'):
            # Execute the if __name__ == "__main__" block
            import multiprocessing
            multiprocessing.freeze_support()
            
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
            
            import pygame
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
