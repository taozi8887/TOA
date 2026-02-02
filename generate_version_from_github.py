"""
Generate version.json file by downloading files from GitHub to ensure hash compatibility.
This fixes the hash mismatch issue where local files have different line endings than GitHub-served files.
"""

import os
import json
import hashlib
import requests
import time

def create_version_file_from_github(output_file: str = "version.json"):
    """
    Create version.json by downloading files from GitHub to match download hashes.
    """
    raw_url = "https://raw.githubusercontent.com/taozi8887/TOA/main"
    
    version_data = {
        "version": "0.4.1",
        "files": {}
    }
    
    print("Generating version.json from GitHub raw files...")
    
    # Track assets directory
    directories = ['assets']
    for directory in directories:
        if os.path.exists(directory):
            version_data['files'][directory] = {}
            print(f"Processing directory: {directory}")
            
            # Walk through directory and get files from GitHub
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.json', '.osu', '.mp3', '.wav', '.ogg', '.jpg', '.png', '.osz')):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, directory)
                        relative_path = relative_path.replace('\\', '/')
                        
                        try:
                            github_url = f"{raw_url}/{directory}/{relative_path}"
                            print(f"  Fetching: {relative_path}")
                            response = requests.get(github_url, timeout=30)
                            if response.status_code == 200:
                                sha256_hash = hashlib.sha256()
                                sha256_hash.update(response.content)
                                file_hash = sha256_hash.hexdigest()
                                version_data['files'][directory][relative_path] = file_hash
                            else:
                                print(f"    Failed: HTTP {response.status_code}")
                        except Exception as e:
                            print(f"    Error: {e}")
                        
                        time.sleep(0.1)  # Be nice to GitHub
    
    # Track Python code files
    print("Processing code files...")
    version_data['files']['code'] = {}
    code_files = ['main.py', 'osu_to_level.py', 'unzip.py', 'auto_updater.py', 'batch_process_osz.py']
    
    for code_file in code_files:
        if os.path.exists(code_file):
            try:
                github_url = f"{raw_url}/{code_file}"
                print(f"  Fetching: {code_file}")
                response = requests.get(github_url, timeout=30)
                if response.status_code == 200:
                    sha256_hash = hashlib.sha256()
                    sha256_hash.update(response.content)
                    file_hash = sha256_hash.hexdigest()
                    version_data['files']['code'][code_file] = file_hash
                else:
                    print(f"    Failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"    Error: {e}")
            
            time.sleep(0.1)
    
    with open(output_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    total_files = sum(len(files) for files in version_data['files'].values())
    print(f"\nCreated {output_file} with {total_files} files tracked")
    print("All hashes calculated from GitHub raw URLs to match download behavior")

if __name__ == "__main__":
    create_version_file_from_github()