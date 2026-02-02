# 🚀 Quick Start - Professional Update System

## Your System Now Works Like Riot Games!

### What Changed?
✅ **Manifest-based updates** - only downloads what changed  
✅ **Chunked downloads** - shows real progress & speed  
✅ **Hash verification** - file integrity checking  
✅ **Auto rollback** - if update fails, restores previous version  
✅ **All powered by GitHub** - zero infrastructure costs!

---

## Publishing a New Update (3 Steps)

### 1. Update Version
Edit [main.py](main.py#L28):
```python
__version__ = "0.6.0"  # Change this
```

### 2. Generate Manifest
```bash
python generate_manifest.py
```
Creates: `manifest.json` + `version.json`

### 3. Push to GitHub
```bash
git add manifest.json version.json main.py assets/
git commit -m "Release v0.6.0"
git push
```

**Done!** Players get update on next launch.

---

## What Players See

```
Opening Launcher.exe...
Checking for updates...
Update available: v0.6.0 (Released: 2026-02-02)
Downloading: 5/12 files
  ↓ 15.2/24.8 MB (3.4 MB/s)
  [████████████░░░░░░░] 73%
Verifying files...
✓ Complete! Starting game...
```

---

## Files & Structure

```
YourGame/
├── Launcher.exe              # Lightweight launcher
├── manifest.json             # Version manifest (push to GitHub)
├── version.json              # Legacy support (push to GitHub)
├── generate_manifest.py      # Run before each release
│
└── .toa/                     # Hidden game folder
    ├── manifest.json         # Local version info
    ├── main.py              # Downloaded game code
    ├── assets/              # Downloaded assets
    ├── backup/              # Auto backup before updates
    └── update_config.json   # Update settings
```

---

## Configuration

[.toa/update_config.json](.toa/update_config.json):
```json
{
  "auto_update": {
    "enabled": true,
    "github_username": "taozi8887",
    "repository_name": "TOA",
    "branch": "main"
  }
}
```

---

## How It Works Under the Hood

### Update Flow:
```
1. Launcher checks GitHub for manifest.json
2. Compares versions (0.6.0 > 0.5.0?)
3. If newer:
   - Creates backup of current files
   - Downloads changed files in chunks
   - Verifies each file with SHA256 hash
   - If success: Update manifest, delete backup
   - If failure: Restore from backup
4. Launch game with updated files
```

### Manifest Structure:
```json
{
  "version": "0.6.0",
  "release_date": "2026-02-02",
  "files": {
    "code": {
      "main.py": {
        "hash": "abc123...",  // SHA256 hash
        "size": 52428         // bytes
      }
    },
    "assets": {
      "icon.png": {
        "hash": "def456...",
        "size": 5834
      }
    }
  },
  "patches": {
    "from_0.5.0": {
      "changed_files": ["main.py", "assets/icon.png"],
      "removed_files": []
    }
  }
}
```

---

## Key Features

### 1. Manifest-Based Updates
Only downloads files that changed between versions.  
Old: Download everything (100 MB)  
New: Download only changes (5 MB)

### 2. Chunked Downloads
Downloads large files in 1MB chunks:
- Shows real-time progress
- Displays download speed
- Can resume if interrupted

### 3. Hash Verification
Every file verified with SHA256:
- Wrong hash? Re-download automatically
- Corrupted file? Auto-rollback to previous version

### 4. Automatic Rollback
Update fails? Automatically restores previous version:
```
Downloading updates...
ERROR: Hash mismatch for main.py
Rolling back to v0.5.0...
✓ Restored previous version
```

### 5. Delta Patches
Tracks exactly what changed:
```json
"patches": {
  "from_0.5.0": {
    "changed_files": ["main.py"],
    "removed_files": ["deprecated.py"]
  }
}
```

---

## Troubleshooting

### "Files failed to download"
1. Check internet connection
2. Verify repo is public
3. Check GitHub username in config

### "Hash mismatch"
- File corrupted during download
- System auto-retries 3 times
- If still fails, auto-rollback

### Test locally without GitHub:
```bash
# Run local server
python -m http.server 8000

# Edit auto_updater.py temporarily:
self.raw_url = "http://localhost:8000"
```

---

## Comparison

| Feature | Before | After (Riot-style) |
|---------|--------|-------------------|
| Downloads | Full files every time | Only changed files |
| Progress | Simple counter | Chunked with speed |
| Verification | None | SHA256 hashes |
| Failed updates | Broken game | Auto-rollback |
| Size tracking | Estimate | Exact file sizes |
| Retry logic | Basic | 3 attempts per file |
| Backup | None | Auto before update |

---

## Commands

```bash
# Generate manifest before release
python generate_manifest.py

# Test update system
python launcher.py

# Force redownload everything
rm .toa/manifest.json
python launcher.py
```

---

## What's Tracked

✅ **Code files:** `main.py`, `osu_to_level.py`, `launcher.py`, etc.  
✅ **Assets:** `assets/*.png`, `assets/*.jpg`, `assets/osz/*.osz`  
✅ **Config:** `update_config.json`, `toa_settings.json`  

Files in `.toa/` folder:
- Hidden + System attributes (Windows)
- Auto-downloaded on first run
- Auto-updated on subsequent runs

---

## Publishing Checklist

Before each release:
- [ ] Update `__version__` in main.py
- [ ] Run `python generate_manifest.py`
- [ ] Test locally with launcher
- [ ] Commit manifest.json + version.json
- [ ] Push to GitHub
- [ ] (Optional) Create GitHub Release tag

**That's it!** Players automatically get updates. 🎉

---

## Full Documentation

See [UPDATE_SYSTEM_GUIDE.md](UPDATE_SYSTEM_GUIDE.md) for complete details.
