"""Publish only built frontend assets to Vercel's static CDN directory."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / "frontend" / "dist"
if not (source / "index.html").is_file():
    raise SystemExit("The frontend build is missing")
shutil.copytree(source, root / "public", dirs_exist_ok=True)
print("Frontend static assets prepared.")
