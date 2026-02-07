# TOA - Rhythm Game

A rhythm game where tiles approach from screen edges and players must hit them at the right time. Supports custom beatmaps from osu! `.osz` files.

## Features

- **4-directional gameplay** - Tiles approach from left, right, top, and bottom
- **WASD or Arrow Key controls** - Hit corresponding directions when tiles reach target boxes
- **Mouse control support** - Click boxes with left/right mouse buttons
- **Autoplay mode** - Watch perfect gameplay or test new beatmaps
- **osu! beatmap support** - Import and play `.osz` beatmap files
- **Custom level generation** - Create levels from audio files or beatmaps
- **Real-time scoring** - Track accuracy, combo, and performance
- **Fullscreen borderless mode** - Immersive gameplay experience

## Installation

### Requirements
- Python 3.13 or higher
- Windows (tested), should work on other platforms

### Setup
1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Playing the Game
```bash
python main.py
```

The game will:
1. Ask if you want to enable autoplay (Y/N)
2. Load the configured level and audio
3. Start gameplay after a 3-second countdown

### Controls
- **W** - Select top square
- **A** - Select left square
- **S** - Select bottom square
- **D** - Select right square
- **Space** - Alternative select (can be used with WAD keys)
- **Left Click** - Hit red tiles
- **Right Click** - Hit blue tiles
- **P** - Pause/Resume
- **ESC (double press)** - Return to level selector

## Importing Custom Songpacks

TOA supports Etterna/StepMania songpacks in ZIP format! 

### How to Import Custom Songpacks

You can select any folder on your computer to load songpacks from:

1. **In the songpack or level selector, click "Set Folder"**
2. **Browse to your songpack folder** (where you keep your ZIPs)
3. **Confirm** - the game will reload and scan that folder
4. **All ZIPs in that folder** will appear as separate songpacks

Your custom folder works alongside the game's built-in packs - all appear in the same selector!

### Supported Formats
- Etterna/StepMania songpacks (.zip files)
- Chart formats: `.sm`, `.ssc`, `.dwi`
- Audio formats: `.mp3`, `.ogg`, `.wav`, `.flac`

### How It Works
- Click "Set Folder" button to choose where your songpacks are stored
- The game scans your chosen folder on startup
- ZIP files are automatically extracted and converted
- New maps added to your folder will be imported on next launch
- Each ZIP becomes its own separate songpack
- All packs work seamlessly with full metadata, previews, and gameplay features
- Your folder selection is saved permanently in game settings

## Creating Custom Levels

### Method 1: From osu! Beatmaps (.osz files)

1. Place your `.osz` file in the project folder
2. Run the conversion:
```bash
python convert_beatmap.py
```

Or edit `convert_beatmap.py` to process specific beatmaps:
```python
process_osz_to_level(
    osz_path="path/to/beatmap.osz",
    extract_name="beatmap_name",
    output_json="levels/levelname.json",
    seed=42
)
```

### Method 3: Direct Integration

Edit `main.py` to generate and play a beatmap:
```python
REGENERATE_LEVEL = True  # Set to True to regenerate
level_json, audio_dir = process_osz_to_level(
    "assets/beatmap.osz", 
    "beatmap_name", 
    "levels/levelname.json", 
    seed=42
)
main(level_json=level_json, audio_dir=audio_dir)
```

## Project Structure

```
toa/
├── main.py                 # Main game engine
├── autoplay.py            # Autoplay functionality
├── osu_to_level.py        # osu! beatmap parser
├── unzip.py               # .osz file extractor
├── convert_beatmap.py     # Beatmap conversion utility
├── song_to_level.py       # Audio-to-level generator
├── build_exe.py           # Executable builder
├── organize_levels.py     # Move JSON files to levels folder
├── requirements.txt       # Python dependencies
├── assets/                # Game assets (images, icons)
├── levels/                # Level JSON files
└── beatmaps/              # Extracted beatmap audio files
```

## Building Executable

To create a standalone `.exe`:

```bash
python build_exe.py [optional_name]
```

Examples:
```bash
python build_exe.py TOA
python build_exe.py MyCustomGame
```

The executable will be created in the `dist` folder with all necessary assets bundled.

## Level Format

Levels are stored as JSON files in the `levels/` folder:

```json
{
  "meta": {
    "source": "beatmap_name.osu",
    "total_notes": 500,
    "pattern": "random",
    "color_mode": "random"
  },
  "level": [
    {
      "t": 2.5,
      "box": 0,
      "color": "red"
    }
  ]
}
```

Where:
- `t` - Time in seconds
- `box` - Direction (0=top, 1=right, 2=bottom, 3=left)
- `color` - "red" or "blue"

## Configuration

Edit `main.py` to configure:

```python
# Choose which level to play
REGENERATE_LEVEL = False  # Use existing level
main(level_json="levels/mylevel.json", audio_dir="beatmaps/mybeatmap")

# Or regenerate from .osz
REGENERATE_LEVEL = True
```

## Gameplay Rules

- **Tiles spawn** from screen edges and approach target boxes
- **Top tiles** come from the left side
- **Bottom tiles** come from the right side  
- **Left/Right tiles** come from their respective sides
- **Hit timing window**: ±200ms for accuracy
- **Scoring**: 
  - 300 points (perfect timing)
  - 100 points (good timing)
  - 50 points (ok timing)
  - Miss (outside window)

## Troubleshooting

### "No module named 'pygame'"
```bash
pip install -r requirements.txt
```

### Audio not playing
- Verify `audio.mp3` exists in the beatmap folder
- Check that pygame mixer is properly initialized

### Executable issues
- Ensure all files are included via `build_exe.py`
- Check that levels and beatmaps folders exist before building

## Credits

- Built with pygame
- osu! beatmap format support
- Audio analysis using librosa and demucs

## License

This project is provided as-is for educational and personal use.
