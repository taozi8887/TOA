from songpack_loader import parse_sm_or_ssc_file
import re

sm_file = 'songpacks/extracted/10Dollar Dump Dump Revolutions 4/10Dollar Dump Dump Revolutions 4/1 (10Dollar)/1.sm'

with open(sm_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Split by #NOTES:
sections = content.split('#NOTES:')
print(f"Found {len(sections)} sections")

if len(sections) > 1:
    chart_content = sections[1]
    lines = chart_content.split('\n')
    
    print(f"\nFirst 50 lines of chart:")
    for i, line in enumerate(lines[:50]):
        print(f"{i}: '{line.strip()}'")
    
    # Count commas
    comma_count = sum(1 for line in lines if line.strip() == ',')
    print(f"\nTotal commas found: {comma_count}")
    
    # Count note lines
    note_lines = sum(1 for line in lines if re.match(r'^[0-9MKLF]{4}$', line.strip()))
    print(f"Total note lines: {note_lines}")
