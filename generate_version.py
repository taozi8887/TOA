"""
Generate version.json file for the TOA repository.
Run this script whenever you want to publish new updates.
"""

from auto_updater import create_version_file

if __name__ == "__main__":
    print("=" * 60)
    print("TOA Auto-Update Version Generator")
    print("=" * 60)
    print("\nThis will create a version.json file tracking:")
    print("  - Assets (including .osz files)")
    print("  - Python code files (main.py, etc.)")
    print("\nNote: Beatmaps and levels are generated from .osz files at runtime")
    print("      and are not tracked in version.json")
    print()
    
    # Create version file tracking assets AND code (but NOT beatmaps/levels)
    create_version_file(directories=['assets'], include_code=True, output_file='version.json')
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Commit version.json to your git repository")
    print("2. Push to GitHub")
    print("3. Update main.py with your GitHub username and repo name")
    print("   (Look for 'YOUR_GITHUB_USERNAME' and 'YOUR_REPO_NAME')")
    print("4. Rebuild your executable")
    print("5. Users will auto-update from your repository!")
    print("=" * 60)
