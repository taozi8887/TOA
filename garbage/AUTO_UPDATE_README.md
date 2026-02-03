# Auto-Update System for TOA

## Overview

The TOA game now includes an auto-update system that automatically downloads new levels and beatmaps from your GitHub repository. This means you can distribute a single executable, and users will automatically receive updates without needing to rebuild or redistribute the entire game.

## How It Works

1. **Version Tracking**: A `version.json` file tracks the hash of every level and beatmap file
2. **Update Check**: On game startup, the loading screen checks GitHub for updates
3. **Smart Download**: Only changed or new files are downloaded
4. **Seamless Integration**: Updates happen automatically during the loading screen

## Setup Instructions

### 1. Initial Setup

1. **Install the requests library** (if not already installed):
   ```bash
   pip install requests
   ```

2. **Update main.py with your GitHub info**:
   - Open `main.py`
   - Find the line: `updater = AutoUpdater("YOUR_GITHUB_USERNAME", "YOUR_REPO_NAME", "main")`
   - Replace `YOUR_GITHUB_USERNAME` with your GitHub username
   - Replace `YOUR_REPO_NAME` with your repository name
   - Change `"main"` to your branch name if different

3. **Generate initial version.json**:
   ```bash
   python generate_version.py
   ```

4. **Commit and push to GitHub**:
   ```bash
   git add version.json
   git commit -m "Add version tracking for auto-updates"
   git push origin main
   ```

5. **Rebuild your executable** with PyInstaller (if using):
   ```bash
   python build_exe.py
   ```

### 2. Publishing Updates

When you want to release new levels or beatmaps:

1. **Add your new files** to the `levels/` or `beatmaps/` directories

2. **Regenerate version.json**:
   ```bash
   python generate_version.py
   ```

3. **Commit and push**:
   ```bash
   git add levels/ beatmaps/ version.json
   git commit -m "Add new levels"
   git push origin main
   ```

4. **Done!** All users will automatically receive the updates next time they launch the game

## Features

- ✅ **Automatic Updates**: Users get new content without reinstalling
- ✅ **Smart Downloads**: Only downloads changed files
- ✅ **Progress Bar**: Visual feedback during download
- ✅ **Graceful Fallback**: Game works even if updates fail or internet is unavailable
- ✅ **No Breaking Changes**: Old executables continue working

## Files

- `auto_updater.py`: Core auto-update functionality
- `generate_version.py`: Utility to create version.json
- `version.json`: Tracks file versions (generated, should be committed to git)

## Technical Details

### Version File Format

The `version.json` file contains:
```json
{
  "version": "0.4.0",
  "files": {
    "levels": {
      "song_difficulty.json": "sha256_hash_here"
    },
    "beatmaps": {
      "songname/audio.mp3": "sha256_hash_here"
    }
  }
}
```

### Update Process

1. Game starts → Loading screen
2. Fetch remote `version.json` from GitHub
3. Compare with local `version.json`
4. Download any files with different hashes
5. Update local `version.json`
6. Continue with normal game loading

### Network Failure Handling

- If GitHub is unreachable, game continues without updates
- If a download fails, game uses existing local files
- Users can play offline without issues

## Configuration Options

### Custom Directories

To track additional directories, modify `generate_version.py`:

```python
create_version_file(directories=['levels', 'beatmaps', 'assets'], output_file='version.json')
```

### Different Branch

To pull from a different branch (e.g., 'beta'):

```python
updater = AutoUpdater("username", "repo", "beta")
```

### File Types

By default, these file types are tracked:
- `.json` (level files)
- `.osu` (beatmap files)
- `.mp3`, `.wav`, `.ogg` (audio files)
- `.jpg`, `.png` (images)

To add more types, edit `auto_updater.py` in the `create_version_file` function.

## Troubleshooting

### Updates not downloading?

1. Check your GitHub username/repo in `main.py`
2. Ensure `version.json` is committed and pushed to GitHub
3. Check that your repository is public (or properly authenticated for private repos)
4. Verify internet connection

### "requests library not installed" error?

Install it with:
```bash
pip install requests
```

Then rebuild your executable.

### Want to disable auto-updates temporarily?

In `main.py`, change:
```python
if AUTO_UPDATE_AVAILABLE:
```
to:
```python
if False:  # Temporarily disabled
```

## Building Executable with Auto-Update

When building with PyInstaller, the `requests` library will be automatically included. No special configuration needed.

Just run:
```bash
python build_exe.py
```

The built executable will include auto-update functionality!

## Best Practices

1. **Test First**: Test updates on a development machine before pushing
2. **Version Consistently**: Update the version number in `generate_version.py` to match `main.py`
3. **Commit Version File**: Always commit `version.json` after adding new content
4. **Keep Repository Clean**: Don't track unnecessary large files
5. **Use .gitignore**: Exclude build artifacts, but include levels and beatmaps

## Example Workflow

```bash
# 1. Create new levels
python osu_to_level.py path/to/beatmap.osz

# 2. Generate version file
python generate_version.py

# 3. Commit and push
git add levels/ beatmaps/ version.json
git commit -m "Added awesome new song"
git push

# 4. Users automatically get the update! 🎉
```

## Security Note

This system downloads files directly from your GitHub repository. Make sure:
- Your repository is under your control
- You review all changes before committing
- You don't accidentally commit sensitive information

## License

This auto-update system is part of the TOA project and follows the same license.
