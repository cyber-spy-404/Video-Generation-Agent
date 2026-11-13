import requests
from datetime import datetime
from typing import Dict, Any, Optional
from config import DISCORD_WEBHOOK_URL
from modules.database import db

class DiscordNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or DISCORD_WEBHOOK_URL

    def send_video_update(self, video_data: Dict[str, Any], article_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Sends an attractive cyberpunk embed notification to a Discord channel when a video is published.
        """
        if not self.webhook_url:
            return False

        job_id = video_data.get("job_id", video_data.get("id", "?"))
        title = video_data.get("title", "Breaking Cyber Advisory")
        hook = video_data.get("hook", "")
        duration = video_data.get("duration", "40s")
        word_count = video_data.get("word_count", "95 words")
        voice_font = video_data.get("voice", "AI Voice")
        storage_url = video_data.get("storage_url", "")
        youtube_url = video_data.get("youtube_url", "")
        source_url = article_data.get("url", "") if article_data else ""
        category = article_data.get("category", "Cybersecurity") if article_data else "Cybersecurity"

        # Cyber Green if uploaded, Cyan if rendered, Gold if alert
        embed_color = 0x00FF66 if youtube_url and "youtube" in youtube_url else 0x00E5FF

        links_desc = []
        if youtube_url and "youtube" in youtube_url:
            links_desc.append(f"▶️ **[Watch on YouTube Shorts]({youtube_url})**")
        if storage_url:
            links_desc.append(f"☁️ **[Free Cloud Storage (Telegram)]({storage_url})**")
        if source_url:
            links_desc.append(f"📰 **[Original Advisory / CVE]({source_url})**")

        embed = {
            "title": f"🎬 New Short Published: {title}",
            "description": f"**Hook:** *\"{hook}\"*\n\n" + ("\n".join(links_desc) if links_desc else ""),
            "color": embed_color,
            "fields": [
                {
                    "name": "🏷️ Topic",
                    "value": category,
                    "inline": True
                },
                {
                    "name": "⏱️ Duration",
                    "value": f"{duration} ({word_count})",
                    "inline": True
                },
                {
                    "name": "🆔 Job ID",
                    "value": f"#{job_id}",
                    "inline": True
                },
                {
                    "name": "🎙️ Voice & Typography Profile",
                    "value": voice_font,
                    "inline": False
                },
                {
                    "name": "⚡ Pipeline Execution",
                    "value": video_data.get("execution_log", "Complete production pipeline executed."),
                    "inline": False
                }
            ],
            "footer": {
                "text": "CyberShorts AI • 24/7 Autonomous Video Production Suite"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "username": "CyberShorts AI Mission Control",
            "avatar_url": "https://img.icons8.com/neon/96/bot.png",
            "embeds": [embed]
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                db.log("INFO", "Discord", f"Published video notification sent for Job #{job_id}")
                return True
            else:
                db.log("WARNING", "Discord", f"Discord webhook returned HTTP {resp.status_code}")
        except Exception as e:
            db.log("ERROR", "Discord", f"Failed to send Discord notification: {e}")

        return False

    def send_error_alert(self, job_id: int, title: str, error_msg: str) -> bool:
        """
        Sends an emergency red embed notification to Discord if a pipeline job fails.
        """
        if not self.webhook_url:
            return False

        embed = {
            "title": f"⚠️ Pipeline Production Warning: Job #{job_id}",
            "description": f"An issue was encountered while processing **{title}**.",
            "color": 0xFF0033,  # Cyber Red Alert
            "fields": [
                {
                    "name": "🚨 Error Details",
                    "value": f"```{error_msg[:900]}```",
                    "inline": False
                }
            ],
            "footer": {
                "text": "CyberShorts AI • Automated Diagnostics"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "username": "CyberShorts AI Alert",
            "avatar_url": "https://img.icons8.com/neon/96/error.png",
            "embeds": [embed]
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def send_test_message(self) -> bool:
        """Sends a verification message to ensure Discord webhook connectivity."""
        if not self.webhook_url:
            return False

        payload = {
            "username": "CyberShorts AI Mission Control",
            "avatar_url": "https://img.icons8.com/neon/96/bot.png",
            "embeds": [{
                "title": "⚡ CyberShorts AI Discord Link Established",
                "description": "Your Discord channel is now connected to receive automated video drops, YouTube Shorts links, Telegram storage backups, and daily production reports!",
                "color": 0x00E5FF,
                "fields": [
                    {"name": "Status", "value": "🟢 Online & Monitoring", "inline": True},
                    {"name": "Daily Quota", "value": "Max 2 Videos/Day", "inline": True},
                    {"name": "Active Channels", "value": "YouTube Shorts, Telegram, Google Sheets", "inline": False}
                ],
                "footer": {"text": "CyberShorts AI • Autonomous 24/7 Engine"},
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"Discord test failed: {e}")
            return False

discord_notifier = DiscordNotifier()

