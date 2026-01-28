import json
import random
import os

def parse_osu_file(osu_filepath):
    """Parse .osu file and extract hit object timings, hitsounds, and metadata."""
    timings = []
    metadata = {}
    
    # Parse metadata and hit objects
    with open(osu_filepath, 'r', encoding='utf-8') as f:
        in_metadata = False
        in_hitobjects = False
        
        for line in f:
            line = line.strip()
            
            # Parse metadata section
            if line == '[Metadata]':
                in_metadata = True
                continue
            elif line.startswith('['):
                in_metadata = False
                if line == '[HitObjects]':
                    in_hitobjects = True
                    continue
            
            if in_metadata and ':' in line:
                key, value = line.split(':', 1)
                if key in ['Title', 'Artist', 'Creator', 'Version']:
                    metadata[key] = value.strip()
            
            # Parse hit objects section
            if in_hitobjects and line and not line.startswith('//'):
                parts = line.split(',')
                if len(parts) >= 5:
                    try:
                        timing_ms = int(parts[2])
                        hitsound = int(parts[4])  # Hitsound flags
                        
                        # Parse hitsound flags (bits 0-3)
                        has_normal = hitsound & 1 == 0  # Normal is default if no bits set
                        has_whistle = hitsound & 2
                        has_finish = hitsound & 4
                        has_clap = hitsound & 8
                        
                        timings.append({
                            'time': timing_ms,
                            'hitsound': hitsound,
                            'whistle': bool(has_whistle),
                            'finish': bool(has_finish),
                            'clap': bool(has_clap)
                        })
                    except (ValueError, IndexError):
                        continue
    
    return timings, metadata

def generate_level(timings):
    """Generate level data with random colors and boxes (min 2 tiles between repeats)."""
    level = []
    boxes = [0, 1, 2, 3]  # 0=top, 1=right, 2=bottom, 3=left
    colors = ['red', 'blue']
    
    # Track last 3 boxes to ensure at least 2 different tiles before repeat
    last_boxes = []
    
    for timing_obj in timings:
        # Convert milliseconds to seconds
        time_seconds = timing_obj['time'] / 1000.0
        
        # Random color
        color = random.choice(colors)
        
        # Exclude boxes that appeared in the last 2 positions
        # This ensures at least 2 different tiles before the same tile can repeat
        excluded_boxes = set()
        if len(last_boxes) >= 1:
            excluded_boxes.add(last_boxes[-1])
        if len(last_boxes) >= 2:
            excluded_boxes.add(last_boxes[-2])
        
        available_boxes = [b for b in boxes if b not in excluded_boxes]
        
        # Fallback: if somehow no boxes available (shouldn't happen with 4 boxes)
        if not available_boxes:
            available_boxes = [b for b in boxes if b != last_boxes[-1]]
        
        box = random.choice(available_boxes)
        
        # Update history
        last_boxes.append(box)
        if len(last_boxes) > 2:
            last_boxes.pop(0)
        
        level.append({
            "t": time_seconds,
            "box": box,
            "color": color,
            "hitsound": timing_obj.get('hitsound', 0),
            "whistle": timing_obj.get('whistle', False),
            "finish": timing_obj.get('finish', False),
            "clap": timing_obj.get('clap', False)
        })
    
    return level

def create_level_json(osu_filepath, output_filepath, seed=None):
    """Create a level JSON file from an .osu beatmap file."""
    if seed is not None:
        random.seed(seed)
    
    # Parse the .osu file
    print(f"Parsing {osu_filepath}...")
    timings, beatmap_metadata = parse_osu_file(osu_filepath)
    print(f"Found {len(timings)} hit objects")
    
    # Generate level data
    print("Generating level...")
    level = generate_level(timings)
    
    # Create metadata
    osu_filename = os.path.basename(osu_filepath)
    meta = {
        "source": osu_filename,
        "total_notes": len(level),
        "pattern": "random",
        "color_mode": "random",
        "seed": seed if seed is not None else "none",
        "title": beatmap_metadata.get('Title', 'Unknown'),
        "artist": beatmap_metadata.get('Artist', 'Unknown'),
        "creator": beatmap_metadata.get('Creator', 'Unknown'),
        "version": beatmap_metadata.get('Version', 'Unknown')
    }
    
    # Create final JSON structure
    output_data = {
        "meta": meta,
        "level": level
    }
    
    # Write to file
    print(f"Writing to {output_filepath}...")
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Successfully created level with {len(level)} notes!")

# Disabled for EXE build - this module is imported by main.py
# if __name__ == "__main__":
#     # Default input/output paths
#     osu_file = "temp_beatmap/Kensuke Ushio - Ping Pong Phase2 (Kanabis) [The Hero Appears!].osu"
#     output_file = "levels/levelpingpongfromosu.json"
#     
#     # You can change the seed for different random patterns
#     seed = 42
#     
#     create_level_json(osu_file, output_file, seed=seed)
