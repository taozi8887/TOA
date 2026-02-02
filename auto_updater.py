"""
Auto-updater module for TOA game
Downloads updates from GitHub repository
"""

import os
import json
import hashlib
import requests
from typing import Optional, Tuple, List, Dict
from pathlib import Path

class AutoUpdater:
    """Handles auto-updates from GitHub repository"""
    
    def __init__(self, repo_owner: str, repo_name: str, branch: str = "main"):
        """
        Initialize auto-updater
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            branch: Git branch to pull from (default: main)
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.raw_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        self.version_file = "version.json"
        
    def check_for_updates(self, directories: List[str] = None, include_code: bool = True) -> Tuple[bool, List[str]]:
        """
        Check if updates are available
        
        Args:
            directories: List of directories to check (e.g., ['levels', 'beatmaps'])
            include_code: If True, also check for Python code updates
            
        Returns:
            Tuple of (has_updates, list_of_changed_files)
        """
        if directories is None:
            directories = ['levels', 'beatmaps']
        
        try:
            # Get remote version info
            remote_version = self._get_remote_version()
            if remote_version is None:
                return False, []
            
            # Get local version info
            local_version = self._get_local_version()
            
            # Compare and find differences
            changed_files = []
            
            # Check data directories (levels, beatmaps)
            for directory in directories:
                if directory in remote_version.get('files', {}):
                    remote_files = remote_version['files'][directory]
                    local_files = local_version.get('files', {}).get(directory, {})
                    
                    for file_path, remote_hash in remote_files.items():
                        local_hash = local_files.get(file_path, "")
                        if remote_hash != local_hash:
                            changed_files.append(os.path.join(directory, file_path))
            
            # Check Python code files if include_code is True
            if include_code and 'code' in remote_version.get('files', {}):
                remote_code = remote_version['files']['code']
                local_code = local_version.get('files', {}).get('code', {})
                
                for file_path, remote_hash in remote_code.items():
                    local_hash = local_code.get(file_path, "")
                    if remote_hash != local_hash:
                        changed_files.append(file_path)
            
            return len(changed_files) > 0, changed_files
        
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False, []
    
    def download_updates(self, files_to_download: List[str], progress_callback=None) -> bool:
        """
        Download updated files from GitHub
        
        Args:
            files_to_download: List of file paths to download
            progress_callback: Optional callback function(current, total, filename)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            total_files = len(files_to_download)
            for idx, file_path in enumerate(files_to_download):
                if progress_callback:
                    progress_callback(idx + 1, total_files, file_path)
                
                # Download file
                url = f"{self.raw_url}/{file_path}"
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Create directory if needed
                    local_path = Path(file_path)
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"Downloaded: {file_path}")
                else:
                    print(f"Failed to download {file_path}: HTTP {response.status_code}")
                    return False
            
            # Update local version info after successful download
            self._update_local_version()
            return True
        
        except Exception as e:
            print(f"Error downloading updates: {e}")
            return False
    
    def _get_remote_version(self) -> Optional[Dict]:
        """Get version info from remote repository"""
        try:
            url = f"{self.raw_url}/{self.version_file}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return json.loads(response.content)
            return None
        
        except Exception as e:
            print(f"Error fetching remote version: {e}")
            return None
    
    def _get_local_version(self) -> Dict:
        """Get local version info"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading local version: {e}")
        
        return {"version": "0.0.0", "files": {}}
    
    def _update_local_version(self):
        """Update local version file after successful download"""
        try:
            remote_version = self._get_remote_version()
            if remote_version:
                with open(self.version_file, 'w') as f:
                    json.dump(remote_version, f, indent=2)
        except Exception as e:
            print(f"Error updating local version: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except:
            return ""


def create_version_file(directories: List[str] = None, include_code: bool = True, output_file: str = "version.json"):
    """
    Utility function to create a version.json file for the repository.
    This should be run whenever you want to publish new updates.
    
    Args:
        directories: List of directories to include in version tracking
        include_code: If True, also track Python code files
        output_file: Output filename for version info
    """
    if directories is None:
        directories = ['levels', 'beatmaps']
    
    version_data = {
        "version": "0.4.0",  # Should match __version__ in main.py
        "files": {}
    }
    
    # Track data directories (levels, beatmaps)
    for directory in directories:
        if os.path.exists(directory):
            version_data['files'][directory] = {}
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.json', '.osu', '.mp3', '.wav', '.ogg', '.jpg', '.png')):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, directory)
                        
                        # Calculate file hash
                        try:
                            sha256_hash = hashlib.sha256()
                            with open(file_path, "rb") as f:
                                for byte_block in iter(lambda: f.read(4096), b""):
                                    sha256_hash.update(byte_block)
                            file_hash = sha256_hash.hexdigest()
                            version_data['files'][directory][relative_path] = file_hash
                        except Exception as e:
                            print(f"Error hashing {file_path}: {e}")
    
    # Track Python code files
    if include_code:
        version_data['files']['code'] = {}
        code_files = ['main.py', 'osu_to_level.py', 'unzip.py', 'auto_updater.py', 'batch_process_osz.py']
        
        for code_file in code_files:
            if os.path.exists(code_file):
                try:
                    sha256_hash = hashlib.sha256()
                    with open(code_file, "rb") as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                    file_hash = sha256_hash.hexdigest()
                    version_data['files']['code'][code_file] = file_hash
                except Exception as e:
                    print(f"Error hashing {code_file}: {e}")
    
    with open(output_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    print(f"Created {output_file} with {sum(len(files) for files in version_data['files'].values())} files tracked")


if __name__ == "__main__":
    # Example: Create version file for current repository state
    print("Creating version.json for current repository state...")
    create_version_file()
