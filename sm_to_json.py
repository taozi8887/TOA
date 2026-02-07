"""
Simple SM to JSON converter - for converting standalone .sm files
For song packs, use songpack_loader.py instead
"""

import json
import re
import random

def parse_sm_file(filepath):
    """Parse a StepMania .sm file and extract metadata and notes."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract metadata
    metadata = {}
    metadata['title'] = re.search(r'#TITLE:([^;]+);', content)
    metadata['artist'] = re.search(r'#ARTIST:([^;]+);', content)
    metadata['offset'] = re.search(r'#OFFSET:([^;]+);', content)
    metadata['bpms'] = re.search(r'#BPMS:([^;]+);', content)
    metadata['music'] = re.search(r'#MUSIC:([^;]+);', content)
    
    # Clean up metadata
    title = metadata['title'].group(1).strip() if metadata['title'] else "Unknown"
    artist = metadata['artist'].group(1).strip() if metadata['artist'] else "Unknown"
    offset = float(metadata['offset'].group(1).strip()) if metadata['offset'] else 0.0
    music = metadata['music'].group(1).strip() if metadata['music'] else "music.mp3"
    
    # Parse BPMs (format: beat=bpm,beat=bpm,...)
    bpm_data = []
    if metadata['bpms']:
        bpm_string = metadata['bpms'].group(1).strip()
        for bpm_entry in bpm_string.split(','):
            if '=' in bpm_entry:
                beat, bpm = bpm_entry.split('=')
                bpm_data.append((float(beat.strip()), float(bpm.strip())))
    
    if not bpm_data:
        bpm_data = [(0.0, 120.0)]  # Default BPM
    
    # Extract notes section
    notes_match = re.search(r'#NOTES:.*?:(.*?)^;', content, re.MULTILINE | re.DOTALL)
    if not notes_match:
        raise ValueError("No notes section found in SM file")
    
    notes_content = notes_match.group(1)
    
    # Split into measures (separated by commas)
    measures = []
    current_measure = []
    for line in notes_content.split('\n'):
        line = line.strip()
        # Skip comments and empty lines
        if line.startswith('//') or not line:
            continue
        if line == ',':
            if current_measure:
                measures.append(current_measure)
                current_measure = []
        elif re.match(r'^[0-9MKLF]+$', line):  # Line with note data
            current_measure.append(line)
    
    # Add last measure if not empty
    if current_measure:
        measures.append(current_measure)
    
    return {
        'title': title,
        'artist': artist,
        'offset': offset,
        'music': music,
        'bpm_data': bpm_data,
        'measures': measures
    }

def beat_to_time(beat, bpm_data, offset):
    """Convert a beat number to time in seconds."""
    # Find the appropriate BPM for this beat
    current_bpm = bpm_data[0][1]  # Start with first BPM
    time = 0.0
    last_beat = 0.0
    
    for bpm_beat, bpm in bpm_data:
        if beat >= bpm_beat:
            # Add time from last beat change to this one
            if bpm_beat > last_beat and current_bpm > 0:
                beats_elapsed = bpm_beat - last_beat
                time += (beats_elapsed * 60.0) / current_bpm
            last_beat = bpm_beat
            current_bpm = bpm
        else:
            break
    
    # Add remaining time
    if current_bpm > 0:
        beats_elapsed = beat - last_beat
        time += (beats_elapsed * 60.0) / current_bpm
    
    # Apply offset (SM offset is typically negative)
    return time + offset

def convert_sm_to_json(sm_filepath, json_filepath):
    """Convert a .sm file to the game's level JSON format."""
    data = parse_sm_file(sm_filepath)
    
    notes = []
    # Box mapping: left=0, top=1, bottom=2, right=3 (as specified by user)
    # SM format: left, down, up, right -> 0, 2, 1, 3 in our box system
    box_mapping = [0, 2, 1, 3]  # SM indices to game box indices
    colors = ['red', 'blue', 'yellow', 'green']
    
    for measure_idx, measure in enumerate(data['measures']):
        if not measure:
            continue
        
        rows_in_measure = len(measure)
        beats_per_row = 4.0 / rows_in_measure  # Each measure is 4 beats
        
        for row_idx, row in enumerate(measure):
            # Calculate beat position
            beat = measure_idx * 4.0 + row_idx * beats_per_row
            time = beat_to_time(beat, data['bpm_data'], data['offset'])
            
            # Parse the row (4 characters for dance-single)
            if len(row) >= 4:
                for col_idx in range(4):
                    note_type = row[col_idx]
                    
                    # 1 = regular note, 2/4 = hold/roll start
                    if note_type in ['1', '2', '4']:
                        box = box_mapping[col_idx]
                        
                        note = {
                            "t": round(time, 3),
                            "box": box,
                            "color": random.choice(colors),
                            "hitsound": 0,
                            "whistle": False,
                            "finish": False,
                            "clap": False
                        }
                        notes.append(note)
    
    # Sort notes by time
    notes.sort(key=lambda x: x['t'])
    
    # Create the level JSON structure
    level_json = {
        "meta": {
            "source": f"{sm_filepath}",
            "total_notes": len(notes),
            "pattern": "converted_from_sm",
            "color_mode": "random",
            "seed": 42,
            "title": data['title'],
            "artist": data['artist'],
            "creator": "SM Converter",
            "version": "Challenge"
        },
        "level": notes
    }
    
    # Write to JSON file
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(level_json, f, indent=2)
    
    print(f"Converted {len(data['measures'])} measures with {len(notes)} notes")
    print(f"Output written to: {json_filepath}")
    return level_json

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        sm_file = sys.argv[1]
        json_file = sys.argv[2] if len(sys.argv) > 2 else "testlevel.json"
        convert_sm_to_json(sm_file, json_file)
    else:
        # Default behavior
        convert_sm_to_json("test.sm", "testlevel.json")
