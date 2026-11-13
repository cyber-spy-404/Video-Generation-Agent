import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.youtube_uploader import youtube_uploader

def main():
    print("Testing YouTube Studio Data API v3 Connection...")
    try:
        service = youtube_uploader.get_authenticated_service()
        if not service:
            print("[!] Could not initialize service.")
            return

        resp = service.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if items:
            channel = items[0]
            title = channel["snippet"]["title"]
            sub_count = channel["statistics"].get("subscriberCount", "0")
            video_count = channel["statistics"].get("videoCount", "0")
            print(f"[✔] SUCCESS! Connected to YouTube Channel: '{title}'")
            print(f"    Subscribers: {sub_count}")
            print(f"    Total Videos: {video_count}")
        else:
            print("[+] Authenticated successfully, but no YouTube Channel was found on this Google Account.")
            print("    Please create a YouTube channel under this Google account at https://www.youtube.com/create_channel")
    except Exception as e:
        print("[!] Error connecting to YouTube API:", e)

if __name__ == "__main__":
    main()

