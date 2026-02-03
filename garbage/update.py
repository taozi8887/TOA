"""
Quick update script to push changes to GitHub
Usage: python update.py "Your commit message"
"""

import subprocess
import sys

if len(sys.argv) < 2:
    print("Usage: python update.py \"Your commit message\"")
    sys.exit(1)

commit_msg = sys.argv[1]

print("=" * 60)
print("Step 1: Pushing changed files...")
print("=" * 60)
result = subprocess.run(
    f'git add main.py && git commit -m "{commit_msg}" && git push origin main',
    shell=True
)
if result.returncode != 0:
    print("Failed to push changes")
    sys.exit(1)

print("\n" + "=" * 60)
print("Step 2: Generating version.json from GitHub...")
print("=" * 60)
result = subprocess.run("python generate_version_from_github.py", shell=True)
if result.returncode != 0:
    print("Failed to generate version.json")
    sys.exit(1)

print("\n" + "=" * 60)
print("Step 3: Pushing version.json...")
print("=" * 60)
result = subprocess.run(
    'git add version.json && git commit -m "Update version.json" && git push origin main',
    shell=True
)
if result.returncode != 0:
    print("Failed to push version.json")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ Update complete!")
print("=" * 60)
