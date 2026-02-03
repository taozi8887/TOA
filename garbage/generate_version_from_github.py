"""
Generate version.json file by downloading files from GitHub to ensure hash compatibility.
This fixes the hash mismatch issue where local files have different line endings than GitHub-served files.
Only updates files that have been committed in the most recent commit.
"""

import os
import json
import hashlib
import requests
import time
import subprocess

def get_changed_files():
    """Get list of files changed in the most recent commit"""
    try:
        result = subprocess.run(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            return [f for f in files if f]
        return []
    except Exception as e:
        print(f"Error getting changed files: {e}")
        return []

def create_version_file_from_github(output_file: str = "version.json"):
    """
    Update version.json by downloading only changed files from GitHub.
    """
    raw_url = "https://raw.githubusercontent.com/taozi8887/TOA/main"
    
    # Load existing version.json
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            version_data = json.load(f)
        print("Loaded existing version.json")
    else:
        version_data = {
            "version": "0.5.0",
            "files": {
                "assets": {},
                "code": {}
            }
        }
        print("Creating new version.json")
    
    # Get files that changed in last commit
    changed_files = get_changed_files()
    if not changed_files:
        print("No files changed in last commit")
        return
    
    print(f"\nUpdating hashes for {len(changed_files)} changed file(s)...")
    
    for file_path in changed_files:
        # Normalize path separators
        file_path = file_path.replace('\\', '/')
        
        # Determine category
        if file_path.startswith('assets/'):
            category = 'assets'
            relative_path = file_path[7:]  # Remove 'assets/' prefix
        elif file_path.endswith('.py'):
            category = 'code'
            relative_path = file_path
        else:
            continue  # Skip files we don't track
        
        # Ensure category exists
        if category not in version_data['files']:
            version_data['files'][category] = {}
        
        try:
            github_url = f"{raw_url}/{file_path}"
            print(f"  Fetching: {file_path}")
            response = requests.get(github_url, timeout=30)
            if response.status_code == 200:
                sha256_hash = hashlib.sha256()
                sha256_hash.update(response.content)
                file_hash = sha256_hash.hexdigest()
                version_data['files'][category][relative_path] = file_hash
                print(f"    ✓ Updated hash")
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