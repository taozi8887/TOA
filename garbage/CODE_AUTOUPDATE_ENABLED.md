# ✅ FULL CODE AUTO-UPDATE NOW ENABLED!

## What Changed

Your game now auto-updates **EVERYTHING**, including:
- ✅ **Python code** (main.py, osu_to_level.py, etc.)
- ✅ **Game logic and features**
- ✅ **Levels** (.json files)
- ✅ **Beatmaps** (audio, images, .osu files)

**You never need to rebuild the exe again!** Just push to GitHub and all users auto-update.

---

## How It Works Now

### Launcher System
Instead of running main.py directly, the exe now uses `launcher.py` which:
1. Checks GitHub for updates (code + content)
2. Downloads any changed Python files
3. Restarts if code was updated
4. Runs the game with latest code

### For End Users
**They do NOTHING.** Just run the exe:
```
User double-clicks TOA.exe
  ↓
Launcher checks for updates
  ↓
Downloads new code/content automatically
  ↓
Game starts with latest version
```

---

## Publishing Updates (Code OR Content)

### ANY change - same workflow:

```bash
# 1. Make your changes (edit main.py, add levels, whatever)

# 2. Generate version file
python generate_version.py

# 3. Commit and push
git add .
git commit -m "New feature: custom keybinds"
git push origin main
```

**Done!** All users get the update next time they launch. No rebuild needed.

---

## What Gets Auto-Updated

| Type | Auto-Updated? | Requires Rebuild? |
|------|---------------|-------------------|
| **main.py** | ✅ YES | ❌ NO |
| **osu_to_level.py** | ✅ YES | ❌ NO |
| **unzip.py** | ✅ YES | ❌ NO |
| **auto_updater.py** | ✅ YES | ❌ NO |
| **batch_process_osz.py** | ✅ YES | ❌ NO |
| **levels/*.json** | ✅ YES | ❌ NO |
| **beatmaps/*/** | ✅ YES | ❌ NO |
| **assets/** | ❌ NO | ✅ YES (rare) |
| **launcher.py** | ❌ NO | ✅ YES (rare) |

**Only rebuild exe if you change launcher.py or need new assets!**

---

## First-Time Setup

```bash
# 1. Install dependency (if not done)
pip install requests

# 2. Update config is already done ✅

# 3. Generate version file INCLUDING CODE
python generate_version.py

# 4. Commit
git add version.json update_config.json
git commit -m "Enable code auto-update"
git push origin main

# 5. Build exe (LAST TIME!)
python build_exe.py
```

---

## Configuration

Your `update_config.json` now has:
```json
{
  "auto_update": {
    "enabled": true,
    "update_code": true,  ← NEW! Enables code updates
    ...
  }
}
```

Set `"update_code": false` to disable code updates (content only).

---

## Examples

### Example 1: Add New Feature
```bash
# Edit main.py - add new game mode
vim main.py

# Generate version
python generate_version.py

# Push
git add main.py version.json
git commit -m "Add new game mode"
git push

# Users auto-download new main.py and see new feature!
```

### Example 2: Fix Bug
```bash
# Fix bug in main.py
vim main.py

python generate_version.py
git add main.py version.json
git commit -m "Fix scoring bug"
git push

# Bug fix auto-deploys to all users!
```

### Example 3: Add New Song
```bash
# Process new beatmap
python osu_to_level.py newsong.osz

python generate_version.py
git add levels/ beatmaps/ version.json
git commit -m "Add new song"
git push

# New song appears for all users!
```

---

## Building Executable (One Last Time)

```bash
python build_exe.py
```

This creates `TOA-v0.4.0.exe` with the **launcher** that auto-updates everything.

**After distributing this exe, you never need to rebuild again!**

---

## How Launcher Works

```
TOA.exe starts
  ↓
launcher.py runs
  ↓
Checks GitHub for updates
  ↓
Downloads changed .py files
  ↓
If code updated → Restart launcher
  ↓
Import and run main.py
  ↓
main.py shows loading screen
  ↓
Checks for content updates (levels/beatmaps)
  ↓
Downloads new content
  ↓
Game runs with latest everything!
```

---

## Advanced: Disable Code Updates

If you want content-only updates (safer for major changes):

Edit `update_config.json`:
```json
{
  "auto_update": {
    "update_code": false,  ← Disables code updates
    ...
  }
}
```

Then rebuild exe once more.

---

## Testing

```bash
# Test locally
python launcher.py

# Should check for updates then start game
```

---

## Benefits

### Before (Old System):
- Change code → Rebuild exe → Redistribute → Users download new exe
- 😓 Time-consuming
- 😓 Large downloads
- 😓 Users might miss updates

### Now (New System):
- Change code → Push to GitHub → Done! ✅
- ⚡ Instant deployment
- ⚡ Small downloads (only changed files)
- ⚡ All users auto-update

---

## Security Note

Code auto-update is safe because:
- Only YOUR GitHub repo is used
- SHA256 hash verification
- Users control which branch (stable/beta/dev)
- Can be disabled via config
- Git history tracks all changes

---

## Workflow Summary

```bash
# Every time you make ANY change:
python generate_version.py
git add .
git commit -m "description"
git push

# That's it! No rebuild needed!
```

---

**You now have FULL auto-update!** 🚀

Push code changes to GitHub and they auto-deploy to all users instantly!
