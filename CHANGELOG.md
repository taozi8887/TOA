# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
