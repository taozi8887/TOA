"""
Minimal bootstrap launcher - just sets up paths and runs the real launcher from .toa
This file is bundled in the exe and never changes.
The real launcher.py in .toa can be updated.
"""
import os
import sys

# Get exe directory
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(exe_dir)

# Setup .toa folder
toa_folder = os.path.join(exe_dir, '.toa')

# If .toa doesn't exist, extract bundled launcher first time
if not os.path.exists(toa_folder) or not os.path.exists(os.path.join(toa_folder, 'launcher.py')):
    os.makedirs(toa_folder, exist_ok=True)
    # Extract bundled files for first run
    if getattr(sys, 'frozen', False):
        import shutil
        for filename in ['launcher.py', 'auto_updater.py', 'update_config.json']:
            bundled_file = os.path.join(sys._MEIPASS, filename)
            target_file = os.path.join(toa_folder, filename)
            if os.path.exists(bundled_file) and not os.path.exists(target_file):
                shutil.copy2(bundled_file, target_file)
                print(f"Extracted {filename}")

# CRITICAL: Prioritize .toa for ALL imports
sys.path.insert(0, toa_folder)
sys.path.insert(0, exe_dir)

# Now import and run the REAL launcher from .toa (which can be updated)
import launcher
launcher.main()
