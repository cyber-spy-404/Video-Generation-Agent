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

        # Proactively ensure we use direct Page Access Token if a User Token was supplied
        if self.enabled and self.page_id and self.page_access_token:
            self._attempt_resolve_page_token()

    def _attempt_resolve_page_token(self) -> Optional[str]:
        """
        If the configured access token is a User Token that lacks direct Page write permissions,
        calls /me/accounts to auto-discover and extract the true Page Access Token for self.page_id.
        """
        try:
            url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={self.page_access_token}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                accounts = resp.json().get("data", [])
                for acc in accounts:
                    if str(acc.get("id")) == str(self.page_id):
                        page_token = acc.get("access_token")
                        if page_token:
                            db.log("INFO", "Facebook", f"Auto-resolved Page Access Token for Page '{acc.get('name')}' ({self.page_id})!")
                            self.page_access_token = page_token
                            return page_token
        except Exception as e:
            db.log("WARNING", "Facebook", f"Could not auto-resolve Page token from /me/accounts: {e}")
        return None

    def post_video_reel(
        self,
        video_path: str,
        public_video_url: str,
        title: str,
        script: str,
        scheduled_publish_time: Optional[int] = None,
        immediate: bool = False
    ) -> Optional[str]:
        """
        Publishes a vertical video / Reel to your Facebook Page using the Meta Graph API.
        Supports automated IST Peak Timing scheduling or direct immediate publication.
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
        if immediate:
            target_schedule_time = None
            db.log("INFO", "Facebook", "Direct Immediate Publication requested (No fixed time slots).")
        elif target_schedule_time is None and self.schedule_mode == "scheduled":
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
                    if "No permission" in resp.text or "OAuthException" in resp.text:
                        resolved = self._attempt_resolve_page_token()
                        if resolved:
                            payload["access_token"] = resolved
                            retry_resp = requests.post(api_url, data=payload, timeout=45)
                            if retry_resp.status_code == 200:
                                video_id = retry_resp.json().get("id")
                                fb_url = f"https://www.facebook.com/watch/?v={video_id}"
                                db.log("INFO", "Facebook", f"Facebook video published after token resolution! Link: {fb_url}")
                                return fb_url
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
                    if "No permission" in resp.text or "OAuthException" in resp.text:
                        resolved = self._attempt_resolve_page_token()
                        if resolved:
                            video_file.seek(0)
                            payload["access_token"] = resolved
                            retry_resp = requests.post(api_url, data=payload, files={"source": video_file}, timeout=120)
                            if retry_resp.status_code == 200:
                                video_id = retry_resp.json().get("id")
                                fb_url = f"https://www.facebook.com/watch/?v={video_id}"
                                db.log("INFO", "Facebook", f"Facebook binary upload successful after token resolution! Link: {fb_url}")
                                return fb_url
                    db.log("ERROR", "Facebook", f"Facebook upload failed HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            db.log("ERROR", "Facebook", f"Facebook direct upload failed: {e}")

        return None

facebook_uploader = FacebookUploader()

