import zipfile
import os

def read_osz_file(osz_path, extract_dir="temp_beatmap"):
    """
    Extracts the contents of an .osz file to a specified directory.
    Returns the list of extracted .osu files.
    """
    # Ensure the destination directory exists
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    # Open the .osz file as a zip file
    osu_files = []

    try:
        with zipfile.ZipFile(osz_path, 'r') as zf:
            print(f"Extracting contents of {osz_path} to {extract_dir}...")
            # Only extract files not in any 'sb' folder
            for member in zf.namelist():
                # Skip any file or folder inside a directory named 'sb'
                parts = member.split('/')
                if 'sb' in parts:
                    continue
                zf.extract(member, extract_dir)
                if member.endswith('.osu'):
                    osu_files.append(os.path.join(extract_dir, member))
                print(f"- {member}")

    except zipfile.BadZipFile:
        print(f"Error: {osz_path} is not a valid zip file.")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return osu_files

if __name__ == "__main__":
    # Example usage:
    # Replace "path/to/your/beatmap.osz" with the actual path to your file
    read_osz_file("assets/pingpong.osz", extract_dir="beatmaps/pingpong")