"""
Build script to create TOA executable using PyInstaller
Run this script to package the game into a standalone .exe

Usage:
    python build_exe.py
"""
import subprocess
import sys
import os
import shutil
import re

def get_version_from_spec():
    """Extract version from TOA.spec file"""
    try:
        with open('TOA.spec', 'r') as f:
            content = f.read()
            match = re.search(r"name='TOA-v([\d.]+)'", content)
            if match:
                return match.group(1)
    except:
        pass
    return "0.5.0"  # Fallback

VERSION = get_version_from_spec()

def build_exe():
    """Build the executable using PyInstaller"""
    
    exe_name = "TOA"
    release_folder = f"releases"
    
    # Use the TOA.spec file which has all the proper configuration
    print(f"\nBuilding {exe_name}.exe...")
    print("This may take a few minutes...")
    
    try:
        result = subprocess.run(['pyinstaller', 'TOA.spec'], check=True)
        print("\n✓ Build successful!")
        
        # Create release folder
        os.makedirs(release_folder, exist_ok=True)
        
        # Copy ONLY the exe to release folder
        shutil.copy2(f"dist/{exe_name}.exe", release_folder)
        print(f"\n✓ Copied exe to {release_folder}")
        
        print("\nAUTO-UPDATE MODE WITH ENHANCED SECURITY:")
        print("  ✓ launcher.py + auto_updater.py (bundled in exe)")
        print("  ✓ update_config.json (bundled in exe)")
        print("  ✓ .toa folder hidden with system attributes")
        print("  ✓ File operations invisible to users")
        print("\nOn first run, the exe will automatically download:")
        print("  - All Python game files (main.py, etc.)")
        print("  - assets/ folder")
        print("  - levels/ folder")
        print("  - beatmaps/ folder")
        print("  - version.json")
        print("\nSECURITY FEATURES:")
        print("  ✓ Files stored in hidden .toa folder (system + hidden)")
        print("  ✓ No file names shown during installation/updates")
        print("  ✓ Progress bar shows only size and count")
        print("  ✓ Users cannot access .toa folder during operations")
        print("\nOn subsequent runs:")
        print("  - Checks GitHub for updates")
        print("  - Downloads only changed files")
        print("  - All operations hidden from view")
        print("  - No re-download needed!")
        
        # Create README for distribution
        readme_content = f"""TOA v{VERSION} - Rhythm Game
============================

INSTALLATION:
1. Download TOA-v{VERSION}.exe
2. Place it in a folder (it will create subfolders)
3. Run it!

FIRST RUN:
The game will automatically download all required files from GitHub:
- Game levels and beatmaps
- Music and sound files  
- Assets and images

SECURITY & INTEGRITY:
✓ All game files stored in hidden .toa folder (system protected)
✓ File operations are invisible to users
✓ Only progress bar and size shown during updates
✓ Game files protected from user modification

This first download may take 1-2 minutes.
Make sure you have an internet connection!

AUTO-UPDATE:
Every time you launch the game:
✓ Automatically checks for updates
✓ Downloads only new/changed files
✓ No reinstallation needed!

When you push updates to GitHub, users get them automatically.

WHAT USERS SEE:
TOA-v{VERSION}.exe
levels/ (downloaded automatically)
beatmaps/ (downloaded automatically)
assets/ (downloaded automatically)
+ Python files (downloaded automatically)

Version: {VERSION}
"""
        
        with open(os.path.join(release_folder, "README.txt"), "w", encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"\n{'='*60}")
        print(f"✓ AUTO-UPDATE EXE READY: {release_folder}")
        print(f"{'='*60}")
        print(f"\nYour exe is in: {release_folder}/")
        print(f"File: TOA-v{VERSION}.exe")
        print(f"Size: ~{os.path.getsize(f'{release_folder}/{exe_name}.exe') / (1024*1024):.1f} MB")
        print("\nDISTRIBUTION:")
        print("  1. Upload the .exe to GitHub releases")
        print("  2. Users download the exe")
        print("  3. Users run it - files download automatically!")
        print("\nFUTURE UPDATES:")
        print("  → Just push changes to GitHub")
        print("  → Users run game - updates download automatically")
        print("  → NO REBUILD NEEDED!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with error: {e}")
        return False
    except FileNotFoundError:
        print("\n✗ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("Please run this script again.")
        return False
    
    return True

if __name__ == "__main__":
    build_exe()
