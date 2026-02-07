from songpack_loader import parse_sm_or_ssc_file, convert_level_to_json

# Test parsing
sm_file = 'songpacks/extracted/10Dollar Dump Dump Revolutions 4/10Dollar Dump Dump Revolutions 4/1 (10Dollar)/1.sm'

print("Parsing SM file...")
data = parse_sm_or_ssc_file(sm_file)

print(f"Title: {data['title']}")
print(f"Artist: {data['artist']}")
print(f"Offset: {data['offset']}")
print(f"BPMs: {data['bpm_data']}")
print(f"Charts found: {len(data['charts'])}")

if data['charts']:
    chart = data['charts'][0]
    print(f"\nFirst chart:")
    print(f"  Type: {chart['type']}")
    print(f"  Difficulty: {chart['difficulty']}")
    print(f"  Measures: {len(chart['measures'])}")
    
    if chart['measures']:
        print(f"  First measure has {len(chart['measures'][0])} notes")
        print(f"  First few notes: {chart['measures'][0][:5]}")

print("\nTesting conversion...")
level_info = {
    'folder': 'songpacks/extracted/10Dollar Dump Dump Revolutions 4/10Dollar Dump Dump Revolutions 4/1 (10Dollar)',
    'name': '1 (10Dollar)',
    'audio': 'songpacks/extracted/10Dollar Dump Dump Revolutions 4/10Dollar Dump Dump Revolutions 4/1 (10Dollar)/1.mp3',
    'sm_file': sm_file,
    'ssc_file': None,
    'background': 'songpacks/extracted/10Dollar Dump Dump Revolutions 4/10Dollar Dump Dump Revolutions 4/1 (10Dollar)/BG.png'
}

json_files = convert_level_to_json(level_info, output_dir='levels')
print(f"Created {len(json_files)} JSON file(s)")
