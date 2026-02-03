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

To share your game, distribute the entire `dist` folder or just the `TOA.exe` file. The exe is self-contained and includes:
- All Python dependencies
- Assets (images, sounds)
- Level data
- Autoplay script

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
