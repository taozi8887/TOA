# Update Workflow - Step by Step

## For Developers (You)

### Step 1: Make Code Changes
Edit any Python files:
```python
# main.py
__version__ = "0.5.1"
# ... your changes ...
```

### Step 2: Push Update to GitHub
```powershell
python update.py "Fixed: bug in level loading"
```

**What this does:**
1. `git add main.py`
2. `git commit -m "Fixed: bug in level loading"`
3. `git push origin main` ← Files now on GitHub
4. `python generate_version_from_github.py` ← Downloads changed files from GitHub
5. Calculates SHA256 checksums for ONLY changed files
6. Updates `version.json` with new checksums
7. `git add version.json`
8. `git commit -m "Update version.json"`
9. `git push origin main` ← Updated version.json now on GitHub

**That's it!** Your job is done.

---

## For Users

### Their Process
```
User runs: TOA-v0.5.0.exe
        ↓
[AUTOMATIC] Checks GitHub for updates
        ↓
Compares remote version.json with local version.json
        ↓
Found 1 file with different checksum: main.py ← ONLY download this
        ↓
Shows progress: "Downloading updates (1/1)"
        ↓
Downloads ONLY main.py to .toa/ folder
        ↓
Detects code was updated
        ↓
Rebuilds EXE with new code
        ↓
Launches new EXE
        ↓
Game starts with your update ✓
```

---

## How Changed Files Are Detected

### Before (Local)
```json
version.json (in .toa/ folder):
{
  "files": {
    "code": {
      "main.py": "abc123def456..."  ← Old checksum
    }
  }
}
```

### After (Remote - GitHub)
```json
version.json (on GitHub):
{
  "files": {
    "code": {
      "main.py": "xyz789uvw012..."  ← New checksum (different!)
    }
  }
}
```

### Detection
```
Local checksum:  abc123def456
Remote checksum: xyz789uvw012
                 ❌ Different → DOWNLOAD NEEDED
```

Only files with mismatched checksums are downloaded. Everything else is skipped.

---

## Example: Multiple File Update

### You make changes to:
- `main.py` ← Code change
- `levels/level1.json` ← Content change

### You run:
```powershell
python update.py "Added new level, fixed bug"
```

### What happens:
1. Both files pushed to GitHub
2. `generate_version_from_github.py` downloads BOTH
3. Calculates checksums for BOTH
4. Updates `version.json` with ONLY these 2 files
5. Pushes new `version.json`

### User's experience:
```
Updates found: 2 files
  - main.py
  - levels/level1.json

Downloading updates (1/2): main.py
Downloading updates (2/2): levels/level1.json

Rebuilding EXE (code changed)...

✓ New version launching!
```

**Total time:** ~1 min (1 sec check, 30 sec download, 30 sec rebuild)

---

## What if Only Assets Change (No Code)?

### Scenario: You add a new image

### You edit:
- `assets/new_icon.png` ← Asset only

### You run:
```powershell
python update.py "Added new game icon"
```

### User's experience:
```
Updates found: 1 file
  - assets/new_icon.png

Downloading updates (1/1): assets/new_icon.png

✓ No code changes - launching game

Game starts immediately with new asset!
```

**Total time:** ~20 seconds (no EXE rebuild needed)

---

## What if Multiple Code Files Change?

### Scenario: You optimize audio processing

### You edit:
- `osu_to_level.py` ← Code change
- `batch_process_osz.py` ← Code change

### You run:
```powershell
python update.py "Optimized audio processing for better performance"
```

### What happens:
1. Both pushed to GitHub
2. `generate_version_from_github.py` gets both
3. Updates `version.json` with BOTH
4. Pushes new `version.json`

### User's experience:
```
Updates found: 2 files
  - osu_to_level.py
  - batch_process_osz.py

Downloading updates (1/2): osu_to_level.py
Downloading updates (2/2): batch_process_osz.py

⚠ Code changes detected - EXE will be rebuilt!

Rebuilding EXE...
✓ Rebuild successful!

✓ New version launching!
```

**Total time:** ~2 min (1 sec check, 30 sec download, 90 sec rebuild)

---

## Perfect Scenario: Your Workflow

### Day 1: Initial Release
```powershell
python build_exe.py
# Creates: releases/TOA-v0.5.0.exe
# Users download and run it
```

### Day 5: Minor Bug Fix
```powershell
# Edit main.py (fix bug)
# Edit version.json in code if needed
python update.py "Fixed: level loading race condition"
# Users run game → gets update automatically (1 min)
```

### Day 10: Add New Content
```powershell
# Add levels/new_song.json
# Add assets/new_beat.png
python update.py "Added new song 'Cosmic Journey'"
# Users run game → downloads only new files (30 sec)
```

### Day 15: Major Optimization
```powershell
# Edit main.py (optimize rendering)
# Edit osu_to_level.py (faster parsing)
python update.py "Performance: 60% faster level loading"
# Users run game → downloads + rebuilds (2 min)
```

**No manual steps. No user downloads. Automatic.**

---

## Troubleshooting

### Problem: User says "No update detected"

**Check 1: Did you run `python update.py`?**
```powershell
python update.py "Your message"
```
✓ Must do this, not just `git push`

**Check 2: Is `version.json` on GitHub?**
```
https://github.com/taozi8887/TOA/blob/main/version.json
```
✓ File must exist and contain updated checksums

**Check 3: Are checksums different?**
```json
{
  "files": {
    "code": {
      "main.py": "NEW_HASH_HERE"  ← Must be different from local
    }
  }
}
```

### Problem: User says "EXE didn't rebuild"

**Check:** Was a code file in the changed files list?
```
Changes detected:
  - assets/icon.png  ← Asset only = no rebuild ✓
  - levels/new.json  ← Content only = no rebuild ✓
  - main.py          ← Code = rebuild ✓
```

---

## Summary Table

| Action | Command | Time | Result |
|--------|---------|------|--------|
| Initial release | `python build_exe.py` | 5 min | EXE ready |
| Push update | `python update.py "msg"` | 30 sec | GitHub updated |
| User runs EXE | (automatic) | 1-2 min | Game updated |
| Check if working | Look at version/timestamp | instant | Verify |

---

## Key Points

✅ **Users don't download anything manually**
✅ **Only changed files are downloaded**
✅ **EXE rebuilds only for code changes**
✅ **Your workflow is: edit, push, done**
✅ **All detection is automatic**

That's the whole system in a nutshell!
