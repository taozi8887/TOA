# TOA Auto-Update Quick Reference

## 🚀 First-Time Setup (One Time Only)

```bash
# 1. Install dependency
pip install requests

# 2. Run setup wizard
python setup_auto_update.py

# 3. Test configuration
python test_auto_update.py

# 4. Commit to GitHub
git add update_config.json version.json auto_updater.py
git commit -m "Add auto-update system"
git push origin main

# 5. Rebuild executable
python build_exe.py
```

## 📦 Publishing New Content (Every Time)

```bash
# 1. Add your new levels/beatmaps
python osu_to_level.py path/to/newmap.osz

# 2. Generate version file
python generate_version.py

# 3. Commit and push
git add levels/ beatmaps/ version.json
git commit -m "Add new songs"
git push origin main

# That's it! Users auto-update on next launch 🎉
```

## ⚙️ Common Commands

| Command | Purpose |
|---------|---------|
| `python setup_auto_update.py` | Initial configuration |
| `python generate_version.py` | Create/update version.json |
| `python test_auto_update.py` | Test auto-update system |
| `python build_exe.py` | Build distributable executable |

## 📝 Configuration File Locations

| File | Purpose | Commit to Git? |
|------|---------|---------------|
| `update_config.json` | GitHub repo settings | ✅ Yes |
| `version.json` | File version tracking | ✅ Yes |
| `auto_updater.py` | Update engine code | ✅ Yes |
| `toa_settings.json` | User game settings | ❌ No (user-specific) |

## 🔧 Quick Fixes

### Auto-update not working?
```bash
# Check configuration
python test_auto_update.py

# Check if requests is installed
pip show requests

# Verify GitHub settings in update_config.json
```

### Disable auto-update temporarily?
Edit `update_config.json`:
```json
{
  "auto_update": {
    "enabled": false,
    ...
  }
}
```

### Force re-download everything?
Delete local `version.json`:
```bash
rm version.json
```
Next launch will download all files.

### Use different branch for testing?
Edit `update_config.json`:
```json
{
  "auto_update": {
    "branch": "beta",
    ...
  }
}
```

## 📊 What Gets Auto-Updated?

✅ **Yes (Auto-Updated)**
- Level JSON files (`levels/*.json`)
- Beatmap folders (`beatmaps/*/`)
- Audio files (`.mp3`, `.ogg`, `.wav`)
- Images (`.jpg`, `.png`)
- OSU files (`.osu`)

❌ **No (Requires New Build)**
- Game code (`main.py`)
- Game assets (`assets/`)
- Executable file
- Python scripts

## 🎯 Typical Workflow

```
Local Dev:
  Add content → Generate version → Test locally
                        ↓
                   Commit to Git
                        ↓
                    Push to GitHub
                        ↓
            Users auto-download on launch!
```

## 💡 Pro Tips

1. **Test branch**: Use `branch: "beta"` for testing updates
2. **Selective sync**: Remove directories from `directories_to_sync` to exclude them
3. **Version tracking**: Update version number in both `main.py` and `generate_version.py`
4. **Bandwidth**: Only changed files are downloaded (hash-based)
5. **Offline mode**: Game works fine without internet

## 📞 Troubleshooting Checklist

- [ ] Is `requests` installed? (`pip show requests`)
- [ ] Is `update_config.json` configured? (not "YOUR_GITHUB_USERNAME")
- [ ] Is `version.json` committed to GitHub?
- [ ] Is repository public? (or auth configured for private)
- [ ] Did you run `python generate_version.py` after adding content?
- [ ] Did you `git push` after generating version.json?
- [ ] Is game using correct branch? (check `update_config.json`)

## 🎓 Key Concepts

**SHA256 Hash**: Unique fingerprint of each file
- Same file = same hash
- Different file = different hash
- Used to detect changes

**version.json**: Master list of all files and their hashes
- Lives in GitHub repo root
- Auto-updated by `generate_version.py`
- Downloaded by game on startup

**update_config.json**: Your GitHub repository settings
- Tells game where to check for updates
- Can be disabled without breaking game
- Included in built executable

---

## 📚 Full Documentation

- `AUTO_UPDATE_README.md` - Complete guide
- `AUTO_UPDATE_SUMMARY.md` - Implementation details
- `ARCHITECTURE.md` - Visual diagrams

---

**Need Help?** Run `python test_auto_update.py` to diagnose issues!
