"""
Auto-updater module for TOA game
Downloads updates from GitHub repository
"""

import os
import json
import hashlib
import requests
import time
import shutil
import tempfile
import stat
from typing import Optional, Tuple, List, Dict, Callable
from pathlib import Path
from datetime import datetime

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
        # Manifest-based system
        self.local_manifest_file = os.path.join('.toa', 'manifest.json')
        self.remote_manifest_file = 'manifest.json'
        # Legacy support
        self.local_version_file = os.path.join('.toa', 'version.json')
        self.remote_version_file = 'version.json'
        # Backup folder for rollback
        self.backup_folder = os.path.join('.toa', 'backup')
        # Chunk size for downloads (1MB)
        self.chunk_size = 1024 * 1024
        self._lock_file = None
        # Debug log file
        self.log_file = os.path.join('.toa', 'update_debug.log') if os.path.exists('.toa') else 'update_debug.log'
    
    def _log(self, msg: str):
        """Write debug message to log file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except:
            pass
        
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
    
    def check_for_updates(self, directories: List[str] = None, include_code: bool = True) -> Tuple[bool, List[str], Dict]:
        """
        Check if updates are available using manifest-based system
        
        Args:
            directories: List of directories to check (e.g., ['levels', 'beatmaps'])
            include_code: If True, also check for Python code updates
            
        Returns:
            Tuple of (has_updates, list_of_changed_files, update_info)
        """
        if directories is None:
            directories = ['levels', 'beatmaps']
        
        try:
            # Get local and remote manifests
            local_manifest = self._get_local_manifest()
            remote_manifest = self._get_remote_manifest()
            
            if not remote_manifest:
                # Fallback to legacy version.json system
                has_updates, changed = self._legacy_check_updates(directories, include_code)
                return has_updates, changed, {}
            
            local_version = local_manifest.get('version', '0.0.0')
            remote_version = remote_manifest.get('version', '0.0.0')
            
            # Compare versions - if same version, no updates needed
            if local_version == remote_version:
                return False, [], {}
            
            # If remote is older, no updates
            if self._version_compare(remote_version, local_version) < 0:
                return False, [], {}
            
            # Find changed/new files
            changed_files = []
            remote_files = remote_manifest.get('files', {})
            local_files = local_manifest.get('files', {})
            
            # Check assets
            if 'assets' in remote_files:
                for file_path, file_info in remote_files['assets'].items():
                    local_info = local_files.get('assets', {}).get(file_path, {})
                    remote_hash = file_info if isinstance(file_info, str) else file_info.get('hash', '')
                    local_hash = local_info if isinstance(local_info, str) else local_info.get('hash', '')
                    if remote_hash != local_hash:
                        changed_files.append(f"assets/{file_path}")
            
            # Check code files
            if include_code and 'code' in remote_files:
                for file_path, file_info in remote_files['code'].items():
                    local_info = local_files.get('code', {}).get(file_path, {})
                    remote_hash = file_info if isinstance(file_info, str) else file_info.get('hash', '')
                    local_hash = local_info if isinstance(local_info, str) else local_info.get('hash', '')
                    if remote_hash != local_hash:
                        changed_files.append(file_path)
            
            # Get patch info if available
            update_info = {
                'from_version': local_version,
                'to_version': remote_version,
                'can_patch': False,
                'patch_info': None,
                'release_date': remote_manifest.get('release_date', ''),
                'total_size': 0
            }
            
            # Check if delta patch is available
            patches = remote_manifest.get('patches', {})
            patch_key = f"from_{local_version}"
            if patch_key in patches:
                update_info['can_patch'] = True
                update_info['patch_info'] = patches[patch_key]
            
            return len(changed_files) > 0, changed_files, update_info
        
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False, [], {}
    
    def download_updates(self, files_to_download: List[str], progress_callback: Callable[[int, int, str, int, int], None] = None, is_initial_download: bool = False, create_backup: bool = True) -> bool:
        """
        Download updated files from GitHub with chunked download and hash verification
        
        Args:
            files_to_download: List of file paths to download
            progress_callback: Optional callback(current_file, total_files, filename, downloaded_bytes, total_bytes)
            is_initial_download: If True, this is the first-time download
            create_backup: If True, backup existing files before updating
            
        Returns:
            True if successful, False otherwise
        """
        # Debug logging
        log_file = os.path.join('.toa', 'update_debug.log') if os.path.exists('.toa') else 'update_debug.log'
        def log(msg):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        
        log(f"=== Download started: {len(files_to_download)} files ===")
        
        try:
            data_folder = '.toa'
            os.makedirs(data_folder, exist_ok=True)
            
            # Set folder as hidden + system on Windows
            if os.name == 'nt':
                import subprocess
                import ctypes
                subprocess.run(['attrib', '+H', '+S', data_folder], shell=True, capture_output=True)
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(data_folder, 0x02 | 0x04)
                except:
                    pass
            
            # Create backup if requested and not initial download
            if create_backup and not is_initial_download:
                self._create_backup(files_to_download)
            
            total_files = len(files_to_download)
            failed_files = []
            remote_manifest = self._get_remote_manifest()
            log(f"Remote manifest fetched, version: {remote_manifest.get('version', 'unknown') if remote_manifest else 'FAILED'}")
            
            for idx, file_path in enumerate(files_to_download):
                log(f"Downloading {idx+1}/{total_files}: {file_path}")
                # Get expected hash from manifest
                expected_hash = self._get_file_hash_from_manifest(remote_manifest, file_path)
                log(f"  Expected hash: {expected_hash[:16]}...")
                
                # Download with chunked streaming and hash verification
                success = self._download_file_chunked(
                    file_path, 
                    data_folder, 
                    expected_hash,
                    lambda downloaded, total: progress_callback(idx + 1, total_files, file_path, downloaded, total) if progress_callback else None
                )
                
                if not success:
                    log(f"  FAILED to download: {file_path}")
                    print(f"FAILED to download: {file_path}")
                    failed_files.append(file_path)
                else:
                    log(f"  ✓ Successfully downloaded: {file_path}")
                    print(f"✓ Downloaded: {file_path}")
                
                time.sleep(0.1)
            
            # Only update manifest if ALL files downloaded successfully
            if len(failed_files) == 0:
                log("All files downloaded successfully, updating manifest...")
                self._update_local_manifest(remote_manifest)
                print("✓ Updated local manifest")
                log("✓ Manifest updated")
                
                # Download config files if initial install
                if is_initial_download:
                    log("Initial download, fetching config files...")
                    for config_file in ['update_config.json', 'toa_settings.json']:
                        try:
                            url = f"{self.raw_url}/{config_file}"
                            response = requests.get(url, timeout=10)
                            if response.status_code == 200:
                                with open(os.path.join(data_folder, config_file), 'wb') as f:
                                    f.write(response.content)
                                log(f"  ✓ Downloaded {config_file}")
                        except Exception as e:
                            log(f"  Failed to download {config_file}: {e}")
            else:
                log(f"Download incomplete: {len(failed_files)} files failed")
            
            if failed_files:
                log(f"WARNING: {len(failed_files)} files failed: {failed_files}")
                print(f"\nWarning: {len(failed_files)} files failed to download")
                return len(failed_files) < total_files * 0.5
            
            log("=== Download completed successfully ===")
            return True
        
        except Exception as e:
            log(f"ERROR in download_updates: {e}")
            print(f"Error downloading updates: {e}")
            # Rollback if backup exists
            if create_backup and not is_initial_download:
                log("Attempting rollback...")
                self._rollback_from_backup()
            return False
    
    def _get_remote_version(self) -> Optional[Dict]:
        """Get version info from remote repository with cache-busting"""
        try:
            # Add timestamp to URL to bypass CDN cache completely
            import time
            url = f"{self.raw_url}/{self.remote_version_file}?t={int(time.time())}"
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
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
    
    def _update_local_version(self, successfully_downloaded_files=None):
        """Update local version file - simplified to just use GitHub version"""
        try:
            # Local version.json is already updated in check_for_updates
            print("Local version.json updated from GitHub")
                
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
    
    def _get_local_manifest(self) -> Dict:
        """Get local manifest file"""
        try:
            if os.path.exists(self.local_manifest_file):
                with open(self.local_manifest_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        # Fallback to version.json
        return self._get_local_version()
    
    def _get_remote_manifest(self) -> Optional[Dict]:
        """Get remote manifest from GitHub with cache-busting"""
        try:
            # Add timestamp to URL to bypass CDN cache completely
            import time
            url = f"{self.raw_url}/{self.remote_manifest_file}?t={int(time.time())}"
            # Add cache-busting headers to get fresh data from GitHub
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return json.loads(response.content)
        except:
            pass
        # Fallback to version.json
        return self._get_remote_version()
    
    def _update_local_manifest(self, manifest: Dict):
        """Update local manifest file"""
        try:
            os.makedirs('.toa', exist_ok=True)
            with open(self.local_manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"Error updating manifest: {e}")
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1 = v1_parts[i] if i < len(v1_parts) else 0
                v2 = v2_parts[i] if i < len(v2_parts) else 0
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0
        except:
            return 0
    
    def _get_file_hash_from_manifest(self, manifest: Dict, file_path: str) -> str:
        """Extract expected file hash from manifest"""
        try:
            files = manifest.get('files', {})
            # Handle both 'assets/file.png' and 'file.py' paths
            if '/' in file_path:
                dir_name, file_name = file_path.split('/', 1)
                file_info = files.get(dir_name, {}).get(file_name, '')
            else:
                file_info = files.get('code', {}).get(file_path, '')
            
            # Handle both string hash and dict with 'hash' key
            if isinstance(file_info, str):
                return file_info
            elif isinstance(file_info, dict):
                return file_info.get('hash', '')
        except:
            pass
        return ''
    
    def _download_file_chunked(self, file_path: str, data_folder: str, expected_hash: str, progress_callback: Callable = None) -> bool:
        """Download file in chunks with hash verification"""
        url_path = file_path.replace('\\', '/')
        url = f"{self.raw_url}/{url_path}"
        local_path = os.path.join(data_folder, file_path)
        temp_path = None  # Initialize to prevent UnboundLocalError in exception handler
        
        for attempt in range(3):
            try:
                # Stream download
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code != 200:
                    time.sleep(2)
                    continue
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # Create temp file
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                temp_path = local_path + '.tmp'
                
                # For Python files, we need to handle them specially
                is_python_file = file_path.endswith('.py')
                sha256_hash = hashlib.sha256() if not is_python_file else None
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            if not is_python_file:
                                sha256_hash.update(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size)
                
                # Verify hash if provided
                if expected_hash:
                    if is_python_file:
                        # For Python files, normalize line endings before hashing
                        try:
                            with open(temp_path, 'r', encoding='utf-8', newline='') as f:
                                content = f.read()
                                content = content.replace('\r\n', '\n')
                                actual_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                        except:
                            # Fallback to binary hash
                            actual_hash = self._calculate_file_hash(temp_path)
                    else:
                        actual_hash = sha256_hash.hexdigest()
                    
                    if actual_hash != expected_hash:
                        os.remove(temp_path)
                        time.sleep(2)
                        continue
                
                # Move temp file to final location
                if os.path.exists(local_path):
                    # Remove read-only attribute if present (so we can delete/replace)
                    try:
                        os.chmod(local_path, stat.S_IWRITE | stat.S_IREAD)
                    except Exception as chmod_err:
                        self._log(f"  Warning: Could not change permissions: {chmod_err}")
                    try:
                        os.remove(local_path)
                    except Exception as remove_err:
                        self._log(f"  ERROR: Could not remove existing file: {remove_err}")
                        raise
                os.rename(temp_path, local_path)
                
                # Make Python code files read-only for protection
                if file_path.endswith('.py'):
                    try:
                        os.chmod(local_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                    except:
                        pass  # Not critical if this fails
                
                return True
            
            except Exception as e:
                self._log(f"  Exception during download: {e}")
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                if attempt < 2:
                    time.sleep(2)
        
        return False
    
    def _create_backup(self, files_to_backup: List[str]):
        """Create backup of files before updating"""
        try:
            if os.path.exists(self.backup_folder):
                shutil.rmtree(self.backup_folder)
            os.makedirs(self.backup_folder, exist_ok=True)
            
            data_folder = '.toa'
            for file_path in files_to_backup:
                src = os.path.join(data_folder, file_path)
                if os.path.exists(src):
                    dst = os.path.join(self.backup_folder, file_path)
                    Path(dst).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            
            # Backup manifest
            if os.path.exists(self.local_manifest_file):
                shutil.copy2(self.local_manifest_file, os.path.join(self.backup_folder, 'manifest.json'))
        
        except Exception as e:
            print(f"Error creating backup: {e}")
    
    def _rollback_from_backup(self) -> bool:
        """Rollback to backup if update fails"""
        try:
            if not os.path.exists(self.backup_folder):
                return False
            
            data_folder = '.toa'
            for root, dirs, files in os.walk(self.backup_folder):
                for file in files:
                    src = os.path.join(root, file)
                    rel_path = os.path.relpath(src, self.backup_folder)
                    dst = os.path.join(data_folder, rel_path)
                    Path(dst).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            
            print("Rolled back to previous version")
            return True
        
        except Exception as e:
            print(f"Error rolling back: {e}")
            return False
    
    def _legacy_check_updates(self, directories: List[str], include_code: bool) -> Tuple[bool, List[str]]:
        """Legacy version.json based update check"""
        try:
            local_version = self._get_local_version()
            version_url = f"{self.raw_url}/version.json"
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            remote_version = json.loads(response.text)
            
            changed_files = []
            if 'assets' in remote_version.get('files', {}):
                remote_assets = remote_version['files']['assets']
                local_assets = local_version.get('files', {}).get('assets', {})
                for file_path, remote_hash in remote_assets.items():
                    if remote_hash != local_assets.get(file_path, ""):
                        changed_files.append(f"assets/{file_path}")
            
            if include_code and 'code' in remote_version.get('files', {}):
                remote_code = remote_version['files']['code']
                local_code = local_version.get('files', {}).get('code', {})
                for file_path, remote_hash in remote_code.items():
                    if remote_hash != local_code.get(file_path, ""):
                        changed_files.append(file_path)
            
            if changed_files:
                os.makedirs('.toa', exist_ok=True)
                with open(self.local_version_file, 'w') as f:
                    f.write(response.text)
            
            return len(changed_files) > 0, changed_files
        except Exception as e:
            print(f"Error in legacy check: {e}")
            return False, []
    
    def verify_file_integrity(self, file_path: str, data_folder: str = '.toa') -> bool:
        """Verify if a file matches its expected hash from manifest"""
        try:
            manifest = self._get_local_manifest()
            expected_hash = self._get_file_hash_from_manifest(manifest, file_path)
            
            if not expected_hash:
                return True  # No hash to verify against
            
            local_path = os.path.join(data_folder, file_path)
            if not os.path.exists(local_path):
                return False
            
            # Calculate hash with line ending normalization for .py files
            if file_path.endswith('.py'):
                try:
                    with open(local_path, 'r', encoding='utf-8', newline='') as f:
                        content = f.read()
                        content = content.replace('\r\n', '\n')
                        actual_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                except:
                    actual_hash = self._calculate_file_hash(local_path)
            else:
                actual_hash = self._calculate_file_hash(local_path)
            
            return actual_hash == expected_hash
        except:
            return True  # If we can't verify, assume it's OK
    
    def repair_file(self, file_path: str, data_folder: str = '.toa', progress_callback: Callable = None) -> bool:
        """Redownload a corrupted/modified file"""
        try:
            manifest = self._get_local_manifest()
            expected_hash = self._get_file_hash_from_manifest(manifest, file_path)
            
            # Make file writable before repairing
            local_path = os.path.join(data_folder, file_path)
            if os.path.exists(local_path):
                try:
                    os.chmod(local_path, stat.S_IWUSR | stat.S_IRUSR)
                except:
                    pass
            
            print(f"Repairing {file_path}...")
            success = self._download_file_chunked(file_path, data_folder, expected_hash, progress_callback)
            
            if success:
                print(f"✓ Repaired {file_path}")
            
            return success
        except Exception as e:
            print(f"Error repairing {file_path}: {e}")
            return False


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
                        # Normalize path separators to forward slashes for cross-platform compatibility
                        relative_path = relative_path.replace('\\', '/')
                        
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
