import os
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = BASE_DIR / "cybershorts-vps-deploy.zip"

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "node_modules"
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log"
}

EXCLUDE_STORAGE_SUBDIRS = {
    "videos",
    "audio",
    "subtitles",
    "cache"
}

def build_package():
    print(f"[*] Building deployment archive: {OUTPUT_ZIP.name}...")
    
    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            rel_root = Path(root).relative_to(BASE_DIR)

            # Skip storage media folders
            if len(rel_root.parts) >= 2 and rel_root.parts[0] == "storage" and rel_root.parts[1] in EXCLUDE_STORAGE_SUBDIRS:
                continue

            for file in files:
                file_path = Path(root) / file
                rel_file = file_path.relative_to(BASE_DIR)

                if file_path == OUTPUT_ZIP:
                    continue

                if file_path.suffix.lower() in EXCLUDE_EXTS:
                    continue

                # Skip any large generated video/audio files
                if file_path.suffix.lower() in [".mp4", ".mp3", ".wav", ".db", ".sqlite"]:
                    continue

                zipf.write(file_path, arcname=str(rel_file))
                file_count += 1
                total_uncompressed_bytes += file_path.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)

    print(f"[+] Archive created successfully!")
    print(f"    • Files included: {file_count}")
    print(f"    • Uncompressed size: {raw_size_mb:.2f} MB")
    print(f"    • Compressed zip size: {zip_size_mb:.2f} MB")
    print(f"    • Target: {OUTPUT_ZIP.resolve()}")

if __name__ == "__main__":
    build_package()

