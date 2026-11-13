import os
import json
import httplib2
from pathlib import Path
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config import (
    BASE_DIR,
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_TOKEN_FILE,
    YOUTUBE_PRIVACY_STATUS,
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_AUTO_UPLOAD,
    YOUTUBE_POST_TIMES_UTC,
    YOUTUBE_SCHEDULE_MODE
)
from modules.database import db
from modules.timing_manager import timing_manager

# YouTube Data API v3 Scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]

class YouTubeUploader:
    def __init__(self):
        self.secrets_file = BASE_DIR / YOUTUBE_CLIENT_SECRETS_FILE
        self.token_file = BASE_DIR / YOUTUBE_TOKEN_FILE
        self.privacy_status = YOUTUBE_PRIVACY_STATUS
        self.category_id = YOUTUBE_CATEGORY_ID
        self.enabled = YOUTUBE_AUTO_UPLOAD
        self.schedule_mode = YOUTUBE_SCHEDULE_MODE
        self.post_times_utc = YOUTUBE_POST_TIMES_UTC

    def get_authenticated_service(self):
        """Authenticates with YouTube API using OAuth2 credentials."""
        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                db.log("WARNING", "YouTube", f"Failed to load cached credentials: {e}")

        # If credentials don't exist or are invalid, refresh them
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                db.log("ERROR", "YouTube", f"Failed to refresh YouTube token: {e}")
                creds = None

        if not creds:
            if not self.secrets_file.exists():
                db.log("WARNING", "YouTube", f"Client secrets file '{self.secrets_file.name}' not found. Please add client_secrets.json.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.secrets_file), SCOPES)
                creds = flow.run_local_server(port=0, open_browser=False)
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                db.log("ERROR", "YouTube", f"OAuth flow initiation failed: {e}")
                return None

        return build("youtube", "v3", credentials=creds)

    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        publish_at: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Uploads vertical video directly to YouTube Studio as a YouTube Short.
        Supports automated UTC Peak Timing scheduling (e.g. 15:00 UTC / 20:00 UTC).
        Returns: {"id": video_id, "url": f"https://youtube.com/shorts/{video_id}", "publish_at": publish_at, "scheduled": bool}
        """
        if not self.enabled:
            db.log("INFO", "YouTube", "YouTube auto-upload is disabled in config.")
            return None

        youtube = self.get_authenticated_service()
        if not youtube:
            db.log("WARNING", "YouTube", "Skipping YouTube upload: service not authenticated.")
            return None

        # Ensure #Shorts is present in title and description for YouTube algorithm
        if "#shorts" not in title.lower():
            title = f"{title[:80]} #Shorts"

        if "#shorts" not in description.lower():
            description = f"{description}\n\n#Shorts #CyberSecurity #WebPentesting #EthicalHacking #ArtificialIntelligence"

        # Determine UTC Best Timing for Global Audience
        target_publish_at = publish_at
        schedule_summary = "Immediate Public"
        is_scheduled = False

        if target_publish_at is None and self.schedule_mode == "scheduled":
            _, auto_iso, schedule_summary = timing_manager.get_next_youtube_utc_slot(self.post_times_utc)
            target_publish_at = auto_iso

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:20],
                "categoryId": self.category_id
            },
            "status": {
                "selfDeclaredMadeForKids": False
            }
        }

        # YouTube Data API requires privacyStatus='private' when publishAt is specified
        if target_publish_at:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = target_publish_at
            is_scheduled = True
            db.log("INFO", "YouTube", f"Short scheduled for UTC drop: {target_publish_at} ({schedule_summary})")
        else:
            body["status"]["privacyStatus"] = self.privacy_status

        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024 * 2,  # 2MB chunks for resumable VPS upload
            resumable=True,
            mimetype="video/mp4"
        )

        db.log("INFO", "YouTube", f"Starting upload of '{title}' to YouTube Studio...")
        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    db.log("INFO", "YouTube", f"Uploading: {pct}% complete...")

            video_id = response.get("id")
            short_url = f"https://youtube.com/shorts/{video_id}"
            
            if is_scheduled:
                db.log("INFO", "YouTube", f"Upload complete! Scheduled for release at {target_publish_at}: {short_url}")
            else:
                db.log("INFO", "YouTube", f"Upload complete! Live now at: {short_url}")

            return {
                "id": video_id,
                "url": short_url,
                "scheduled": is_scheduled,
                "publish_at": target_publish_at,
                "schedule_summary": schedule_summary
            }

        except Exception as e:
            db.log("ERROR", "YouTube", f"YouTube upload failed: {str(e)}")
            return None

youtube_uploader = YouTubeUploader()

