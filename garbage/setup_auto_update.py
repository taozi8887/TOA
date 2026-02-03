"""
Quick setup script for TOA auto-update system
"""

import json
import os

def setup_auto_update():
    print("=" * 60)
    print("TOA Auto-Update Setup")
    print("=" * 60)
    print()
    
    # Get GitHub information
    print("Enter your GitHub information:")
    github_username = input("GitHub Username: ").strip()
    repo_name = input("Repository Name: ").strip()
    branch = input("Branch (press Enter for 'main'): ").strip() or "main"
    
    # Confirm
    print()
    print("Configuration:")
    print(f"  GitHub URL: https://github.com/{github_username}/{repo_name}")
    print(f"  Branch: {branch}")
    print()
    
    confirm = input("Is this correct? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Setup cancelled.")
        return
    
    # Create/update config file
    config = {
        "auto_update": {
            "enabled": True,
            "github_username": github_username,
            "repository_name": repo_name,
            "branch": branch,
            "update_on_startup": True,
            "directories_to_sync": ["levels", "beatmaps"]
        },
        "comment": "Configure auto-update settings here. Change 'enabled' to false to disable auto-updates."
    }
    
    with open('update_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print()
    print("✓ Configuration saved to update_config.json")
    print()
    
    # Generate version file
    print("Generating version.json...")
    try:
        from auto_updater import create_version_file
        create_version_file(directories=['levels', 'beatmaps'], output_file='version.json')
        print("✓ version.json created")
    except Exception as e:
        print(f"✗ Failed to create version.json: {e}")
        print("  You can run 'python generate_version.py' manually later.")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("NEXT STEPS:")
    print("1. Commit both files to git:")
    print("   git add update_config.json version.json")
    print("   git commit -m 'Configure auto-update system'")
    print()
    print("2. Push to GitHub:")
    print("   git push origin " + branch)
    print()
    print("3. Rebuild your executable (if needed):")
    print("   python build_exe.py")
    print()
    print("4. Done! The game will now auto-update from GitHub.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        setup_auto_update()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
    except Exception as e:
        print(f"\n\nError during setup: {e}")
