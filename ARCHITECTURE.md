# TOA Auto-Update System Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          GAME STARTUP                               │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LOADING SCREEN                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  "Loading TOA..."                                             │  │
│  │  [Fade in animation]                                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CHECK FOR UPDATES                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  "Checking for updates..."                                    │  │
│  │                                                                │  │
│  │  1. Fetch version.json from GitHub                           │  │
│  │  2. Compare with local version.json                          │  │
│  │  3. Identify changed files (SHA256 hash)                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────┬────────────────────────────┘
                 │                        │
        NO UPDATES FOUND          UPDATES AVAILABLE
                 │                        │
                 │                        ▼
                 │       ┌─────────────────────────────────────────────┐
                 │       │         DOWNLOAD UPDATES                    │
                 │       │  ┌───────────────────────────────────────┐  │
                 │       │  │ "Downloading updates... 3/10"         │  │
                 │       │  │ [████████░░░░░░░░] 45%                │  │
                 │       │  │ levels/newsong_Hard.json              │  │
                 │       │  │                                       │  │
                 │       │  │ • Download each changed file          │  │
                 │       │  │ • Show progress bar                   │  │
                 │       │  │ • Update local version.json           │  │
                 │       │  └───────────────────────────────────────┘  │
                 │       └─────────────────┬───────────────────────────┘
                 │                         │
                 └─────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LOAD LEVEL METADATA                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  "Loading levels... 15/42"                                    │  │
│  │  [████████████████████] 100%                                  │  │
│  │                                                                │  │
│  │  • Read all .json files from levels/                         │  │
│  │  • Load backgrounds from beatmaps/                           │  │
│  │  • Cache metadata                                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LEVEL SELECT MENU                              │
│                                                                     │
│  [Shows all levels including newly downloaded ones!]               │
└─────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
TOA/
├── main.py                      # Main game file (MODIFIED)
├── auto_updater.py              # Auto-update engine (NEW)
├── update_config.json           # Configuration (NEW)
├── version.json                 # Version tracking (NEW, generated)
├── setup_auto_update.py         # Setup wizard (NEW)
├── generate_version.py          # Version generator (NEW)
├── test_auto_update.py          # Test utility (NEW)
├── requirements.txt             # Dependencies (MODIFIED)
├── TOA.spec                     # PyInstaller spec (MODIFIED)
│
├── levels/                      # Auto-updated from GitHub
│   ├── song1_Easy.json
│   ├── song1_Hard.json
│   └── song2_Normal.json
│
└── beatmaps/                    # Auto-updated from GitHub
    ├── song1/
    │   ├── audio.mp3
    │   ├── background.jpg
    │   └── song.osu
    └── song2/
        ├── audio.mp3
        └── song.osu
```

## Update Publishing Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOU (Game Developer)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Add new levels/beatmaps to local folders                   │
│     $ python osu_to_level.py newmap.osz                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Generate version.json                                       │
│     $ python generate_version.py                               │
│                                                                 │
│     • Scans levels/ and beatmaps/                             │
│     • Calculates SHA256 hash of each file                     │
│     • Creates/updates version.json                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Commit to git                                               │
│     $ git add levels/ beatmaps/ version.json                   │
│     $ git commit -m "Add awesome new songs"                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Push to GitHub                                              │
│     $ git push origin main                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GITHUB REPOSITORY                          │
│                                                                 │
│  https://github.com/username/repo                              │
│  ├── version.json          (version info & hashes)             │
│  ├── levels/               (all level files)                   │
│  └── beatmaps/             (all beatmap folders)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    USERS' GAME CLIENTS                          │
│                                                                 │
│  Next time any user launches the game:                         │
│  1. Auto-updater fetches version.json from GitHub              │
│  2. Compares with local version.json                           │
│  3. Downloads new/changed files                                │
│  4. Users see new songs in level select!                       │
└─────────────────────────────────────────────────────────────────┘
```

## Version Comparison Logic

```
┌────────────────────────┐      ┌────────────────────────┐
│   LOCAL version.json   │      │  REMOTE version.json   │
│                        │      │     (from GitHub)      │
├────────────────────────┤      ├────────────────────────┤
│ version: "0.4.0"       │      │ version: "0.4.1"       │
│ files:                 │      │ files:                 │
│   levels/              │      │   levels/              │
│     song1.json: abc123 │ ──┐  │     song1.json: abc123 │ Same
│     song2.json: def456 │ ──┼─▶│     song2.json: xyz789 │ Changed!
│                        │   └─▶│     song3.json: new999 │ New!
└────────────────────────┘      └────────────────────────┘
                                          │
                                          ▼
                              ┌─────────────────────────┐
                              │   DOWNLOAD THESE:       │
                              │   • song2.json (updated)│
                              │   • song3.json (new)    │
                              └─────────────────────────┘
```

## Configuration Flow

```
update_config.json
─────────────────
{
  "auto_update": {
    "enabled": true,              ◄─── Turn on/off
    "github_username": "user",    ◄─── Your GitHub username
    "repository_name": "toa",     ◄─── Your repo name
    "branch": "main",             ◄─── Which branch
    "update_on_startup": true,    ◄─── When to check
    "directories_to_sync": [      ◄─── What to sync
      "levels",
      "beatmaps"
    ]
  }
}
       │
       ▼
┌──────────────────────────┐
│    auto_updater.py       │
│                          │
│  class AutoUpdater:      │
│    def __init__():       │
│      • Reads config      │
│      • Sets up URLs      │
│                          │
│    def check_updates():  │
│      • Fetch remote      │
│      • Compare local     │
│      • Return changes    │
│                          │
│    def download():       │
│      • Get each file     │
│      • Show progress     │
│      • Update local      │
└──────────────────────────┘
```

## Error Handling Strategy

```
                    Game Starts
                        │
                        ▼
              ┌──────────────────┐
              │ Try Auto-Update  │
              └─────────┬────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    SUCCESS         NETWORK        DOWNLOAD
    ✓               ERROR          ERROR
         │              │              │
         │              ▼              ▼
         │      ┌─────────────┐  ┌─────────────┐
         │      │Print warning│  │Print warning│
         │      │Continue game│  │Use local    │
         │      └─────────────┘  └─────────────┘
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ Load Local Files │
              │  Game Continues  │
              └──────────────────┘
                        │
                        ▼
                   ✓ Game Runs!
```

## Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR CONTROL                         │
├─────────────────────────────────────────────────────────┤
│  • Only YOU can commit to your GitHub repo              │
│  • Version file signed by git commit                    │
│  • SHA256 hashes verify file integrity                  │
│  • No code execution - only data files                  │
│  • Users download only what you publish                 │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  WHAT GETS UPDATED                      │
├─────────────────────────────────────────────────────────┤
│  ✓ Level JSON files     (.json)                         │
│  ✓ Beatmap folders      (directories)                   │
│  ✓ Audio files          (.mp3, .ogg, .wav)              │
│  ✓ Images               (.jpg, .png)                    │
│  ✓ OSU beatmap files    (.osu)                          │
│                                                          │
│  ✗ Game code            (not updated)                   │
│  ✗ Executable           (not updated)                   │
│  ✗ Python scripts       (not updated)                   │
└─────────────────────────────────────────────────────────┘
```

## Performance Characteristics

```
┌──────────────────────────┬─────────────────────────────┐
│        OPERATION         │          TIME               │
├──────────────────────────┼─────────────────────────────┤
│ Fetch version.json       │ ~0.5-2 seconds              │
│ Compare hashes           │ <0.1 seconds                │
│ Download 1 level file    │ ~0.1-0.5 seconds (tiny)     │
│ Download 1 beatmap       │ ~2-10 seconds (has audio)   │
│ Total for 5 new songs    │ ~10-50 seconds              │
└──────────────────────────┴─────────────────────────────┘

Network Efficiency:
• Only downloads changed files (not entire repo)
• Uses GitHub's CDN (fast worldwide)
• Parallel downloads possible (future enhancement)
• No unnecessary re-downloads (hash comparison)
```

## Development vs Production

```
┌─────────────────────────────────────────────────────────┐
│                  DEVELOPMENT MODE                       │
├─────────────────────────────────────────────────────────┤
│  $ python main.py                                       │
│                                                          │
│  • Auto-update available if requests installed          │
│  • Can test updates locally                             │
│  • Easy to disable via config                           │
│  • Direct file access                                   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  PRODUCTION MODE                        │
├─────────────────────────────────────────────────────────┤
│  $ pyinstaller TOA.spec                                 │
│  → Creates TOA-v0.4.0.exe                               │
│                                                          │
│  • Auto-updater compiled into exe                       │
│  • update_config.json bundled                           │
│  • requests library included                            │
│  • Users get seamless updates                           │
└─────────────────────────────────────────────────────────┘
```

---

This visual guide should help understand how all the pieces fit together!
