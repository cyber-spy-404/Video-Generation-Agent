import os
import requests
from typing import Dict, Any, Optional
from config import (
    FACEBOOK_PAGE_ID,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    FACEBOOK_AUTO_POST,
    INSTAGRAM_FB_POST_TIMES_IST,
    INSTAGRAM_FB_SCHEDULE_MODE
)
from modules.database import db
from modules.timing_manager import timing_manager

class FacebookUploader:
    def __init__(self):
        self.page_id = FACEBOOK_PAGE_ID
        self.page_access_token = FACEBOOK_PAGE_ACCESS_TOKEN
        self.enabled = FACEBOOK_AUTO_POST
        self.schedule_mode = INSTAGRAM_FB_SCHEDULE_MODE
        self.post_times_ist = INSTAGRAM_FB_POST_TIMES_IST

    def post_video_reel(
        self,
        video_path: str,
        public_video_url: str,
        title: str,
        script: str,
        scheduled_publish_time: Optional[int] = None
    ) -> Optional[str]:
        """
        Publishes a vertical video / Reel to your Facebook Page using the Meta Graph API.
        Supports automated IST Peak Timing scheduling (13:00 IST / 20:00 IST).
        Returns: Facebook Reel/Video URL (e.g. https://www.facebook.com/watch/?v=123456789)
        """
        if not self.enabled:
            db.log("INFO", "Facebook", "Facebook auto-post is disabled in config.")
            return None

        if not self.page_id or not self.page_access_token:
            db.log("WARNING", "Facebook", "Facebook Page ID or Page Access Token is missing. Skipping Facebook upload.")
            return None

        db.log("INFO", "Facebook", f"Publishing video to Facebook Page {self.page_id}...")

        caption = (
            f"🚨 {title}\n\n"
            f"{script[:350]}...\n\n"
            f"#CyberSecurity #TechNews #EthicalHacking #WebPentesting #ZeroDay #Infosec #Reels"
        )

        api_url = f"https://graph.facebook.com/v21.0/{self.page_id}/videos"

        # Determine target IST schedule if applicable
        target_schedule_time = scheduled_publish_time
        if target_schedule_time is None and self.schedule_mode == "scheduled":
            _, auto_ts, summary = timing_manager.get_next_instagram_ist_slot(self.post_times_ist)
            target_schedule_time = auto_ts
            db.log("INFO", "Facebook", f"Targeting IST drop slot: {summary}")

        extra_params = {}
        if target_schedule_time:
            extra_params["published"] = False
            extra_params["scheduled_publish_time"] = target_schedule_time
        else:
            extra_params["published"] = True

        # Method 1: Upload via public video URL (Fastest, zero VPS upload bandwidth)
        if public_video_url and public_video_url.startswith("http"):
            try:
                payload = {
                    "file_url": public_video_url,
                    "title": title[:100],
                    "description": caption[:5000],
                    "access_token": self.page_access_token,
                    **extra_params
                }
                resp = requests.post(api_url, data=payload, timeout=45)
                if resp.status_code == 200:
                    video_id = resp.json().get("id")
                    fb_url = f"https://www.facebook.com/watch/?v={video_id}"
                    status_lbl = f"scheduled for IST {target_schedule_time}" if target_schedule_time else "live"
                    db.log("INFO", "Facebook", f"Facebook video ({status_lbl}) published successfully! Link: {fb_url}")
                    return fb_url
                else:
                    db.log("WARNING", "Facebook", f"URL upload responded HTTP {resp.status_code}: {resp.text[:200]}. Trying direct binary file upload...")
            except Exception as e:
                db.log("WARNING", "Facebook", f"URL upload failed ({e}), falling back to binary upload...")

        # Method 2: Direct Binary Upload
        try:
            with open(video_path, "rb") as video_file:
                payload = {
                    "title": title[:100],
                    "description": caption[:5000],
                    "access_token": self.page_access_token,
                    **extra_params
                }
                files = {"source": video_file}
                resp = requests.post(api_url, data=payload, files=files, timeout=120)
                if resp.status_code == 200:
                    video_id = resp.json().get("id")
                    fb_url = f"https://www.facebook.com/watch/?v={video_id}"
                    db.log("INFO", "Facebook", f"Facebook binary upload successful! Link: {fb_url}")
                    return fb_url
                else:
                    db.log("ERROR", "Facebook", f"Facebook upload failed HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            db.log("ERROR", "Facebook", f"Facebook direct upload failed: {e}")

        return None

facebook_uploader = FacebookUploader()

