import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.database import db
from modules.researcher import researcher
from modules.scriptwriter import scriptwriter
from modules.voice_engine import voice_engine
from modules.subtitles import subtitle_engine
from modules.storage_uploader import storage_uploader
from modules.sheets_sync import sheets_sync

def run_diagnostics():
    print("======================================================================")
    print("🔍 RUNNING AUTOMATION SUITE DIAGNOSTICS")
    print("======================================================================")

    # 1. Check FFmpeg
    from modules.video_compositor import video_compositor
    ffmpeg_path = video_compositor.ffmpeg_bin
    ffmpeg_available = os.path.exists(ffmpeg_path) or shutil.which("ffmpeg") is not None
    print(f"\n[1] FFmpeg status: {'AVAILABLE (' + ffmpeg_path + ')' if ffmpeg_available else 'NOT FOUND IN PATH'}")

    # 2. Test News Researcher
    print("\n[2] Testing News Researcher (Cybersecurity, Pentesting & Tech)...")
    try:
        articles = researcher.discover_and_save_trending()
        print(f"    Scraped {len(articles)} fresh articles from RSS/Reddit/HN.")
        if articles:
            print(f"    Sample: '{articles[0]['title']}' ({articles[0]['category']})")
    except Exception as e:
        print(f"    Error during research: {e}")

    # 3. Test Scriptwriting
    print("\n[3] Testing Viral Scriptwriter...")
    sample_article = {
        "title": "Critical RCE Flaw Discovered in Apache Web Servers",
        "category": "Web Penetration Testing",
        "summary": "Researchers discovered a remote code execution exploit allowing hackers to take over web servers without authentication.",
        "url": "https://example.com/test-cve"
    }
    script_data = scriptwriter.generate_script(sample_article)
    print(f"    Title: {script_data['title']}")
    print(f"    Hook: {script_data['hook']}")
    print(f"    Script preview: {script_data['script'][:120]}...")

    # 4. Test Voice Engine (Edge-TTS)
    print("\n[4] Testing Free Neural TTS (Edge-TTS)...")
    try:
        test_audio, timings = voice_engine.generate_speech("Hackers found a loophole that lets anyone bypass passwords.", 9999)
        print(f"    Generated audio: {os.path.basename(test_audio)} ({os.path.getsize(test_audio)} bytes)")
        print(f"    Extracted {len(timings)} word timestamps for viral highlight captions.")
    except Exception as e:
        print(f"    Voice test failed: {e}")

    # 5. Test Subtitle Generator
    print("\n[5] Testing ASS Viral Highlight Subtitle Generator...")
    try:
        ass_path = subtitle_engine.generate_ass_subtitles(timings, 9999)
        print(f"    Generated ASS subtitles: {os.path.basename(ass_path)}")
    except Exception as e:
        print(f"    Subtitle test failed: {e}")

    # 6. Test Free Cloud Storage
    print("\n[6] Testing Free Cloud Storage (Telegram/Catbox)...")
    if storage_uploader.bot_token and storage_uploader.chat_id:
        print("    Telegram Bot storage is CONFIGURED.")
    else:
        print("    Telegram Bot keys not set. Free cloud fallback (Catbox.moe) is active.")

    # 7. Test Google Sheets Sync
    print("\n[7] Testing Google Sheets Sync...")
    sheet_link = sheets_sync.get_sheet_link()
    print(f"    Active Sheet / Template: {sheet_link}")

    print("\n======================================================================")
    print("✅ DIAGNOSTICS COMPLETE!")
    print("======================================================================")

if __name__ == "__main__":
    run_diagnostics()

