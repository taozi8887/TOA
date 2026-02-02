"""
Auto-updater module for TOA game
Downloads updates from GitHub repository
"""

import os
import json
import hashlib
import requests
import time
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
        # Store local version.json in hidden folder, but fetch from root on GitHub
        self.local_version_file = os.path.join('.toa', 'version.json')
        self.remote_version_file = 'version.json'
        
    def is_first_run(self) -> bool:
        """
        Check if this is the first run (no local files exist)
        
        Returns:
            True if this is first run, False otherwise
        """
        # Check if essential files/folders exist in hidden folder
        # Note: beatmaps and levels are generated from .osz, not downloaded
        hidden_folder = '.toa'
        if not os.path.exists(hidden_folder):
            return True
        required_paths = ['assets', 'main.py']
        for path in required_paths:
            full_path = os.path.join(hidden_folder, path)
            if not os.path.exists(full_path):
                return True
        return False
    
    def get_all_remote_files(self) -> List[str]:
        """
        Get list of all files from remote version.json
        Prioritizes Python code files, then assets, then levels/beatmaps
        
        Returns:
            List of all file paths that need to be downloaded (prioritized order)
        """
        try:
            remote_version = self._get_remote_version()
            if not remote_version:
                return []
            
            code_files = []
            asset_files = []
            content_files = []
            files_dict = remote_version.get('files', {})
            
            # Separate files by priority: code > assets > content (levels/beatmaps)
            for directory, files in files_dict.items():
                if directory == 'code':
                    # Code files are at root level - highest priority
                    code_files.extend(files.keys())
                elif directory == 'assets':
                    # Assets are second priority
                    for file_name in files.keys():
                        asset_files.append(os.path.join(directory, file_name))
                else:
                    # Content files (levels, beatmaps) are last
                    for file_name in files.keys():
                        content_files.append(os.path.join(directory, file_name))
            
            # Return in priority order: code first, then assets, then content
            return code_files + asset_files + content_files
        
        except Exception as e:
            print(f"Error getting remote files: {e}")
            return []
    
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
    
    def download_updates(self, files_to_download: List[str], progress_callback=None, is_initial_download: bool = False) -> bool:
        """
        Download updated files from GitHub
        
        Args:
            files_to_download: List of file paths to download
            progress_callback: Optional callback function(current, total, filename)
            is_initial_download: If True, this is the first-time download of all files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use hidden folder for game data
            data_folder = '.toa'
            os.makedirs(data_folder, exist_ok=True)
            
            # Set folder as hidden on Windows
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(data_folder, 0x02)  # FILE_ATTRIBUTE_HIDDEN
            except:
                pass
            
            total_files = len(files_to_download)
            failed_files = []
            
            for idx, file_path in enumerate(files_to_download):
                if progress_callback:
                    progress_callback(idx + 1, total_files, file_path)
                
                # Download file - convert Windows paths to URL paths
                url_path = file_path.replace('\\', '/')
                url = f"{self.raw_url}/{url_path}"
                
                # Retry logic: try up to 3 times
                max_retries = 3
                success = False
                
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, timeout=30)
                        
                        if response.status_code == 200:
                            # Download to hidden folder
                            hidden_path = os.path.join(data_folder, file_path)
                            local_path = Path(hidden_path)
                            local_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Write file
                            with open(hidden_path, 'wb') as f:
                                f.write(response.content)
                            
                            print(f"Downloaded: {file_path}")
                            success = True
                            break
                        else:
                            print(f"Attempt {attempt+1}: Failed to download {file_path}: HTTP {response.status_code}")
                    
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        print(f"Attempt {attempt+1}: Connection error for {file_path}: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)  # Wait 2 seconds before retry
                    
                    except Exception as e:
                        print(f"Attempt {attempt+1}: Error downloading {file_path}: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                
                if not success:
                    failed_files.append(file_path)
                    # Continue downloading other files instead of failing completely
                
                # Small delay between downloads to avoid overwhelming connection
                if idx < total_files - 1:  # Don't delay after last file
                    time.sleep(0.1)
            
            # Update local version info after successful download
            self._update_local_version()
            
            # If this was initial download, also download config files to hidden folder
            if is_initial_download:
                config_files = ['update_config.json', 'toa_settings.json']
                for config_file in config_files:
                    try:
                        url = f"{self.raw_url}/{config_file}"
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            config_path = os.path.join(data_folder, config_file)
                            with open(config_path, 'wb') as f:
                                f.write(response.content)
                            print(f"Downloaded config: {config_file}")
                    except:
                        pass  # Config files are optional
            
            # Report any failed files
            if failed_files:
                print(f"\nWarning: {len(failed_files)} files failed to download:")
                for f in failed_files[:10]:  # Show first 10
                    print(f"  - {f}")
                if len(failed_files) > 10:
                    print(f"  ... and {len(failed_files) - 10} more")
                # Return True if at least code files downloaded
                return len(failed_files) < total_files * 0.5  # Succeed if >50% downloaded
            
            return True
        
        except Exception as e:
            print(f"Error downloading updates: {e}")
            return False
    
    def _get_remote_version(self) -> Optional[Dict]:
        """Get version info from remote repository"""
        try:
            url = f"{self.raw_url}/{self.remote_version_file}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return json.loads(response.content)
            return None
        
        except Exception as e:
            print(f"Error fetching remote version: {e}")
            print(f"URL attempted: {url}")
            return None
    
    def _get_local_version(self) -> Dict:
        """Get local version info"""
        try:
            if os.path.exists(self.local_version_file):
                with open(self.local_version_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading local version: {e}")
        
        return {"version": "0.0.0", "files": {}}
    
    def _update_local_version(self):
        """Update local version file after successful download"""
        try:
            remote_version = self._get_remote_version()
            if remote_version:
                # Ensure .toa directory exists
                os.makedirs(os.path.dirname(self.local_version_file), exist_ok=True)
                with open(self.local_version_file, 'w') as f:
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
    
    # Auto-detect version from main.py
    game_version = "0.4.0"  # Default fallback
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('__version__'):
                    # Extract version string from __version__ = "x.x.x"
                    parts = line.split('=')[1].strip()
                    # Remove quotes and comments
                    for quote in ['"', "'"]:
                        if quote in parts:
                            game_version = parts.split(quote)[1]
                            break
                    break
    except Exception as e:
        print(f"Warning: Could not auto-detect version from main.py: {e}")
    
    version_data = {
        "version": game_version,
        "files": {}
    }
    
    # Track data directories (levels, beatmaps)
    for directory in directories:
        if os.path.exists(directory):
            version_data['files'][directory] = {}
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.json', '.osu', '.mp3', '.wav', '.ogg', '.jpg', '.png', '.osz')):
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
