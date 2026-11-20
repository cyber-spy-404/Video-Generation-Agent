import os
import time
import requests
from typing import Dict, Any, Optional
from config import (
    INSTAGRAM_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    INSTAGRAM_AUTO_POST,
    INSTAGRAM_FB_POST_TIMES_IST,
    INSTAGRAM_FB_SCHEDULE_MODE
)
from modules.database import db
from modules.timing_manager import timing_manager

class InstagramUploader:
    def __init__(self):
        self.account_id = INSTAGRAM_ACCOUNT_ID
        self.access_token = INSTAGRAM_ACCESS_TOKEN
        self.username = INSTAGRAM_USERNAME
        self.password = INSTAGRAM_PASSWORD
        self.enabled = INSTAGRAM_AUTO_POST
        self.schedule_mode = INSTAGRAM_FB_SCHEDULE_MODE
        self.post_times_ist = INSTAGRAM_FB_POST_TIMES_IST

    def refresh_long_lived_token(self) -> Optional[str]:
        """
        Refreshes a 60-day Instagram user long-lived access token.
        Tokens can be refreshed when they are at least 24 hours old.
        """
        if not self.access_token:
            return None

        url = "https://graph.instagram.com/refresh_access_token"
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": self.access_token
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                new_token = data.get("access_token")
                if new_token:
                    self.access_token = new_token
                    db.log("INFO", "Instagram", "Instagram long-lived access token refreshed successfully!")
                    return new_token
        except Exception as e:
            db.log("WARNING", "Instagram", f"Token refresh warning: {e}")
        return None

    def post_reel_via_graph_api(
        self,
        public_video_url: str,
        caption: str,
        scheduled_publish_time: Optional[int] = None
    ) -> Optional[str]:
        """
        Publishes a Reel via Meta Graph API (Supports both graph.instagram.com & graph.facebook.com).
        Requires a public video URL (provided by Telegram or Catbox).
        Supports scheduled_publish_time (Unix timestamp in seconds for IST scheduling).
        """
        if not self.account_id or not self.access_token:
            return None

        db.log("INFO", "Instagram", "Publishing Reel via Meta Instagram Graph API...")

        # Try graph.instagram.com first (Instagram Login for Business API), fallback to graph.facebook.com
        base_hosts = ["https://graph.instagram.com/v21.0", "https://graph.facebook.com/v21.0"]

        container_id = None
        working_base = None

        payload = {
            "media_type": "REELS",
            "video_url": public_video_url,
            "caption": caption[:2200],
            "access_token": self.access_token
        }

        if scheduled_publish_time:
            payload["scheduled_publish_time"] = scheduled_publish_time
            db.log("INFO", "Instagram", f"Reel scheduled for IST drop at timestamp: {scheduled_publish_time}")

        # 1. Create Media Container
        for base in base_hosts:
            graph_url = f"{base}/{self.account_id}/media"
            try:
                resp = requests.post(graph_url, data=payload, timeout=30)
                if resp.status_code == 200:
                    container_id = resp.json().get("id")
                    working_base = base
                    db.log("INFO", "Instagram", f"Reel container created ({container_id}) via {base}. Processing...")
                    break
                else:
                    db.log("WARNING", "Instagram", f"Host {base} returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                db.log("WARNING", "Instagram", f"Error connecting to {base}: {e}")

        if not container_id or not working_base:
            db.log("ERROR", "Instagram", "Failed to create Instagram Reel container on all endpoints.")
            return None

        # If scheduled with scheduled_publish_time, container will be published automatically by Instagram
        if scheduled_publish_time:
            ig_scheduled_url = f"https://www.instagram.com/reel/scheduled_{container_id}/"
            db.log("INFO", "Instagram", f"Reel scheduled successfully in container {container_id}!")
            return ig_scheduled_url

        # 2. Poll Status until FINISHED
        status_url = f"{working_base}/{container_id}"
        for _ in range(30):
            time.sleep(10)
            try:
                status_resp = requests.get(status_url, params={"fields": "status_code", "access_token": self.access_token}, timeout=15)
                if status_resp.status_code == 200:
                    status_code = status_resp.json().get("status_code")
                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        db.log("ERROR", "Instagram", "Instagram server returned ERROR during video processing.")
                        return None
            except Exception as e:
                db.log("WARNING", "Instagram", f"Status poll exception: {e}")

        # 3. Publish Media
        publish_url = f"{working_base}/{self.account_id}/media_publish"
        try:
            pub_resp = requests.post(publish_url, data={"creation_id": container_id, "access_token": self.access_token}, timeout=30)
            if pub_resp.status_code == 200:
                post_id = pub_resp.json().get("id")
                ig_url = f"https://www.instagram.com/reel/{post_id}/"
                db.log("INFO", "Instagram", f"Reel published successfully: {ig_url}")
                return ig_url
            else:
                db.log("ERROR", "Instagram", f"Failed to publish container: {pub_resp.text}")
        except Exception as e:
            db.log("ERROR", "Instagram", f"Publish exception: {e}")

        return None

    def post_reel_via_instagrapi(self, video_path: str, caption: str) -> Optional[str]:
        """Publishes Reel via direct instagrapi client (personal accounts)."""
        if not self.username or not self.password:
            return None

        try:
            from instagrapi import Client
            cl = Client()
            cl.login(self.username, self.password)
            media = cl.clip_upload(video_path, caption=caption)
            media_code = getattr(media, "code", "")
            if media_code:
                ig_url = f"https://www.instagram.com/reel/{media_code}/"
                db.log("INFO", "Instagram", f"Reel published via instagrapi: {ig_url}")
                return ig_url
        except ImportError:
            db.log("WARNING", "Instagram", "instagrapi package not installed.")
        except Exception as e:
            db.log("ERROR", "Instagram", f"instagrapi publish failed: {str(e)}")

        return None

    def post_reel_via_resumable_upload(
        self,
        video_path: str,
        caption: str,
        scheduled_publish_time: Optional[int] = None
    ) -> Optional[str]:
        """
        Publishes a Reel via Meta Graph API Resumable Binary Upload.
        Uploads binary MP4 directly from local disk (zero external cloud storage needed).
        """
        if not self.account_id or not self.access_token:
            return None

        if not os.path.exists(video_path):
            db.log("ERROR", "Instagram", f"Video file not found for resumable upload: {video_path}")
            return None

        db.log("INFO", "Instagram", f"Initiating direct binary resumable Reel upload for {os.path.basename(video_path)}...")

        # Step 1: Initialize Resumable Container
        init_url = f"https://graph.facebook.com/v21.0/{self.account_id}/media"
        payload = {
            "upload_type": "resumable",
            "media_type": "REELS",
            "caption": caption[:2200],
            "access_token": self.access_token
        }
        if scheduled_publish_time:
            payload["scheduled_publish_time"] = scheduled_publish_time

        try:
            init_resp = requests.post(init_url, data=payload, timeout=30)
            if init_resp.status_code != 200:
                db.log("WARNING", "Instagram", f"Resumable init failed HTTP {init_resp.status_code}: {init_resp.text[:200]}")
                return None
            init_data = init_resp.json()
            container_id = init_data.get("id")
            upload_uri = init_data.get("uri")
            if not container_id or not upload_uri:
                db.log("ERROR", "Instagram", "Resumable init did not return container ID or upload URI.")
                return None

            # Step 2: Upload Binary Video Data to rupload.facebook.com
            file_size = os.path.getsize(video_path)
            db.log("INFO", "Instagram", f"Container {container_id} created. Uploading {file_size / (1024*1024):.2f} MB binary payload...")

            with open(video_path, "rb") as vf:
                video_bytes = vf.read()

            upload_headers = {
                "Authorization": f"OAuth {self.access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            upload_resp = requests.post(upload_uri, data=video_bytes, headers=upload_headers, timeout=180)
            if upload_resp.status_code not in (200, 201):
                db.log("ERROR", "Instagram", f"Binary transfer failed HTTP {upload_resp.status_code}: {upload_resp.text[:200]}")
                return None

            db.log("INFO", "Instagram", "Binary video transfer complete! Waiting for Meta processing...")

            if scheduled_publish_time:
                ig_scheduled_url = f"https://www.instagram.com/reel/scheduled_{container_id}/"
                db.log("INFO", "Instagram", f"Reel scheduled successfully in container {container_id}!")
                return ig_scheduled_url

            # Step 3: Poll status until FINISHED
            status_url = f"https://graph.facebook.com/v21.0/{container_id}"
            for _ in range(30):
                time.sleep(8)
                try:
                    status_resp = requests.get(status_url, params={"fields": "status_code", "access_token": self.access_token}, timeout=15)
                    if status_resp.status_code == 200:
                        code = status_resp.json().get("status_code")
                        if code == "FINISHED":
                            break
                        elif code == "ERROR":
                            db.log("ERROR", "Instagram", "Meta returned ERROR during Reel processing.")
                            return None
                except Exception:
                    pass

            # Step 4: Publish Media Container
            pub_url = f"https://graph.facebook.com/v21.0/{self.account_id}/media_publish"
            pub_resp = requests.post(pub_url, data={"creation_id": container_id, "access_token": self.access_token}, timeout=30)
            if pub_resp.status_code == 200:
                post_id = pub_resp.json().get("id")
                ig_url = f"https://www.instagram.com/reel/{post_id}/"
                db.log("INFO", "Instagram", f"Reel published successfully: {ig_url}")
                return ig_url
            else:
                db.log("ERROR", "Instagram", f"Failed to publish container: {pub_resp.text}")
                return None

        except Exception as e:
            db.log("ERROR", "Instagram", f"Resumable upload exception: {e}")
            return None

    def post_reel(
        self,
        video_path: str,
        public_video_url: str,
        title: str,
        script: str,
        scheduled_publish_time: Optional[int] = None,
        immediate: bool = False
    ) -> Optional[str]:
        """Unified publisher: tries Direct Binary Resumable Upload first, then URL Graph API, then instagrapi."""
        if not self.enabled:
            db.log("INFO", "Instagram", "Instagram auto-post is disabled in config.")
            return None

        if immediate:
            scheduled_publish_time = None
            db.log("INFO", "Instagram", "Direct Immediate Publication requested (No fixed time slots).")

        caption = (
            f"🚨 {title}\n\n"
            f"{script[:300]}...\n\n"
            f"#CyberSecurity #EthicalHacking #BugBounty #InfoSec #WebPentesting #Coding #TechNews #Reels"
        )

        # 1. Primary: Direct Binary Resumable Upload (Never depends on 3rd party storage)
        if os.path.exists(video_path):
            url = self.post_reel_via_resumable_upload(video_path, caption, scheduled_publish_time=scheduled_publish_time)
            if url:
                return url

        # 2. Secondary: Graph API via Public URL (if available)
        if public_video_url and public_video_url.startswith("http"):
            url = self.post_reel_via_graph_api(public_video_url, caption, scheduled_publish_time=scheduled_publish_time)
            if url:
                return url

        # 3. Tertiary: instagrapi fallback
        return self.post_reel_via_instagrapi(video_path, caption)

instagram_uploader = InstagramUploader()
