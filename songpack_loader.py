"""
Song Pack Loader for TOA
Handles extraction and loading of song packs (ZIP files containing SM/SSC charts)
"""

import os
import json
import zipfile
import shutil
import re
from pathlib import Path

# --- audio length helpers (seconds) ---
import wave
from typing import Optional

def _parse_synchsafe_int(b: bytes) -> int:
    """Parse a 4-byte synchsafe int (ID3v2 size field)."""
    if len(b) != 4:
        return 0
    return ((b[0] & 0x7F) << 21) | ((b[1] & 0x7F) << 14) | ((b[2] & 0x7F) << 7) | (b[3] & 0x7F)

def _wav_length_seconds(path: str) -> Optional[float]:
    """Exact WAV duration via wave module."""
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return frames / float(rate)
    except Exception:
        return None

def _flac_length_seconds(path: str) -> Optional[float]:
    """
    FLAC duration from STREAMINFO metadata block.
    Works for standard FLAC files (fLaC + metadata blocks).
    """
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"fLaC":
                return None

            # Read metadata blocks until STREAMINFO (type 0) is found
            while True:
                header = f.read(4)
                if len(header) != 4:
                    return None

                is_last = (header[0] & 0x80) != 0
                block_type = header[0] & 0x7F
                block_len = (header[1] << 16) | (header[2] << 8) | header[3]

                block_data = f.read(block_len)
                if len(block_data) != block_len:
                    return None

                if block_type == 0 and block_len >= 18:  # STREAMINFO is 34 bytes, but we need first 18+
                    # STREAMINFO layout:
                    # [0:2] min blocksize, [2:4] max blocksize,
                    # [4:7] min framesize, [7:10] max framesize,
                    # [10:18] packed fields: sample rate (20), channels (3), bps (5), total samples (36)
                    packed = int.from_bytes(block_data[10:18], "big")
                    sample_rate = (packed >> 44) & ((1 << 20) - 1)
                    total_samples = packed & ((1 << 36) - 1)
                    if sample_rate <= 0:
                        return None
                    return total_samples / float(sample_rate)

                if is_last:
                    return None
    except Exception:
        return None

def _mp3_length_seconds(path: str) -> Optional[float]:
    """
    MP3 duration:
      - Skips ID3v2 tag if present
      - Finds first MPEG frame header to get bitrate / sample rate
      - If Xing/Info header exists, uses frame count for better VBR accuracy
      - Otherwise estimates via (audio_bytes * 8 / bitrate)
    """
    # Bitrate tables (kbps)
    # Keys: (mpeg_version_key, layer_number) where mpeg_version_key: 1 for MPEG1, 2 for MPEG2/2.5
    # layer_number: 1=Layer I, 2=Layer II, 3=Layer III
    BITRATES = {
        (1, 1): [None, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],  # MPEG1 L1
        (1, 2): [None, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],      # MPEG1 L2
        (1, 3): [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],       # MPEG1 L3
        (2, 1): [None, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],      # MPEG2/2.5 L1
        (2, 2): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],           # MPEG2/2.5 L2
        (2, 3): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],           # MPEG2/2.5 L3
    }

    # Sample rates by version_id bits (from MPEG header)
    # version_id: 3=MPEG1, 2=MPEG2, 0=MPEG2.5
    SAMPLE_RATES = {
        3: [44100, 48000, 32000],
        2: [22050, 24000, 16000],
        0: [11025, 12000, 8000],
    }

    try:
        file_size = os.path.getsize(path)
        with open(path, "rb") as f:
            # Skip ID3v2 if present
            head = f.read(10)
            if len(head) < 10:
                return None

            start_audio = 0
            if head[0:3] == b"ID3":
                tag_size = _parse_synchsafe_int(head[6:10])
                start_audio = 10 + tag_size
                f.seek(start_audio)

            # Strip ID3v1 at end (optional, 128 bytes)
            end_trim = 0
            try:
                if file_size >= 128:
                    f_end = open(path, "rb")
                    f_end.seek(file_size - 128)
                    tail = f_end.read(3)
                    f_end.close()
                    if tail == b"TAG":
                        end_trim = 128
            except Exception:
                end_trim = 0

            # Scan for first frame sync
            # Read in a small window; if the MP3 has junk before frames, we’ll crawl forward.
            max_scan = min(file_size, start_audio + 1024 * 1024)  # scan up to 1MB after ID3
            pos = start_audio

            while pos + 4 <= max_scan:
                f.seek(pos)
                b = f.read(4)
                if len(b) < 4:
                    return None

                # Frame sync: 11 bits set
                if b[0] == 0xFF and (b[1] & 0xE0) == 0xE0:
                    version_id = (b[1] >> 3) & 0x03  # 3,2,0 valid; 1 invalid
                    layer_id = (b[1] >> 1) & 0x03    # 3=Layer I, 2=Layer II, 1=Layer III, 0 invalid
                    protection_bit = b[1] & 0x01     # 0 => CRC present (2 bytes), 1 => no CRC

                    bitrate_idx = (b[2] >> 4) & 0x0F
                    sample_idx = (b[2] >> 2) & 0x03
                    if version_id == 1 or layer_id == 0 or bitrate_idx in (0, 0xF) or sample_idx == 3:
                        pos += 1
                        continue

                    # Map version -> table key
                    mpeg_version_key = 1 if version_id == 3 else 2  # MPEG1 vs MPEG2/2.5

                    # Map layer_id -> layer_number
                    # layer_id bits: 3=Layer I, 2=Layer II, 1=Layer III
                    layer_number = {3: 1, 2: 2, 1: 3}[layer_id]

                    br_list = BITRATES.get((mpeg_version_key, layer_number))
                    sr_list = SAMPLE_RATES.get(version_id)
                    if not br_list or not sr_list:
                        pos += 1
                        continue

                    bitrate_kbps = br_list[bitrate_idx]
                    if not bitrate_kbps:
                        pos += 1
                        continue

                    sample_rate = sr_list[sample_idx]
                    if sample_rate <= 0:
                        pos += 1
                        continue

                    bitrate_bps = float(bitrate_kbps) * 1000.0

                    # Try Xing/Info header (for better VBR accuracy).
                    # Need to jump past header + optional CRC + side info.
                    channel_mode = (b[3] >> 6) & 0x03  # 3 = mono
                    is_mono = (channel_mode == 3)
                    has_crc = (protection_bit == 0)

                    if layer_number == 3:  # Layer III only (where Xing is common)
                        if version_id == 3:  # MPEG1
                            side_info = 17 if is_mono else 32
                            samples_per_frame = 1152
                        else:  # MPEG2/2.5
                            side_info = 9 if is_mono else 17
                            samples_per_frame = 576
                    elif layer_number == 2:
                        side_info = 0
                        samples_per_frame = 1152
                    else:  # Layer I
                        side_info = 0
                        samples_per_frame = 384

                    xing_pos = pos + 4 + (2 if has_crc else 0) + side_info
                    if xing_pos + 8 <= file_size:
                        f.seek(xing_pos)
                        tag = f.read(4)
                        if tag in (b"Xing", b"Info"):
                            flags_bytes = f.read(4)
                            if len(flags_bytes) == 4:
                                flags = int.from_bytes(flags_bytes, "big")
                                total_frames = None
                                if flags & 0x0001:  # frames field present
                                    frames_bytes = f.read(4)
                                    if len(frames_bytes) == 4:
                                        total_frames = int.from_bytes(frames_bytes, "big")
                                if total_frames and sample_rate > 0:
                                    return (total_frames * samples_per_frame) / float(sample_rate)

                    # Fallback: estimate using bitrate (CBR-ish estimate)
                    audio_bytes = (file_size - end_trim) - pos
                    if audio_bytes <= 0:
                        return None
                    return (audio_bytes * 8.0) / bitrate_bps

                pos += 1

        return None
    except Exception:
        return None

def get_audio_length_seconds(path: Optional[str]) -> Optional[float]:
    """
    Return audio length in seconds (float) if we can determine it, else None.

    Priority:
      1) mutagen (best, if installed)
      2) wav (exact, built-in)
      3) flac (STREAMINFO parse)
      4) mp3 (Xing/Info if present, else bitrate estimate)
    """
    if not path:
        return None
    if not os.path.exists(path):
        return None

    # Try mutagen if available
    try:
        import mutagen  # type: ignore
        info = mutagen.File(path)
        if info is not None and getattr(info, "info", None) is not None and getattr(info.info, "length", None) is not None:
            return float(info.info.length)
    except Exception:
        pass

    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        return _wav_length_seconds(path)
    if ext == ".flac":
        return _flac_length_seconds(path)
    if ext == ".mp3":
        return _mp3_length_seconds(path)

    return None


def parse_dwi_file(filepath):
    """Parse a DanceWith Intensity (.dwi) file and extract metadata and notes."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract metadata (DWI format uses similar tag syntax)
    metadata = {}
    metadata['title'] = re.search(r'#TITLE:([^;]+);', content)
    metadata['artist'] = re.search(r'#ARTIST:([^;]+);', content)
    metadata['file'] = re.search(r'#FILE:([^;]+);', content)
    metadata['bpm'] = re.search(r'#BPM:([^;]+);', content)
    metadata['gap'] = re.search(r'#GAP:([^;]+);', content)  # DWI uses GAP instead of OFFSET
    metadata['cdtitle'] = re.search(r'#CDTITLE:([^;]+);', content)
    
    # Clean up metadata
    title = metadata['title'].group(1).strip() if metadata['title'] else "Unknown"
    artist = metadata['artist'].group(1).strip() if metadata['artist'] else "Unknown"
    music = metadata['file'].group(1).strip() if metadata['file'] else None
    
    # DWI uses GAP (milliseconds from start to first beat) instead of OFFSET (seconds)
    gap = float(metadata['gap'].group(1).strip()) if metadata['gap'] else 0.0
    offset = -gap / 1000.0  # Convert GAP (ms) to OFFSET (seconds), negative
    
    # Parse BPM - DWI can have simple BPM or CHANGEBPM
    bpm_data = []
    if metadata['bpm']:
        bpm_string = metadata['bpm'].group(1).strip()
        bpm = float(bpm_string)
        bpm_data.append((0.0, bpm))
    
    # Check for BPM changes (#CHANGEBPM:beat=bpm,beat=bpm)
    changebpm = re.search(r'#CHANGEBPM:([^;]+);', content)
    if changebpm:
        changebpm_string = changebpm.group(1).strip()
        for bpm_entry in changebpm_string.split(','):
            if '=' in bpm_entry:
                beat, bpm = bpm_entry.split('=')
                bpm_data.append((float(beat.strip()) / 4.0, float(bpm.strip())))  # DWI uses 48th notes
    
    if not bpm_data:
        bpm_data = [(0.0, 120.0)]  # Default BPM
    
    # Background image
    background = metadata['cdtitle'].group(1).strip() if metadata['cdtitle'] else None
    
    # Extract all charts/difficulties
    # DWI format: #SINGLE:DIFFICULTY:RATING:
    charts = []
    
    # Find all chart sections
    chart_pattern = r'#(SINGLE|DOUBLE|COUPLE|SOLO):([^:]+):([^:]+):\s*([^#]+)'
    chart_matches = re.finditer(chart_pattern, content)
    
    for match in chart_matches:
        mode = match.group(1)  # SINGLE, DOUBLE, etc.
        difficulty = match.group(2).strip()  # BASIC, ANOTHER, MANIAC, etc.
        rating = match.group(3).strip()
        note_data = match.group(4).strip()
        
        if note_data and mode == 'SINGLE':  # Only process SINGLE mode for now
            chart = parse_dwi_chart(note_data, difficulty, rating)
            if chart['measures']:
                charts.append(chart)
    
    return {
        'title': title,
        'subtitle': "",
        'artist': artist,
        'offset': offset,
        'music': music,
        'background': background,
        'bpm_data': bpm_data,
        'charts': charts,
        'difficulty': ""
    }


def parse_dwi_chart(note_data, difficulty, rating):
    """Parse DWI note data into measures."""
    # DWI uses a different encoding - compressed format with special characters
    # Format: Each line/group represents steps, with special characters for timing
    # ! = 1/48th note extension
    # ( and ) = group boundaries
    # Numbers: arrows (1=down-left, 2=down, 3=down-right, 4=left, 6=right, 7=up-left, 8=up, 9=up-right)
    # Letters: combinations (A=left+right, B=up+down, etc.)
    
    measures = []
    current_measure = []
    
    # Remove parentheses and newlines for easier parsing
    note_data = note_data.replace('(', '').replace(')', '').replace('\n', '').replace('\r', '')
    
    # Split by known measure markers or parse as continuous stream
    # For now, we'll parse basic patterns and convert to 4-panel arrows
    # This is a simplified parser - full DWI parsing is complex
    
    # Convert DWI note characters to arrow indices
    # Standard 4-panel: 0=left, 1=down, 2=up, 3=right
    dwi_to_arrow = {
        '4': [0],      # left
        '2': [1],      # down
        '8': [2],      # up
        '6': [3],      # right
        'A': [0, 3],   # left+right
        'B': [1, 2],   # down+up
        '0': [],       # empty/rest
    }
    
    # Simple parsing: treat each character group as a note
    i = 0
    measure_length = 16  # Assume 16th notes
    current_notes = []
    
    while i < len(note_data):
        char = note_data[i]
        
        # Skip spaces and special markers
        if char in [' ', '<', '>', '!', "'", '`']:
            i += 1
            continue
        
        # Check if it's a note character
        if char in dwi_to_arrow or char.isdigit() or char.isalpha():
            arrows = dwi_to_arrow.get(char, [])
            if arrows or char == '0':
                note_entry = [0, 0, 0, 0]
                for arrow in arrows:
                    note_entry[arrow] = 1
                current_notes.append(note_entry)
                
                # Group into measures (every 16 notes = 1 measure)
                if len(current_notes) >= measure_length:
                    measures.append(current_notes[:measure_length])
                    current_notes = current_notes[measure_length:]
        
        i += 1
    
    # Add remaining notes as final measure
    if current_notes:
        # Pad to measure length
        while len(current_notes) < measure_length:
            current_notes.append([0, 0, 0, 0])
        measures.append(current_notes)
    
    return {
        'style': 'dance-single',
        'difficulty': difficulty,
        'rating': int(rating) if rating.isdigit() else 0,
        'measures': measures
    }


def parse_sm_or_ssc_file(filepath):
    """Parse a StepMania .sm or .ssc file and extract metadata and notes."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract metadata
    metadata = {}
    metadata['title'] = re.search(r'#TITLE:([^;]+);', content)
    metadata['subtitle'] = re.search(r'#SUBTITLE:([^;]+);', content)
    metadata['artist'] = re.search(r'#ARTIST:([^;]+);', content)
    metadata['offset'] = re.search(r'#OFFSET:([^;]+);', content)
    metadata['bpms'] = re.search(r'#BPMS:([^;]+);', content)
    metadata['music'] = re.search(r'#MUSIC:([^;]+);', content)
    metadata['background'] = re.search(r'#BACKGROUND:([^;]+);', content)
    metadata['difficulty'] = re.search(r'#DIFFICULTY:([^;]+);', content)
    
    # Clean up metadata
    title = metadata['title'].group(1).strip() if metadata['title'] else "Unknown"
    subtitle = metadata['subtitle'].group(1).strip() if metadata['subtitle'] else ""
    artist = metadata['artist'].group(1).strip() if metadata['artist'] else "Unknown"
    offset = float(metadata['offset'].group(1).strip()) if metadata['offset'] else 0.0
    music = metadata['music'].group(1).strip() if metadata['music'] else None
    background = metadata['background'].group(1).strip() if metadata['background'] else None
    difficulty = metadata['difficulty'].group(1).strip() if metadata['difficulty'] else "Unknown"
    
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
    
    # Extract all charts/difficulties
    # SSC files use #NOTEDATA: followed by individual tags, then #NOTES:
    # SM files use #NOTES: followed by inline metadata
    charts = []
    
    # Check if this is SSC format (has #NOTEDATA:)
    if '#NOTEDATA:' in content:
        # SSC format - split by #NOTEDATA:
        notedata_sections = content.split('#NOTEDATA:')
        for section in notedata_sections[1:]:
            chart = parse_ssc_chart_section(section)
            if chart and chart['measures']:
                charts.append(chart)
    else:
        # SM format - split by #NOTES:
        notes_sections = content.split('#NOTES:')
        for section in notes_sections[1:]:
            chart = parse_sm_chart_section(section)
            if chart and chart['measures']:
                charts.append(chart)
    
    return {
        'title': title,
        'subtitle': subtitle,
        'artist': artist,
        'offset': offset,
        'music': music,
        'background': background,
        'bpm_data': bpm_data,
        'charts': charts,
        'difficulty': difficulty
    }

def parse_ssc_chart_section(chart_content):
    """Parse a single chart section from SSC file (uses #NOTEDATA: format)."""
    # SSC format has individual tags like #STEPSTYPE:, #DIFFICULTY:, #METER:, etc.
    # Extract difficulty and meter
    difficulty_match = re.search(r'#DIFFICULTY:([^;]+);', chart_content)
    meter_match = re.search(r'#METER:([^;]+);', chart_content)
    stepstype_match = re.search(r'#STEPSTYPE:([^;]+);', chart_content)
    
    difficulty = difficulty_match.group(1).strip() if difficulty_match else "Unknown"
    rating = int(meter_match.group(1).strip()) if meter_match else 0
    chart_type = stepstype_match.group(1).strip() if stepstype_match else "dance-single"
    
    # Find the #NOTES: section within this NOTEDATA block
    notes_match = re.search(r'#NOTES:\s*\n(.*?)(?:#[A-Z]+:|$)', chart_content, re.DOTALL)
    if not notes_match:
        return None
    
    note_data = notes_match.group(1)
    measures = parse_note_measures(note_data)
    
    return {
        'type': chart_type,
        'difficulty': difficulty,
        'rating': rating,
        'measures': measures
    }

def parse_sm_chart_section(chart_content):
    """Parse a single chart section from SM file (inline metadata format)."""
    lines = chart_content.split('\n')

def parse_sm_chart_section(chart_content):
    """Parse a single chart section from SM file (inline metadata format)."""
    lines = chart_content.split('\n')
    
    # Extract chart metadata - first few lines before note data
    # Format:
    #      chart_type:
    #      description:
    #      difficulty:
    #      rating:
    #      groove_radar_values:
    chart_info = []
    
    for line in lines[:20]:  # Check first 20 lines for metadata
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('//'):
            continue
        
        # Look for lines ending with colon (metadata lines)
        if line.endswith(':'):
            # Remove colon and whitespace
            value = line.rstrip(':').strip()
            if value:  # Not empty
                chart_info.append(value)
            else:  # Empty line with just colon (description line)
                chart_info.append("")
        
        # Stop when we hit note data
        if re.match(r'^[0-9MKLF]{4}$', line):
            break
    
    # Chart type, description, difficulty name, difficulty number, etc.
    chart_type = chart_info[0] if len(chart_info) > 0 else "dance-single"
    difficulty = chart_info[2] if len(chart_info) > 2 else "Unknown"
    rating = int(chart_info[3]) if len(chart_info) > 3 and chart_info[3].isdigit() else 0
    
    # Extract note data starting from where we find the first note line
    note_data = '\n'.join(lines)
    measures = parse_note_measures(note_data)
    
    return {
        'type': chart_type,
        'difficulty': difficulty,
        'rating': rating,
        'measures': measures
    }

def parse_note_measures(note_data):
    """Parse note data into measures (common for both SM and SSC)."""
    measures = []
    current_measure = []
    found_first_note = False
    
    lines = note_data.split('\n')
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip comment-only lines
        if line.startswith('//'):
            continue
        
        # Check if this is note data (4 digits for dance-single)
        if re.match(r'^[0-9MKLF]{4}$', line):
            found_first_note = True
            current_measure.append(line)
        elif found_first_note:
            # Once we've found notes, check for measure/chart endings
            # Commas can have comments after them like ",  // measure 1"
            if line.startswith(','):
                # End of measure
                if current_measure:
                    measures.append(current_measure)
                    current_measure = []
            elif line.startswith(';'):
                # End of chart
                if current_measure:
                    measures.append(current_measure)
                break
    
    return measures

def beat_to_time(beat, bpm_data, offset):
    """Convert a beat number to time in seconds."""
    current_bpm = bpm_data[0][1]
    time = 0.0
    last_beat = 0.0
    
    for bpm_beat, bpm in bpm_data:
        if beat >= bpm_beat:
            if bpm_beat > last_beat and current_bpm > 0:
                beats_elapsed = bpm_beat - last_beat
                time += (beats_elapsed * 60.0) / current_bpm
            last_beat = bpm_beat
            current_bpm = bpm
        else:
            break
    
    if current_bpm > 0:
        beats_elapsed = beat - last_beat
        time += (beats_elapsed * 60.0) / current_bpm
    
    return time - offset  # Negative offset means audio plays earlier, so notes should be later

def convert_chart_to_json(sm_data, chart, colors=['red', 'blue']): #, 'yellow', 'green']):
    """Convert a single chart to the game's level JSON format."""
    import random
    
    notes = []
    # Box mapping: left=0, down=2, up=1, right=3
    # For 4-key charts (dance-single)
    box_mapping = [0, 2, 1, 3]
    
    for measure_idx, measure in enumerate(chart['measures']):
        if not measure:
            continue
        
        rows_in_measure = len(measure)
        beats_per_row = 4.0 / rows_in_measure
        
        for row_idx, row in enumerate(measure):
            beat = measure_idx * 4.0 + row_idx * beats_per_row
            time = beat_to_time(beat, sm_data['bpm_data'], sm_data['offset'])
            
            # Parse the row
            num_columns = len(row)
            for col_idx in range(min(num_columns, 4)):
                note_type = row[col_idx]
                
                # 0 = empty, 1 = regular note, 2 = hold head, 3 = hold/roll tail
                # 4 = roll head, M = mine, K/L/F = other types
                if note_type in ['1', '2', '4']:
                    box = box_mapping[col_idx] if col_idx < len(box_mapping) else col_idx
                    
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
    
    notes.sort(key=lambda x: x['t'])
    return notes

def extract_songpack(zip_path, extract_to='songpacks/extracted'):
    """
    Extract a song pack ZIP file.
    
    Returns: Dict with pack info and list of level folders
    """
    # Convert to absolute path to ensure consistent path storage
    extract_to = os.path.abspath(extract_to)
    
    pack_name = Path(zip_path).stem
    pack_dir = os.path.join(extract_to, pack_name)
    
    # Check if already extracted
    if os.path.exists(pack_dir):
        print(f"Pack '{pack_name}' already extracted, skipping...")
    else:
        # Extract ZIP
        os.makedirs(pack_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(pack_dir)
        
        print(f"Extracted '{pack_name}'")
    
    # Handle nested folder structure (common in song packs)
    # If there's only one folder at the root, use that as the actual pack dir
    items_in_pack = os.listdir(pack_dir)
    if len(items_in_pack) == 1 and os.path.isdir(os.path.join(pack_dir, items_in_pack[0])):
        pack_dir = os.path.join(pack_dir, items_in_pack[0])
    
    # Find pack cover image (PNG or JPG in root, not in song folders)
    pack_image = None
    for file in os.listdir(pack_dir):
        file_path = os.path.join(pack_dir, file)
        file_lower = file.lower()
        # Only look at files, not directories
        if os.path.isfile(file_path) and (file_lower.endswith('.png') or file_lower.endswith('.jpg') or file_lower.endswith('.jpeg')):
            pack_image = file_path
            break
    
    # Recursively find level folders (folders containing .sm, .ssc, or .dwi files)
    levels = []
    
    def scan_for_levels(directory):
        """Recursively scan for folders containing SM/SSC/DWI files."""
        try:
            # Use os.scandir for more reliable directory reading
            with os.scandir(directory) as entries:
                items = [(entry.name, entry.path, entry.is_dir()) for entry in entries]
            
            for item_name, item_path, is_dir in items:
                if not is_dir:
                    continue
                
                # Check if this folder contains SM/SSC/DWI files
                sm_file = None
                ssc_file = None
                dwi_file = None
                audio_file = None
                bg_file = None  # For in-game background
                bn_file = None  # For level box thumbnail
                
                try:
                    with os.scandir(item_path) as file_entries:
                        files = [(e.name, e.path, e.is_file()) for e in file_entries]
                except Exception as e:
                    print(f"Error reading {item_path}: {e}")
                    continue
                
                for file_name, file_path, is_file in files:
                    if not is_file:
                        continue
                        
                    file_lower = file_name.lower()
                    file_base = os.path.splitext(file_lower)[0]
                    file_ext = os.path.splitext(file_lower)[1]
                    
                    if file_lower.endswith('.sm'):
                        sm_file = file_path
                    elif file_lower.endswith('.ssc'):
                        ssc_file = file_path
                    elif file_lower.endswith('.dwi'):
                        dwi_file = file_path
                    elif file_lower.endswith(('.mp3', '.ogg', '.wav', '.flac')):
                        audio_file = file_path
                    # In-game background (any file containing 'bg' with image extension)
                    elif 'bg' in file_base and file_ext in ['.png', '.jpg', '.jpeg']:
                        bg_file = file_path
                    # Level box thumbnail (any file containing 'bn' with image extension)
                    elif 'bn' in file_base and file_ext in ['.png', '.jpg', '.jpeg']:
                        bn_file = file_path
                
                if sm_file or ssc_file or dwi_file:
                    levels.append({
                        'folder': item_path,
                        'name': item_name,
                        'audio': audio_file,
                        'sm_file': sm_file,
                        'ssc_file': ssc_file,
                        'dwi_file': dwi_file,
                        'background': bg_file,  # In-game background
                        'thumbnail': bn_file  # Level box thumbnail
                    })
                else:
                    # Recurse into subdirectories
                    scan_for_levels(item_path)
        except Exception as e:
            print(f"Error scanning {directory}: {e}")
            import traceback
            traceback.print_exc()
    
    scan_for_levels(pack_dir)
    
    return {
        'pack_name': pack_name,
        'pack_image': pack_image,
        'levels': levels
    }

def convert_level_to_json(level_info, output_dir='levels'):
    """
    Convert a level from a song pack to JSON format(s).
    Supports .ssc, .sm, and .dwi files (priority: SSC > SM > DWI)
    Falls back to other files to fill in missing metadata
    
    Returns: List of created JSON file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse all available files to merge metadata
    all_chart_data = []
    
    # Parse in priority order: SSC > SM > DWI
    if level_info.get('ssc_file'):
        try:
            data = parse_sm_or_ssc_file(level_info['ssc_file'])
            data['_source_type'] = 'ssc'
            data['_source_file'] = level_info['ssc_file']
            all_chart_data.append(data)
        except:
            pass
    
    if level_info.get('sm_file'):
        try:
            data = parse_sm_or_ssc_file(level_info['sm_file'])
            data['_source_type'] = 'sm'
            data['_source_file'] = level_info['sm_file']
            all_chart_data.append(data)
        except:
            pass
    
    if level_info.get('dwi_file'):
        try:
            data = parse_dwi_file(level_info['dwi_file'])
            data['_source_type'] = 'dwi'
            data['_source_file'] = level_info['dwi_file']
            all_chart_data.append(data)
        except:
            pass
    
    if not all_chart_data:
        print(f"No valid chart file found for {level_info['name']}")
        return []
    
    # Use primary chart data (first in list = highest priority)
    chart_data = all_chart_data[0]
    file_type = chart_data['_source_type']
    chart_file = chart_data['_source_file']
    
    # Fill in missing metadata from other sources
    for data in all_chart_data[1:]:
        # Fill in title if missing
        if (not chart_data.get('title') or chart_data['title'] == 'Unknown') and data.get('title') and data['title'] != 'Unknown':
            chart_data['title'] = data['title']
        # Fill in artist if missing
        if (not chart_data.get('artist') or chart_data['artist'] == 'Unknown') and data.get('artist') and data['artist'] != 'Unknown':
            chart_data['artist'] = data['artist']
        # Fill in subtitle if missing
        if not chart_data.get('subtitle') and data.get('subtitle'):
            chart_data['subtitle'] = data['subtitle']
    
    # Merge charts from all sources, filling in missing difficulty info
    # Create a map of charts by difficulty from all sources
    difficulty_sources = {}
    for data in all_chart_data:
        for i, chart in enumerate(data['charts']):
            if chart['difficulty'] and chart['difficulty'] != 'Unknown':
                key = (data['_source_type'], i)
                difficulty_sources[key] = chart['difficulty']
    
    # Fill in missing difficulties in primary chart data
    for i, chart in enumerate(chart_data['charts']):
        if chart['difficulty'] == 'Unknown' or not chart['difficulty']:
            # Try to find from DWI first
            dwi_key = ('dwi', i)
            if dwi_key in difficulty_sources:
                chart['difficulty'] = difficulty_sources[dwi_key]
            else:
                # Try from SM
                sm_key = ('sm', i)
                if sm_key in difficulty_sources:
                    chart['difficulty'] = difficulty_sources[sm_key]
                else:
                    # Try from SSC
                    ssc_key = ('ssc', i)
                    if ssc_key in difficulty_sources:
                        chart['difficulty'] = difficulty_sources[ssc_key]
                    else:
                        # Last resort: generic name
                        chart['difficulty'] = f"Chart_{i+1}"

    # Compute audio length once per level folder (same audio for all difficulties)
    audio_length = get_audio_length_seconds(level_info.get('audio'))
    if audio_length is not None:
        audio_length = round(float(audio_length), 3)
    
    # Convert each difficulty to a separate JSON
    created_files = []
    
    for chart in chart_data['charts']:
        # Generate filename
        safe_name = re.sub(r'[^\w\s-]', '', level_info['name']).strip().replace(' ', '_')
        safe_diff = re.sub(r'[^\w\s-]', '', chart['difficulty']).strip().replace(' ', '_')
        json_filename = f"{safe_name}_{safe_diff}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Convert notes
        notes = convert_chart_to_json(chart_data, chart)
        
        # Calculate BPM range
        bpm_values = [bpm for _, bpm in chart_data['bpm_data']]
        min_bpm = min(bpm_values) if bpm_values else 120
        max_bpm = max(bpm_values) if bpm_values else 120
        
        # Create level JSON
        level_json = {
            "meta": {
                "source": os.path.basename(chart_file),
                "total_notes": len(notes),
                "pattern": f"converted_from_{file_type}",
                "color_mode": "random",
                "seed": 42,
                "title": chart_data['title'],
                "subtitle": chart_data['subtitle'],
                "artist": chart_data['artist'],
                "creator": f"{file_type.upper()} Converter",
                "version": chart['difficulty'],
                "audio_file": level_info['audio'],
                "length": audio_length,  # NEW: audio duration in seconds (float) or None
                "background_file": level_info['background'],  # bg.* for in-game
                "thumbnail_file": level_info.get('thumbnail'),  # bn.* for level boxes
                "bpm_min": min_bpm,
                "bpm_max": max_bpm
            },
            "level": notes
        }
        
        # Write JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(level_json, f, indent=2)
        
        created_files.append(json_path)
        print(f"Created: {json_filename} ({len(notes)} notes)")
    
    return created_files

def scan_and_load_songpacks(songpacks_dir='songpacks', extract_to=None, custom_dir=None):
    """
    Scan multiple directories for songpack ZIP files.
    
    Args:
        songpacks_dir: Directory containing built-in .zip songpack files
        extract_to: Directory to extract songpacks to (must be specified explicitly)
        custom_dir: Optional custom directory selected by user via "Set Folder" button
    
    Returns: List of pack info dicts
    """
    # Debug logging
    def log_debug(msg):
        try:
            log_path = os.path.join('.toa', 'songpack_debug.log') if os.path.exists('.toa') else 'songpack_debug.log'
            with open(log_path, 'a', encoding='utf-8') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] {msg}\n")
        except:
            pass
    
    log_debug(f"scan_and_load_songpacks called: songpacks_dir={songpacks_dir}, extract_to={extract_to}, custom_dir={custom_dir}")
    
    packs = []
    
    if extract_to is None:
        # Default: if songpacks_dir contains '.toa', put extracted in .toa/songpacks/extracted
        # Otherwise put in songpacks/extracted
        if '.toa' in str(songpacks_dir):
            # Extract .toa prefix
            if str(songpacks_dir).startswith('.toa'):
                extract_to = os.path.join('.toa', 'songpacks', 'extracted')
            else:
                # Handle case where full path contains .toa
                extract_to = 'songpacks/extracted'
        else:
            extract_to = 'songpacks/extracted'
    
    log_debug(f"extract_to determined: {extract_to}")
    
    # Scan directories to check
    dirs_to_scan = []
    if os.path.exists(songpacks_dir):
        dirs_to_scan.append(songpacks_dir)
        log_debug(f"Added songpacks_dir to scan: {songpacks_dir}")
    else:
        log_debug(f"songpacks_dir does not exist: {songpacks_dir}")
    if custom_dir and os.path.exists(custom_dir):
        dirs_to_scan.append(custom_dir)
        log_debug(f"Added custom_dir to scan: {custom_dir}")
    elif custom_dir:
        log_debug(f"custom_dir specified but does not exist: {custom_dir}")
    
    log_debug(f"Total dirs to scan: {len(dirs_to_scan)}")
    
    for scan_dir in dirs_to_scan:
        log_debug(f"Scanning directory: {scan_dir}")
        try:
            files = os.listdir(scan_dir)
            log_debug(f"  Found {len(files)} files")
            for file in files:
                log_debug(f"  Checking file: {file}")
                if file.lower().endswith('.zip'):
                    zip_path = os.path.join(scan_dir, file)
                    log_debug(f"    Processing ZIP: {zip_path}")
                    try:
                        pack_info = extract_songpack(zip_path, extract_to=extract_to)
                        packs.append(pack_info)
                        print(f"Loaded pack: {pack_info['pack_name']} ({len(pack_info['levels'])} levels)")
                        log_debug(f"    SUCCESS: Loaded {pack_info['pack_name']}")
                    except Exception as e:
                        print(f"Error loading {file}: {e}")
                        log_debug(f"    ERROR loading {file}: {e}")
                        import traceback
                        log_debug(traceback.format_exc())
        except Exception as e:
            log_debug(f"  ERROR scanning {scan_dir}: {e}")
    
    log_debug(f"Total packs loaded: {len(packs)}")
    return packs

if __name__ == "__main__":
    # Test the loader
    packs = scan_and_load_songpacks()
    
    if packs:
        print(f"\nFound {len(packs)} song pack(s)")
        for pack in packs:
            print(f"\nPack: {pack['pack_name']}")
            print(f"  Cover: {pack['pack_image']}")
            print(f"  Levels: {len(pack['levels'])}")
            
            # Convert first level as test
            if pack['levels']:
                level = pack['levels'][0]
                print(f"\n  Converting: {level['name']}")
                convert_level_to_json(level)
    else:
        print("No song packs found in songpacks/ directory")
        print("Place .zip files containing SM/SSC charts in the songpacks/ folder")
