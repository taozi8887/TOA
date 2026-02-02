# Professional Update System - GitHub Edition

Your game now uses a **Riot-Games-style update system** but powered entirely by GitHub. No CDN costs, no external infrastructure - just GitHub repos.

## 🎮 How It Works (Like Riot Client)

### Architecture
```
Launcher.exe (Lightweight, rarely updates)
    ↓
Checks GitHub for manifest.json
    ↓
Downloads only changed files in chunks
    ↓
Verifies with SHA256 hashes
    ↓
Runs main game from .toa folder
```

### Key Features

✅ **Manifest-Based Updates** - Only downloads what changed  
✅ **Chunked Downloads** - Large files downloaded in pieces with progress  
✅ **Hash Verification** - Every file verified for integrity  
✅ **Automatic Rollback** - Failed updates restore previous version  
✅ **Delta Patches** - Tracks what changed between versions  
✅ **Resume Support** - Failed downloads retry automatically  
✅ **Real-time Progress** - Shows file progress, speed, percentage  

## 📝 Workflow: Publishing Updates

### Step 1: Make Your Changes
```bash
# Edit your game code, add assets, etc.
# Update version in main.py:
__version__ = "0.6.0"
```

### Step 2: Generate Manifest
```bash
python generate_manifest.py
```

This creates:
- `manifest.json` - Enhanced manifest with file sizes, hashes, patches
- `version.json` - Legacy compatibility file

### Step 3: Push to GitHub
```bash
git add manifest.json version.json
git commit -m "Release v0.6.0"
git push origin main
```

**That's it!** Players get the update automatically next time they launch.

## 🔧 How Players Get Updates

1. **Player opens Launcher.exe**
2. Launcher checks GitHub for `manifest.json`
3. Compares with local `manifest.json` in `.toa/`
4. Downloads only changed files:
   - Shows progress bar
   - Shows download speed
   - Shows file being downloaded
   - Verifies each file with hash
5. **Automatic rollback if anything fails**
6. Launches game with updated files

## 📦 What Gets Downloaded

### Priority Order:
1. **Code files** (`.py` files) - Critical updates first
2. **Assets** (images, icons, etc.)
3. **Content** (`.osz` beatmaps, levels)

### Files Tracked:
- `main.py`, `osu_to_level.py`, `launcher.py`, `auto_updater.py`, etc.
- `assets/` folder (icons, images, .osz files)
- Future: `levels/`, `beatmaps/` if you add them

## 🛡️ Security & Integrity

### Hash Verification
Every file has a SHA256 hash in the manifest:
```json
{
  "files": {
    "code": {
      "main.py": {
        "hash": "abc123...",
        "size": 52428
      }
    }
  }
}
```

If hash doesn't match → **download fails → rollback to previous version**

### Automatic Backup
Before updating:
1. Backs up current files to `.toa/backup/`
2. Downloads and verifies new files
3. If success → delete backup
4. If failure → restore from backup

## 📊 Manifest Features

### Delta Patches
Manifest tracks what changed between versions:
```json
{
  "patches": {
    "from_0.5.0": {
      "description": "Patch from 0.5.0 to 0.6.0",
      "changed_files": ["main.py", "assets/icon.png"],
      "removed_files": ["deprecated.py"]
    }
  }
}
```

### Version Comparison
Smart version comparison: `0.10.0 > 0.9.5 > 0.9.0`

### Rollback Support
```json
{
  "rollback": {
    "previous_version": "0.5.0",
    "can_rollback": true
  }
}
```

## 💻 Technical Implementation

### Chunked Download with Progress
```python
# Downloads in 1MB chunks
# Shows real-time progress: "5.2 MB/s"
# Calculates percentage: "73%"
# Resumes if connection drops
```

### Retry Logic
- Each file gets **3 attempts**
- 2-second delay between retries
- Partial downloads cleaned up
- Failed files tracked separately

### File Structure
```
YourGame/
├── Launcher.exe           # Lightweight, checks GitHub
├── .toa/                  # Hidden folder with game
│   ├── manifest.json      # Current version info
│   ├── main.py           # Game code
│   ├── assets/           # Game assets
│   ├── backup/           # Rollback backup
│   └── update_config.json
```

## 🎯 Configuration

Edit `.toa/update_config.json`:
```json
{
  "auto_update": {
    "enabled": true,
    "github_username": "yourusername",
    "repository_name": "yourgame",
    "branch": "main",
    "update_on_startup": true,
    "update_code": true
  }
}
```

## 🚀 Publishing Best Practices

### Before Each Release:

1. **Update version** in `main.py`
2. **Run** `python generate_manifest.py`
3. **Test locally** - run launcher to verify
4. **Commit & push** manifest.json + version.json
5. **Tag release** (optional):
   ```bash
   git tag -a v0.6.0 -m "Release 0.6.0"
   git push origin v0.6.0
   ```

### What NOT to do:
❌ Don't manually edit `manifest.json` - use generator  
❌ Don't push without generating manifest  
❌ Don't change manifest format (breaks compatibility)  
❌ Don't remove `version.json` (legacy support)  

## 🔄 Backwards Compatibility

System supports both:
- **New**: `manifest.json` (enhanced features)
- **Old**: `version.json` (fallback for older clients)

Old clients still work, just miss new features like:
- Chunked downloads
- Rollback support
- Patch tracking
- Download speeds

## 📈 Comparison with Riot Client

| Feature | Riot Client | Your System |
|---------|-------------|-------------|
| CDN | Expensive cloud CDN | GitHub (free) |
| Launcher | Separate launcher | Separate launcher ✓ |
| Manifest | Custom format | JSON manifest ✓ |
| Delta patching | Binary diffs | File-level tracking ✓ |
| Chunked downloads | Yes | Yes ✓ |
| Hash verification | Yes | SHA256 ✓ |
| Rollback | Yes | Yes ✓ |
| Resume downloads | Yes | Yes ✓ |

## 🛠️ Advanced Usage

### Manual Rollback
If update breaks something:
```python
from auto_updater import AutoUpdater

updater = AutoUpdater("yourusername", "yourrepo")
updater._rollback_from_backup()
```

### Force Update
```python
# Delete local manifest to force full redownload
import os
os.remove('.toa/manifest.json')
# Next launch will redownload everything
```

### Custom Progress UI
```python
def my_progress(current_file, total_files, filename, downloaded, total):
    percent = (downloaded / total * 100) if total > 0 else 0
    print(f"File {current_file}/{total_files}: {percent:.1f}%")

updater.download_updates(files, progress_callback=my_progress)
```

## 🎉 Benefits

### For You (Developer):
- **Zero infrastructure costs** - just GitHub
- **Simple workflow** - generate manifest, push, done
- **Version history** - Git tracks everything
- **Easy rollback** - just revert commit

### For Players:
- **Fast updates** - only downloads changes
- **Reliable** - hash verification, auto-retry
- **Progress** - see exactly what's happening
- **Safe** - automatic rollback if problems

## 📞 Troubleshooting

### "Files failed to download"
- Check internet connection
- Verify GitHub repo is public
- Check `update_config.json` has correct repo name

### "Hash mismatch"
- File corrupted during download (auto-retries)
- If persists, regenerate manifest with `generate_manifest.py`

### "Update gets stuck"
- Close all game/launcher instances
- Delete `.toa/backup/` folder
- Restart launcher

### "Want to test without pushing to GitHub"
- Modify `raw_url` in `auto_updater.py` to point to local server
- Run: `python -m http.server 8000`
- Change `raw_url` to `http://localhost:8000`

---

**You now have professional-grade game updates powered by GitHub!** 🚀
