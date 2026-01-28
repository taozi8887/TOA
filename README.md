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
- **W** or **Up Arrow** - Hit top tiles
- **A** or **Left Arrow** - Hit left tiles
- **S** or **Down Arrow** - Hit bottom tiles
- **D** or **Right Arrow** - Hit right tiles
- **Left/Right Mouse Click** - Alternative control method
- **ESC (hold)** - Exit game

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

### Method 2: From Audio Files

Generate levels from any audio file using rhythm detection:
```bash
python song_to_level.py path/to/audio.mp3 --out levels/mylevel.json
```

Options:
- `--bpm` - Manually set BPM (auto-detected by default)
- `--quantize` - Note quantization (1/4, 1/8, 1/16)
- `--difficulty` - Difficulty level (0.5 to 2.0)
- `--pattern` - Tile pattern (random, alternating, wave)

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

## Advanced Features

### Random Tile Generation Rules
- Same tile cannot repeat consecutively
- Minimum of 2 different tiles between repeats (prevents patterns like 0-1-0-1)

### Slider Handling
osu! sliders are converted to single hits (slider repeats are currently disabled but can be re-enabled in `osu_to_level.py`)

### Autoplay Mode
Autoplay uses precise timing simulation with slight randomization for human-like gameplay.

## Troubleshooting

### "No module named 'pygame'"
```bash
pip install -r requirements.txt
```

### "FileNotFoundError: level.json"
Make sure level JSON files are in the `levels/` folder. Run:
```bash
python organize_levels.py
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
