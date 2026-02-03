git add main.py; git commit -m "v0.6.29: update"; python generate_manifest.py; git add manifest.json version.json; git commit -m "Update manifest for v0.6.29"; git push origin main




$r = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/taozi8887/TOA/main/manifest.json?t=$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())" -UseBasicParsing; ($r.Content | ConvertFrom-Json).version