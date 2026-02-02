# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-02-02

### Added
- **Auto-Update System** with GUI installer
  - Launcher pattern for code hot-swapping without rebuilding exe
  - Automatic update checks on every launch
  - GUI installer window (600x400) with progress bar and file information
  - Downloads only changed files to minimize bandwidth
  - Updates game code, levels, beatmaps, and assets from GitHub
  - First-run automatic installation of all game files
- **Hidden Console Window** for professional appearance
- **Hidden .toa folder** on Windows (contains runtime files)
- **Dynamic version reading** in build_exe.py from TOA.spec
- **Optimized update workflow** with update.py script
  - One-command push: `python update.py "commit message"`
  - Automatically updates version.json with only changed files
  - Uses GitHub raw URLs for hash calculation

### Changed
- Runtime level/beatmap generation from .osz files instead of pre-generated JSON
- Simplified update system to always sync with GitHub (no hash verification during updates)
- Removed redundant update check from main.py (launcher handles all updates)
- Removed auto-update test text overlay from gameplay

### Fixed
- Pygame DLL loading issues with pre-load strategy
- Path separator issues (standardized to forward slashes for cross-platform compatibility)
- Hash mismatch issues by calculating hashes from GitHub-served files
- Restart logic to prevent pygame temp directory issues

### Technical
- version.json tracks 26 files (5 Python files, 8 images, 13 .osz files)
- SHA256 hash verification for version tracking
- Supports extensions: .json, .osu, .mp3, .wav, .ogg, .jpg, .png, .osz
- Launcher shows GUI installer for first run and updates
- Console hidden via console=False in TOA.spec

## [0.4.0] - 2026-02-01

### Added
- **Comprehensive Settings System** with local storage (toa_settings.json)
  - Music volume slider (0-100%)
  - Hitsound volume slider with enable/disable toggle (0-100%)
  - Scroll speed slider (25-700, default 75)
  - Fade effects toggle for performance optimization
  - Keybind remapping for all gameplay keys (WASD)
  - Mouse button remapping (can map to keyboard keys)
  - Reset keybinds to default button
  - Duplicate keybind prevention
- Settings menu accessible from:
  - In-game via ESC key (pause)
  - Level selector via ESC key
  - Standalone mode
- **Performance Optimizations**
  - Image conversion (.convert() and .convert_alpha()) for all surfaces
  - Gradient surface caching for edge flashes
  - Optional fade effects toggle for lower-end systems
- **Confirmation Popups** with overlay system
  - Quit to menu confirmation
  - Quit game confirmation
  - Overlay darkens background instead of black screen
- **Always-visible mouse cursor** with hover states
  - Hand cursor on interactive elements (buttons, sliders, toggles)
  - Arrow cursor on non-interactive areas

### Changed
- **ESC key behavior**: Opens settings/pause menu instead of double-tap exit
- **In-game pause**: Shows "Quit to Menu" and "Quit Game" buttons (removed Resume)
- **Level selector ESC**: Opens settings instead of quitting directly
- **Keybind system**: Removed Space and Alt keys, kept WASD only
- **Mouse bindings**: Can now be mapped to keyboard keys in addition to mouse buttons
- Settings persist across game restarts via JSON file
- Scroll speed now adjustable from 25 to 700 (previously fixed at 75)

### Fixed
- Scroll speed slider now properly contains values within bounds
- Cursor states properly update in settings window
- Fade effects now apply to all transitions (loading, autoplay, game start)
- Confirmation popups overlay screen content properly

#
# ## [0.3.5] - 2026-01-30
#
# ### Added
# - Auto fade out song and return to level selector when level ends.
# - Updated accuracy windows:
#   - 300: <= 0.02s
#   - 100: <= 0.0475s
#   - 50:  <= 0.075s

## [0.3.4] - 2026-01-29

### Notes
- If you do not hear hitsounds on some maps, it is likely because the required hitsound files (e.g., soft-hitnormal0.ogg) are missing from the beatmap folder. This is not a code error; the game will play any hitsound file present that matches the note's hitsound index and type.

### Changed
- Audio file loading now supports multiple extensions: mp3, ogg, wav, flac, aac, m4a for both music and hitsounds. The game will use the first matching file found for each type.
- All old levels have been replaced with a new set of levels and songs.

#### New Songs (one or more levels each):
  - All The Things She Said — Seraphine
  - DRUM GO DUM feat. Aluna, Wolftyla, Bekuh BOOM — K/DA
  - GIANTS (feat. Becky G, Keke Palmer, SOYEON, DUCKWRTH, Thutmose) — True Damage
  - GODS feat. NewJeans — League of Legends
  - Misfit Toys — Pusha T & Mako
  - MORE feat. Madison Beer, (G)I-DLE, Lexie Liu, Jaira Burns, Seraphine — K/DA
  - POP/STARS (ft. Madison Beer, (G)I-DLE, Jaira Burns) — K/DA
  - RISE (ft. The Glitch Mob, Mako, and The Word Alive) — League of Legends
  - STAR WALKIN' — Lil Nas X
  - Take Over (feat. Jeremy McKinnon (A Day To Remember), MAX, Henry) (Cut Ver.) — League of Legends
  - THE BADDEST feat. (G)I-DLE, Bea Miller, Wolftyla — K/DA
  - VILLAIN feat. Madison Beer and Kim Petras — K/DA
  - Warriors — Imagine Dragons

## [0.3.3] - 2026-01-29

### Added
- Timing-driven box shake when a tile reaches its target box (independent of user input; still triggers on full misses/early misses).
- A short "spawn lockout" before a note can be judged, so clicks immediately on spawn don't get scored.

### Changed
- Tighter timing for a 300 judgment (more strict perfect window).

### Fixed
- Resolved remaining **hitsound**, **hitcheck**, and **ghost-click** edge cases (timing + audio feedback now consistent).
- Visual feedback (shake) no longer gets skipped when you miss early; it's driven by the level timing instead of the current-note pointer.

## [0.3.2] - 2026-01-28

### Changed
- Hitsounds now play correctly in autoplay mode
- Hitsounds only play on successful hits (not on misses)
- Hitsound volume set to 50%

### Fixed
- Ghost clicks and misses no longer trigger hitsounds
- Code cleanup for hitsound playback logic

## [0.3.1] - 2026-01-28

### Changed
- Hitsound playback latency reduced (lower audio buffer, more mixer channels)
- Hitsound volume set to 60% for all hitsounds
- Hitsounds now play more reliably on very fast note streams
- Autoplay popup now only accepts ESC, Y, or N keys (others ignored)
- Improved hitsound timing accuracy (closer to level timing)

### Fixed
- Fixed rare bug where hitsounds could be skipped on dense patterns
- Fixed minor visual/logic bugs in popup and shake feedback

## [0.3.0] - 2026-01-28

### Added
- Loading screen with progress bar that preloads all level assets
- Smooth fade transitions between all screens (level selector, autoplay prompt, game)
- Fade-in effect when game starts (1s fade with 0.3s delay for element rendering)
- Fade-in effect when returning to level selector from game
- Level selector now shows mouse cursor
- Autoplay prompt now hides mouse cursor
- Any key except 'Y' on autoplay prompt registers as 'No'
- ESC key on autoplay prompt returns to level selector

### Changed
- Application now maintains single window throughout (no reopening between screens)
- Level selector bars fully render before fade-in completes
- Level selector title moved down 15px for better spacing
- Fade durations optimized:
  - Level selector ↔ Autoplay: 0.5s
  - Autoplay → Game: 0.3s
  - Game → Level selector: 0.7s
  - Game fade-in: 1.0s (with 0.3s delay)
  - Loading screen transitions: 0.5s
- Miss timing synchronized to exact beat timings in level file
- Tile flashes now occur at exact timepoints (no longer delayed by accuracy window)
- Hit detection remains ±0.2s for player input flexibility

### Fixed
- Multiple windows opening when transitioning between screens
- Black screen flashing between transitions
- Level selector bars appearing instantly without smooth transition
- Tiles flashing 0.2s late on missed notes
- UnboundLocalError when pressing ESC on autoplay prompt
- Level selector content not fully loaded during fade-in when returning from game

### Technical
- Refactored pygame initialization to single instance
- Removed redundant pygame.quit() calls between screen transitions
- Added screen surface copying for smooth fade effects
- Preloading system caches all level metadata and background images
- Main loop now passes preloaded data to avoid redundant file I/O

## [0.2.1] - 2026-01-28

### Added
- The Big Black beatmap
- Blue Zenith beatmap
- fine night by goreshit beatmap
- envidia beatmap

### Removed
- pazolite beatmap (due to bugs)

## [0.2.0] - 2026-01-28

### Added
- Combo counter display with pop animation on successful hits
- Combo counter shake effect during animations
- Combo counter now always displays (including "0x" for zero combo)

### Fixed
- Autoplay mode missing notes due to overly strict timing window (20ms → removed frame-dependent timing)
- Approach indicators now travel at consistent speed regardless of direction (normalized travel distance)

### Changed
- Combo counter positioning: 30px from left edge, 130px from bottom
- Combo counter font size increased to 92pt
- Combo counter animation speed increased (duration reduced to 0.08s)
- Combo counter tilt removed (now displays upright)
- Approach indicators for all boxes now travel the same distance (half screen width)

## [0.1.0] - 2026-01-27

### Added
- Initial release
- Core rhythm game engine with WASD controls
- Level selector with scrollable list
- Autoplay mode
- Score, accuracy, and progress tracking
- 300/100/50 hit judgments
- Visual approach indicators with gradients
- Screen shake effects on hits/misses
- Pause functionality (P key)
- ESC double-press to return to level selector
- Mouse cursor visibility in level selector
- Version display in window title and file properties

### Features
- Fullscreen borderless window
- .osu beatmap file support
- Audio synchronization with 3-second countdown
- Dynamic accuracy windows for rapid note sequences
- Judgment text displays with fade animations
- Beatmap metadata display
- Background image support from beatmap folders
