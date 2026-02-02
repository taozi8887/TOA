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

# Version should match __version__ in main.py
VERSION = "0.4.1"

def build_exe():
    """Build the executable using PyInstaller with version info"""
    
    exe_name = f"TOA-v{VERSION}"
    
    # Use the TOA.spec file which has all the proper configuration
    print(f"\nBuilding {exe_name}.exe...")
    print("This may take a few minutes...")
    
    try:
        result = subprocess.run(['pyinstaller', 'TOA.spec'], check=True)
        print("\n✓ Build successful!")
        
        # Copy Python files to dist folder so they can be auto-updated
        dist_folder = "dist"
        python_files = ['main.py', 'osu_to_level.py', 'unzip.py', 'auto_updater.py', 'batch_process_osz.py']
        
        print("\nCopying Python files for auto-update...")
        for file in python_files:
            if os.path.exists(file):
                shutil.copy2(file, dist_folder)
                print(f"  Copied {file}")
        
        print(f"\n✓ Your executable is ready: dist/{exe_name}.exe")
        print("✓ Python files copied for auto-update support")
        
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
