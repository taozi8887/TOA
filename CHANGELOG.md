# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
