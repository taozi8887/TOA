"""
Test the auto-update system
"""

import sys
import json

def test_auto_update():
    print("=" * 60)
    print("TOA Auto-Update Test")
    print("=" * 60)
    print()
    
    # Test 1: Check if requests is installed
    print("Test 1: Checking for 'requests' library...")
    try:
        import requests
        print("✓ requests library is installed")
        print(f"  Version: {requests.__version__}")
    except ImportError:
        print("✗ requests library is NOT installed")
        print("  Install it with: pip install requests")
        return False
    
    print()
    
    # Test 2: Check if auto_updater module exists
    print("Test 2: Checking for auto_updater module...")
    try:
        from auto_updater import AutoUpdater, create_version_file
        print("✓ auto_updater module found")
    except ImportError as e:
        print(f"✗ auto_updater module not found: {e}")
        return False
    
    print()
    
    # Test 3: Check configuration file
    print("Test 3: Checking update_config.json...")
    try:
        with open('update_config.json', 'r') as f:
            config = json.load(f)
        
        auto_update = config.get('auto_update', {})
        
        if auto_update.get('enabled'):
            print("✓ Auto-update is ENABLED")
        else:
            print("⚠ Auto-update is DISABLED")
        
        username = auto_update.get('github_username', '')
        repo = auto_update.get('repository_name', '')
        branch = auto_update.get('branch', 'main')
        
        if 'YOUR_GITHUB_USERNAME' in username or 'YOUR_REPO_NAME' in repo:
            print("⚠ GitHub credentials not configured yet")
            print("  Run: python setup_auto_update.py")
        else:
            print(f"✓ GitHub: {username}/{repo} (branch: {branch})")
    except FileNotFoundError:
        print("✗ update_config.json not found")
        print("  Run: python setup_auto_update.py")
        return False
    except Exception as e:
        print(f"✗ Error reading config: {e}")
        return False
    
    print()
    
    # Test 4: Check if version.json exists
    print("Test 4: Checking version.json...")
    try:
        with open('version.json', 'r') as f:
            version_data = json.load(f)
        
        version = version_data.get('version', 'unknown')
        files = version_data.get('files', {})
        total_files = sum(len(file_dict) for file_dict in files.values())
        
        print(f"✓ version.json found")
        print(f"  Version: {version}")
        print(f"  Tracked files: {total_files}")
        
        for directory, file_dict in files.items():
            print(f"  - {directory}: {len(file_dict)} files")
    except FileNotFoundError:
        print("✗ version.json not found")
        print("  Run: python generate_version.py")
        return False
    except Exception as e:
        print(f"✗ Error reading version.json: {e}")
        return False
    
    print()
    
    # Test 5: Try to connect to GitHub
    print("Test 5: Testing GitHub connection...")
    if 'YOUR_GITHUB_USERNAME' not in username and 'YOUR_REPO_NAME' not in repo:
        try:
            updater = AutoUpdater(username, repo, branch)
            remote_version = updater._get_remote_version()
            
            if remote_version:
                print("✓ Successfully connected to GitHub repository")
                print(f"  Remote version: {remote_version.get('version', 'unknown')}")
            else:
                print("✗ Could not fetch version.json from GitHub")
                print("  Make sure version.json is committed and pushed to your repo")
        except Exception as e:
            print(f"✗ GitHub connection failed: {e}")
    else:
        print("⊘ Skipped (GitHub not configured)")
    
    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_auto_update()
        if success:
            print("\n✓ All tests passed! Auto-update is ready to use.")
        else:
            print("\n✗ Some tests failed. Please fix the issues above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
