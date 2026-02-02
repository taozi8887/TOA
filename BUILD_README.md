# Building TOA Executable

## Quick Start

### Method 1: Using build script (Recommended)
```bash
python build_exe.py
```

### Method 2: Using PyInstaller directly
```bash
pyinstaller TOA.spec
```

### Method 3: Simple one-liner
```bash
pyinstaller --onefile --add-data "assets;assets" --add-data "level.json;." --add-data "autoplay.py;." --name TOA main.py
```

## Installation

If PyInstaller is not installed:
```bash
pip install pyinstaller
```

## Output

The executable will be created in the `dist` folder:
- `dist/TOA.exe` - Your standalone game executable

## Distribution

To share your game, distribute just the `TOA.exe` file. The exe is self-contained and includes:
- Auto-update system
- Game launcher
- Update configuration

**Security Features:**
- Game files are stored in a hidden `.toa` folder with system attributes
- File names are never displayed during updates to protect integrity
- Users cannot access or modify game files during operation
- All game files are downloaded/updated automatically from GitHub

**On first run, the game will automatically:**
1. Create hidden `.toa` folder (invisible to users)
2. Download all game files (code, assets, levels)
3. Set folder as system + hidden for protection
4. Launch the game

**On subsequent runs:**
- Checks for updates automatically
- Downloads only changed files
- All operations are hidden from user view

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Module not found" errors
Make sure all requirements are installed:
```bash
pip install -r requirements.txt
```

### Missing files at runtime
Check that all necessary files are listed in the `datas` section of `TOA.spec`

### Autoplay not working
The exe uses `sys.executable` to run autoplay.py, which should work in the bundled version. If issues persist, the autoplay script is included in the bundle.

## Notes

- The build creates a console window for the input prompts (autoplay/fade toggles)
- First run may be slower as Windows Defender scans new executables
- The exe is typically 50-100MB due to embedded Python and dependencies
