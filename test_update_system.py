"""
Test the professional update system
Run this to verify everything works before pushing to GitHub
"""

import os
import sys
import json
from auto_updater import AutoUpdater

def test_manifest_generation():
    """Test 1: Check if manifest was generated correctly"""
    print("Test 1: Manifest Generation")
    print("-" * 50)
    
    if not os.path.exists('manifest.json'):
        print("❌ FAIL: manifest.json not found")
        print("   Run: python generate_manifest.py")
        return False
    
    try:
        with open('manifest.json', 'r') as f:
            manifest = json.load(f)
        
        required_keys = ['version', 'release_date', 'manifest_version', 'files']
        for key in required_keys:
            if key not in manifest:
                print(f"❌ FAIL: Missing key '{key}' in manifest")
                return False
        
        file_count = sum(len(files) for files in manifest['files'].values())
        print(f"✓ manifest.json is valid")
        print(f"  Version: {manifest['version']}")
        print(f"  Files tracked: {file_count}")
        print(f"  Release date: {manifest['release_date']}")
        
        return True
    
    except Exception as e:
        print(f"❌ FAIL: Error reading manifest: {e}")
        return False

def test_version_compatibility():
    """Test 2: Check if version.json exists for backwards compatibility"""
    print("\nTest 2: Backwards Compatibility")
    print("-" * 50)
    
    if not os.path.exists('version.json'):
        print("❌ FAIL: version.json not found")
        print("   Run: python generate_manifest.py")
        return False
    
    try:
        with open('version.json', 'r') as f:
            version = json.load(f)
        
        if 'version' not in version or 'files' not in version:
            print("❌ FAIL: version.json missing required keys")
            return False
        
        print(f"✓ version.json is valid (legacy support)")
        print(f"  Version: {version['version']}")
        
        return True
    
    except Exception as e:
        print(f"❌ FAIL: Error reading version.json: {e}")
        return False

def test_config_file():
    """Test 3: Check update configuration"""
    print("\nTest 3: Update Configuration")
    print("-" * 50)
    
    config_path = 'update_config.json'
    if not os.path.exists(config_path):
        print(f"⚠️  WARNING: {config_path} not found")
        return True  # Not critical for GitHub
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        auto_update = config.get('auto_update', {})
        
        if not auto_update.get('github_username'):
            print("⚠️  WARNING: github_username not set")
        
        if not auto_update.get('repository_name'):
            print("⚠️  WARNING: repository_name not set")
        
        print(f"✓ Configuration loaded")
        print(f"  Repository: {auto_update.get('github_username')}/{auto_update.get('repository_name')}")
        print(f"  Branch: {auto_update.get('branch', 'main')}")
        print(f"  Auto-update: {auto_update.get('enabled', False)}")
        
        return True
    
    except Exception as e:
        print(f"⚠️  WARNING: Error reading config: {e}")
        return True

def test_updater_initialization():
    """Test 4: Check if AutoUpdater can be initialized"""
    print("\nTest 4: AutoUpdater Initialization")
    print("-" * 50)
    
    try:
        updater = AutoUpdater("taozi8887", "TOA", "main")
        print("✓ AutoUpdater initialized successfully")
        print(f"  Repository URL: {updater.raw_url}")
        
        return True
    
    except Exception as e:
        print(f"❌ FAIL: Could not initialize AutoUpdater: {e}")
        return False

def test_version_comparison():
    """Test 5: Test version comparison logic"""
    print("\nTest 5: Version Comparison")
    print("-" * 50)
    
    try:
        updater = AutoUpdater("test", "test")
        
        tests = [
            ("0.6.0", "0.5.0", 1),  # newer
            ("0.5.0", "0.6.0", -1),  # older
            ("0.5.0", "0.5.0", 0),  # equal
            ("1.0.0", "0.9.9", 1),  # major version
            ("0.10.0", "0.9.0", 1),  # double digits
        ]
        
        all_passed = True
        for v1, v2, expected in tests:
            result = updater._version_compare(v1, v2)
            if result == expected:
                print(f"  ✓ {v1} vs {v2} = {result} (expected {expected})")
            else:
                print(f"  ❌ {v1} vs {v2} = {result} (expected {expected})")
                all_passed = False
        
        if all_passed:
            print("✓ Version comparison working correctly")
        
        return all_passed
    
    except Exception as e:
        print(f"❌ FAIL: Version comparison error: {e}")
        return False

def test_hash_calculation():
    """Test 6: Test file hash calculation"""
    print("\nTest 6: Hash Calculation")
    print("-" * 50)
    
    try:
        updater = AutoUpdater("test", "test")
        
        # Test with manifest.json itself
        if os.path.exists('manifest.json'):
            hash1 = updater._calculate_file_hash('manifest.json')
            hash2 = updater._calculate_file_hash('manifest.json')
            
            if hash1 == hash2 and len(hash1) == 64:
                print(f"✓ Hash calculation working")
                print(f"  manifest.json hash: {hash1[:16]}...")
                return True
            else:
                print(f"❌ FAIL: Hash mismatch or invalid length")
                return False
        else:
            print("⚠️  WARNING: No files to test hash calculation")
            return True
    
    except Exception as e:
        print(f"❌ FAIL: Hash calculation error: {e}")
        return False

def test_file_structure():
    """Test 7: Check critical files exist"""
    print("\nTest 7: File Structure")
    print("-" * 50)
    
    critical_files = [
        'main.py',
        'launcher.py',
        'auto_updater.py',
        'generate_manifest.py'
    ]
    
    all_exist = True
    for file in critical_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ❌ Missing: {file}")
            all_exist = False
    
    if all_exist:
        print("✓ All critical files present")
    
    return all_exist

def main():
    """Run all tests"""
    print("=" * 50)
    print("Testing Professional Update System")
    print("=" * 50)
    print()
    
    tests = [
        test_file_structure,
        test_manifest_generation,
        test_version_compatibility,
        test_config_file,
        test_updater_initialization,
        test_version_comparison,
        test_hash_calculation
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            results.append(False)
        print()
    
    # Summary
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Update __version__ in main.py")
        print("  2. Run: python generate_manifest.py")
        print("  3. Commit and push to GitHub")
        return 0
    else:
        print(f"❌ {total - passed} tests failed. Fix issues before deploying.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
