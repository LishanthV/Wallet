"""
NexWallet — Project Organizer (Safe Version)
Moves loose files from the root to their proper folders without overwriting newer versions.
"""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP = {
    '.html': 'templates',
    '.css': 'static/css',
    '.js': 'static/js',
    '.png': 'static/img',
    '.jpg': 'static/img',
    '.jpeg': 'static/img',
    '.sql': 'sql',
}

# Files that MUST stay in the root
IGNORE = {'app.py', 'organize_project.py', 'requirements.txt', 'README.md', 'upi_gmail_sync.py'}

def organize():
    print(f"🔍 NexWallet: Cleaning up root directory...")
    
    count = 0
    skipped = 0
    
    for item in ROOT.iterdir():
        # Only process loose files, ignore directories and protected files
        if not item.is_file() or item.name in IGNORE or item.name.startswith('.'):
            continue
            
        ext = item.suffix.lower()
        if ext in MAP:
            target_sub = MAP[ext]
            dest_dir = ROOT / target_sub
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_file = dest_dir / item.name
            
            # CRITICAL: Do not overwrite modernized versions in subfolders
            if dest_file.exists():
                print(f"⚠️  Skipping {item.name}: Newer version already exists in {target_sub}/")
                skipped += 1
            else:
                try:
                    shutil.move(str(item), str(dest_file))
                    print(f"✅ Moved: {item.name} -> {target_sub}/")
                    count += 1
                except Exception as e:
                    print(f"❌ Error moving {item.name}: {e}")

    print(f"\n✨ Cleanup Complete. {count} files moved, {skipped} files preserved.")

if __name__ == "__main__":
    organize()
