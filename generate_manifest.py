"""
Generate manifest.json for distribution
Run this script before pushing updates to GitHub
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file, normalizing line endings for text files"""
    sha256_hash = hashlib.sha256()
    
    # For Python files, normalize line endings to LF (GitHub style)
    if file_path.endswith('.py'):
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()
                # Normalize to LF
                content = content.replace('\r\n', '\n')
                sha256_hash.update(content.encode('utf-8'))
                return sha256_hash.hexdigest()
        except:
            pass  # Fall through to binary mode
    
    # For binary files and fallback
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)

def get_version_from_main() -> str:
    """Extract version from main.py"""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('__version__'):
                    parts = line.split('=')[1].strip()
                    for quote in ['"', "'"]:
                        if quote in parts:
                            return parts.split(quote)[1]
    except:
        pass
    return "0.5.0"

def generate_manifest(
    directories=['levels', 'beatmaps'],
    include_code=True,
    previous_version="0.4.0",
    output_file="manifest.json"
):
    """Generate enhanced manifest.json with file metadata"""
    
    current_version = get_version_from_main()
    
    manifest = {
        "version": current_version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "manifest_version": 1,
        "files": {},
        "patches": {},
        "rollback": {
            "previous_version": previous_version,
            "can_rollback": True
        }
    }
    
    total_size = 0
    file_count = 0
    
    # Track assets
    if os.path.exists('assets'):
        manifest['files']['assets'] = {}
        
        for root, dirs, files in os.walk('assets'):
            for file in files:
                if file.endswith(('.json', '.osu', '.mp3', '.wav', '.ogg', '.jpg', '.png', '.osz', '.ico', '.zip')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, 'assets')
                    relative_path = relative_path.replace('\\', '/')
                    
                    file_hash = calculate_file_hash(file_path)
                    file_size = get_file_size(file_path)
                    
                    manifest['files']['assets'][relative_path] = {
                        "hash": file_hash,
                        "size": file_size
                    }
                    
                    total_size += file_size
                    file_count += 1
    
    # Track code files
    if include_code:
        manifest['files']['code'] = {}
        code_files = [
            'main.py',
            'auto_updater.py',
            'launcher.py',
            'songpack_loader.py',
            'songpack_ui.py',
        ]
        
        for code_file in code_files:
            if os.path.exists(code_file):
                file_hash = calculate_file_hash(code_file)
                file_size = get_file_size(code_file)
                
                manifest['files']['code'][code_file] = {
                    "hash": file_hash,
                    "size": file_size
                }
                
                total_size += file_size
                file_count += 1
    
    # Generate patch info by comparing with old manifest if it exists
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                old_manifest = json.load(f)
            
            old_version = old_manifest.get('version', previous_version)
            changed_files = []
            removed_files = []
            
            # Find changed files
            for category in ['assets', 'code']:
                if category in manifest['files']:
                    for file_path, file_info in manifest['files'][category].items():
                        old_info = old_manifest.get('files', {}).get(category, {}).get(file_path, {})
                        if isinstance(file_info, dict) and isinstance(old_info, dict):
                            if file_info.get('hash') != old_info.get('hash'):
                                full_path = f"{category}/{file_path}" if category == 'assets' else file_path
                                changed_files.append(full_path)
                        elif file_info != old_info:
                            full_path = f"{category}/{file_path}" if category == 'assets' else file_path
                            changed_files.append(full_path)
            
            # Find removed files
            for category in ['assets', 'code']:
                if category in old_manifest.get('files', {}):
                    for file_path in old_manifest['files'][category]:
                        if file_path not in manifest['files'].get(category, {}):
                            full_path = f"{category}/{file_path}" if category == 'assets' else file_path
                            removed_files.append(full_path)
            
            # Add patch info
            if changed_files or removed_files:
                manifest['patches'][f"from_{old_version}"] = {
                    "description": f"Patch from {old_version} to {current_version}",
                    "changed_files": changed_files,
                    "removed_files": removed_files
                }
        except Exception as e:
            print(f"Warning: Could not generate patch info: {e}")
    
    # Save manifest
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Print summary
    print(f"✓ Generated {output_file}")
    print(f"  Version: {current_version}")
    print(f"  Files tracked: {file_count}")
    print(f"  Total size: {total_size / 1024 / 1024:.2f} MB")
    
    if manifest['patches']:
        for patch_key, patch_info in manifest['patches'].items():
            print(f"  Patch ({patch_key}): {len(patch_info['changed_files'])} changed, {len(patch_info['removed_files'])} removed")
    
    # Also generate legacy version.json for backwards compatibility
    legacy_version = {
        "version": current_version,
        "files": {}
    }
    
    for category in ['assets', 'code']:
        if category in manifest['files']:
            legacy_version['files'][category] = {}
            for file_path, file_info in manifest['files'][category].items():
                if isinstance(file_info, dict):
                    legacy_version['files'][category][file_path] = file_info['hash']
                else:
                    legacy_version['files'][category][file_path] = file_info
    
    with open('version.json', 'w') as f:
        json.dump(legacy_version, f, indent=2)
    
    print(f"✓ Generated version.json (legacy compatibility)")
    
    return manifest

if __name__ == "__main__":
    print("Generating manifest for TOA distribution...\n")
    
    # Get previous version from existing manifest or use default
    previous_version = "0.4.0"
    if os.path.exists("manifest.json"):
        try:
            with open("manifest.json", 'r') as f:
                old = json.load(f)
                previous_version = old.get('version', previous_version)
        except:
            pass
    
    manifest = generate_manifest(
        directories=['levels', 'beatmaps'],
        include_code=True,
        previous_version=previous_version
    )
    
    print("\n✓ Manifest generation complete!")
    print("  Push manifest.json and version.json to GitHub to publish update")
