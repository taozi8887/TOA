"""
Batch process all .osz files in assets/osz directory
Creates level JSON files for all difficulties in each beatmap
"""

import os
import sys
from pathlib import Path
from unzip import read_osz_file
from osu_to_level import create_level_json

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()

def get_difficulty_name(osu_file_path):
    """Extract difficulty name from .osu file"""
    try:
        with open(osu_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
    except Exception as e:
        print(f"Error reading difficulty name: {e}")
    
    # Fallback to filename
    basename = os.path.basename(osu_file_path)
    if '[' in basename and ']' in basename:
        start = basename.rfind('[')
        end = basename.rfind(']')
        if start < end:
            return basename[start+1:end]
    
    return "Unknown"

def get_beatmap_metadata(osu_file_path):
    """Extract title and artist from .osu file"""
    title = "Unknown"
    artist = "Unknown"
    
    try:
        with open(osu_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Title:'):
                    title = line.split(':', 1)[1].strip()
                elif line.startswith('Artist:'):
                    artist = line.split(':', 1)[1].strip()
                
                if title != "Unknown" and artist != "Unknown":
                    break
    except Exception as e:
        print(f"Error reading metadata: {e}")
    
    return title, artist

def process_osz_files():
    """Process all .osz files in assets/osz directory"""
    
    # Create directories if they don't exist
    osz_dir = Path("assets/osz")
    beatmaps_dir = Path("beatmaps")
    levels_dir = Path("levels")
    
    osz_dir.mkdir(parents=True, exist_ok=True)
    beatmaps_dir.mkdir(exist_ok=True)
    levels_dir.mkdir(exist_ok=True)
    
    # Get all .osz files
    osz_files = list(osz_dir.glob("*.osz"))
    
    if not osz_files:
        print("No .osz files found in assets/osz/")
        return
    
    print(f"Found {len(osz_files)} .osz file(s)")
    print("=" * 70)
    
    for osz_path in osz_files:
        print(f"\nProcessing: {osz_path.name}")
        print("-" * 70)
        
        # Generate extract name from filename (without .osz extension)
        extract_name = osz_path.stem
        extract_name = sanitize_filename(extract_name)
        extract_dir = beatmaps_dir / extract_name
        
        # Check if beatmap folder already exists
        if extract_dir.exists():
            print(f"✓ Beatmap folder already exists: {extract_dir}")
        else:
            print(f"Creating new beatmap folder: {extract_dir}")
        
        # Extract the .osz file
        try:
            osu_files = read_osz_file(str(osz_path), str(extract_dir))
        except Exception as e:
            print(f"✗ Error extracting {osz_path.name}: {e}")
            continue
        
        if not osu_files:
            print(f"✗ No .osu files found in {osz_path.name}")
            continue
        
        print(f"Found {len(osu_files)} difficulty/difficulties")
        
        # Use the .osz filename as base name for JSON files
        base_name = sanitize_filename(extract_name)
        
        # Process each difficulty
        for i, osu_file in enumerate(osu_files, 1):
            difficulty = get_difficulty_name(osu_file)
            difficulty_safe = sanitize_filename(difficulty)
            
            # Create output JSON filename
            if len(osu_files) == 1:
                # Single difficulty - use base name only
                output_json = levels_dir / f"{base_name}.json"
            else:
                # Multiple difficulties - include difficulty name
                output_json = levels_dir / f"{base_name}_{difficulty_safe}.json"
            
            print(f"  [{i}/{len(osu_files)}] {difficulty}")
            
            # Check if level already exists
            if output_json.exists():
                print(f"      ✓ Level already exists: {output_json.name}")
                continue
            
            # Generate level JSON
            try:
                create_level_json(osu_file, str(output_json), seed=42)
                print(f"      ✓ Created: {output_json.name}")
            except Exception as e:
                print(f"      ✗ Error creating level: {e}")
                continue
        
        print()
    
    print("=" * 70)
    print("Batch processing complete!")
    print(f"Beatmaps directory: {beatmaps_dir.absolute()}")
    print(f"Levels directory: {levels_dir.absolute()}")

if __name__ == "__main__":
    try:
        process_osz_files()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
