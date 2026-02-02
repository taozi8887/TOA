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

def build_exe(silent=False, update_mode=False):
    """
    Build the executable using PyInstaller with version info
    
    Args:
        silent: If True, suppress output (used for auto-updates)
        update_mode: If True, this is an update build and exe will be auto-launched
        
    Returns:
        Tuple of (success: bool, exe_path: str)
    """
    
    exe_name = f"TOA-v{VERSION}"
    release_folder = f"releases"
    
    # Use the TOA.spec file which has all the proper configuration
    if not silent:
        print(f"\nBuilding {exe_name}.exe...")
        print("This may take a few minutes...")
    else:
        print(f"[AUTO-UPDATE] Rebuilding {exe_name}.exe...")
    
    try:
        result = subprocess.run(['pyinstaller', 'TOA.spec'], check=True, 
                                capture_output=silent, text=True)
        if not silent:
            print("\n✓ Build successful!")
        else:
            print("[AUTO-UPDATE] ✓ Rebuild successful!")
        
        # Create release folder
        os.makedirs(release_folder, exist_ok=True)
        
        # Copy ONLY the exe to release folder
        exe_source = f"dist/{exe_name}.exe"
        exe_dest = os.path.join(release_folder, f"{exe_name}.exe")
        shutil.copy2(exe_source, exe_dest)
        
        if not silent:
            print(f"\n✓ Copied exe to {release_folder}")
        
        if not silent:
            print("\nAUTO-UPDATE MODE:")
            print("  ✓ launcher.py + auto_updater.py (bundled in exe)")
            print("  ✓ update_config.json (bundled in exe)")
            print("\nOn first run, the exe will automatically download:")
            print("  - All Python game files (main.py, etc.)")
            print("  - assets/ folder")
            print("  - levels/ folder")
            print("  - beatmaps/ folder")
            print("  - version.json")
            print("\nOn updates:")
            print("  - Detects code changes on GitHub")
            print("  - Rebuilds EXE automatically")
            print("  - Launches new EXE")
            print("  - Old EXE replaced!")
            
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

This first download may take 1-2 minutes.
Make sure you have an internet connection!

AUTO-UPDATE WITH EXE REBUILD:
Every time you launch the game:
✓ Checks GitHub for code updates
✓ If updates found, rebuilds the EXE automatically
✓ Launches the new EXE
✓ Old EXE automatically replaced

When you push updates to GitHub, users get them automatically!

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
            print(f"Size: ~{os.path.getsize(exe_dest) / (1024*1024):.1f} MB")
            print("\nDISTRIBUTION:")
            print("  1. Upload the .exe to GitHub releases")
            print("  2. Users download the exe")
            print("  3. Users run it - files download automatically!")
            print("\nFUTURE UPDATES:")
            print("  → Just push changes to GitHub")
            print("  → Users run game - EXE rebuilds automatically")
            print("  → EXE replaced with new version!")
        
        return (True, exe_dest)
        
    except subprocess.CalledProcessError as e:
        if not silent:
            print(f"\n✗ Build failed with error: {e}")
        else:
            print(f"[AUTO-UPDATE] ✗ Rebuild failed: {e}")
        return (False, None)
    except FileNotFoundError:
        if not silent:
            print("\n✗ PyInstaller not found. Installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            print("Please run this script again.")
        else:
            print("[AUTO-UPDATE] ✗ PyInstaller not found")
        return (False, None)

if __name__ == "__main__":
    success, exe_path = build_exe()
    sys.exit(0 if success else 1)
