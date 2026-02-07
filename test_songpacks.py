"""
Test script for song pack system
Place your .zip song pack files in the songpacks/ folder and run this
"""

from songpack_loader import scan_and_load_songpacks, convert_level_to_json
import os

def main():
    print("=" * 60)
    print("TOA Song Pack Test")
    print("=" * 60)
    
    # Check if songpacks directory exists
    if not os.path.exists('songpacks'):
        os.makedirs('songpacks')
        print("\nCreated songpacks/ directory")
        print("Place your .zip song pack files here and run again!")
        return
    
    # Scan for packs
    print("\nScanning for song packs...")
    packs = scan_and_load_songpacks()
    
    if not packs:
        print("\nNo song packs found in songpacks/ directory")
        print("Add .zip files containing SM/SSC charts to get started!")
        return
    
    print(f"\nFound {len(packs)} song pack(s):\n")
    
    for idx, pack in enumerate(packs, 1):
        print(f"{idx}. {pack['pack_name']}")
        print(f"   Cover: {os.path.basename(pack['pack_image']) if pack['pack_image'] else 'None'}")
        print(f"   Levels: {len(pack['levels'])}")
        
        # Show first few levels
        for i, level in enumerate(pack['levels'][:3]):
            print(f"      - {level['name']}")
            print(f"        Audio: {os.path.basename(level['audio']) if level['audio'] else 'None'}")
            print(f"        Charts: {os.path.basename(level['sm_file']) if level['sm_file'] else 'None'} / {os.path.basename(level['ssc_file']) if level['ssc_file'] else 'None'}")
        
        if len(pack['levels']) > 3:
            print(f"      ... and {len(pack['levels']) - 3} more")
        print()
    
    # Ask if user wants to convert a pack
    print("\nWould you like to convert a pack to JSON? (y/n)")
    response = input().lower()
    
    if response == 'y' and packs:
        print(f"\nConverting pack: {packs[0]['pack_name']}")
        
        for level in packs[0]['levels']:
            print(f"\n  Converting: {level['name']}")
            try:
                created_files = convert_level_to_json(level)
                for file in created_files:
                    print(f"    ✓ Created: {os.path.basename(file)}")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        print("\n✓ Conversion complete! Check the levels/ folder.")

if __name__ == "__main__":
    main()
