import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from config import DISCORD_WEBHOOK_URL
from modules.discord_notifier import DiscordNotifier, discord_notifier

def main():
    parser = argparse.ArgumentParser(description="Test Discord Webhook Notification")
    parser.add_argument("--url", type=str, help="Custom Discord Webhook URL to test", default=None)
    args = parser.parse_args()

    notifier = DiscordNotifier(args.url) if args.url else discord_notifier

    if not notifier.webhook_url:
        print("[!] DISCORD_WEBHOOK_URL is not configured.")
        print("[!] Add your webhook URL to .env as: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        print("[!] Or run: python scripts/test_discord.py --url https://discord.com/api/webhooks/...")
        return

    print(f"[*] Testing Discord Webhook: {notifier.webhook_url[:40]}...")
    
    # 1. Send test greeting
    print("[*] Sending test connection embed...")
    success = notifier.send_test_message()
    if success:
        print("[+] Test connection message delivered to Discord successfully!")
    else:
        print("[!] Failed to send test connection message.")

    # 2. Send sample video published embed
    sample_video = {
        "job_id": 101,
        "title": "🚨 Critical Zero-Day Exploit Analysis #Shorts",
        "hook": "A single missed character just exposed 50 million servers...",
        "duration": "39.2s",
        "word_count": "94 words",
        "voice": "en-US-GuyNeural (+16%) | Font: Anton (Electric Cyan)",
        "storage_url": "https://t.me/c/6150075369/6",
        "youtube_url": "https://youtube.com/shorts/test_verified",
        "execution_log": "Script (94w) -> Voice (39.2s, Guy) -> Subtitles (Anton) -> Telegram -> YouTube (Published)"
    }
    sample_article = {
        "category": "Web Penetration Testing",
        "url": "https://thehackernews.com/cve-2026-analysis"
    }

    print("[*] Sending sample video published drop embed...")
    success_video = notifier.send_video_update(sample_video, sample_article)
    if success_video:
        print("[+] Video drop notification delivered to Discord successfully!")
    else:
        print("[!] Failed to send video drop notification.")

if __name__ == "__main__":
    main()

