import os
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from modules.database import db

class StorageUploader:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID

    def upload_to_telegram(self, file_path: str, caption: str) -> Optional[str]:
        """
        Uploads video to Telegram Channel/Cloud (100% Free Unlimited Storage).
        Features multi-attempt socket retry and high transfer timeout to avoid write timeouts.
        Returns permanent storage URL or message link.
        """
        if not self.bot_token or not self.chat_id:
            db.log("INFO", "Storage", "Telegram Bot Token or Chat ID not configured. Skipping Telegram.")
            return None

        if not os.path.exists(file_path):
            db.log("ERROR", "Storage", f"File not found for Telegram upload: {file_path}")
            return None

        file_name = os.path.basename(file_path)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendVideo"

        try:
            with open(file_path, "rb") as vf:
                video_bytes = vf.read()
        except Exception as e:
            db.log("ERROR", "Storage", f"Failed reading video bytes: {e}")
            return None

        file_size_mb = len(video_bytes) / (1024 * 1024)

        for attempt in range(1, 4):
            try:
                db.log("INFO", "Storage", f"Uploading {file_name} ({file_size_mb:.2f} MB) to Telegram Cloud (Attempt {attempt}/3)...")
                files = {"video": (file_name, video_bytes, "video/mp4")}
                payload = {
                    "chat_id": self.chat_id,
                    "caption": caption[:1024],
                    "supports_streaming": True
                }
                # Use (connect_timeout, read_write_timeout) tuple: 30s connect, 300s for transfer
                resp = requests.post(url, data=payload, files=files, timeout=(30, 300))

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        msg_id = data["result"]["message_id"]
                        file_id = data["result"]["video"]["file_id"]

                        # 1. Fetch direct public video download URL for Meta Graph API / web ingestion
                        try:
                            file_info_resp = requests.get(
                                f"https://api.telegram.org/bot{self.bot_token}/getFile",
                                params={"file_id": file_id},
                                timeout=20
                            )
                            if file_info_resp.status_code == 200:
                                f_data = file_info_resp.json()
                                if f_data.get("ok"):
                                    f_path = f_data["result"]["file_path"]
                                    direct_dl_url = f"https://api.telegram.org/file/bot{self.bot_token}/{f_path}"
                                    db.log("INFO", "Storage", f"Telegram direct public media URL ready: {direct_dl_url}")
                                    return direct_dl_url
                        except Exception as e_dl:
                            db.log("WARNING", "Storage", f"Could not resolve Telegram direct URL: {e_dl}")

                        # 2. Format channel message link if chat_id starts with -100
                        clean_channel = str(self.chat_id).replace("-100", "")
                        storage_link = f"https://t.me/c/{clean_channel}/{msg_id}"

                        db.log("INFO", "Storage", f"Telegram upload complete! Storage link: {storage_link}")
                        return storage_link
                    else:
                        db.log("WARNING", "Storage", f"Telegram API returned ok=False: {data.get('description')}")
                else:
                    db.log("WARNING", "Storage", f"Telegram upload attempt {attempt} returned HTTP {resp.status_code}: {resp.text[:200]}")

            except (requests.exceptions.RequestException, TimeoutError) as e:
                db.log("WARNING", "Storage", f"Telegram upload attempt {attempt}/3 error: {e}")
                if attempt < 3:
                    time.sleep(3 * attempt)

        return None

    def upload_to_tmpfiles_fallback(self, file_path: str) -> Optional[str]:
        """
        Fast zero-login instant public cloud storage fallback (Tmpfiles.org).
        Provides direct public MP4 URLs.
        """
        db.log("INFO", "Storage", f"Uploading {os.path.basename(file_path)} to Tmpfiles cloud...")
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "video/mp4")}
                resp = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=(20, 180))
                if resp.status_code == 200:
                    data = resp.json()
                    url = data.get("data", {}).get("url")
                    if url:
                        direct_url = url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                        db.log("INFO", "Storage", f"Tmpfiles upload complete! Direct link: {direct_url}")
                        return direct_url
        except Exception as e:
            db.log("WARNING", "Storage", f"Tmpfiles fallback upload failed: {e}")
        return None

    def upload_to_catbox_fallback(self, file_path: str) -> Optional[str]:
        """
        Zero-login instant free cloud storage fallback (Catbox.moe).
        Allows immediate testing without any setup.
        """
        db.log("INFO", "Storage", f"Uploading {os.path.basename(file_path)} to Catbox free storage...")
        try:
            url = "https://catbox.moe/user/api.php"
            with open(file_path, "rb") as f:
                data = {"reqtype": "fileupload"}
                files = {"fileToUpload": f}
                resp = requests.post(url, data=data, files=files, timeout=(20, 120))
                if resp.status_code == 200 and resp.text.startswith("http"):
                    link = resp.text.strip()
                    db.log("INFO", "Storage", f"Catbox upload complete! Link: {link}")
                    return link
        except Exception as e:
            db.log("WARNING", "Storage", f"Catbox fallback upload failed: {str(e)}")
        return None

    def upload_video(self, file_path: str, title: str, category: str) -> str:
        """
        Primary storage pipeline: Tries Telegram (unlimited), fallbacks to Tmpfiles and Catbox.
        """
        caption = f"🎬 {title}\n📂 Niche: {category}\n🤖 Generated by AI Video Automation"

        # 1. Try Telegram Free Unlimited Storage (with 3-attempt socket retry & 300s timeout)
        if self.bot_token and self.chat_id:
            link = self.upload_to_telegram(file_path, caption)
            if link:
                return link

        # 2. Try Tmpfiles fast zero-login cloud storage
        tmp_link = self.upload_to_tmpfiles_fallback(file_path)
        if tmp_link:
            return tmp_link

        # 3. Try Catbox zero-config free cloud storage
        fallback_link = self.upload_to_catbox_fallback(file_path)
        if fallback_link:
            return fallback_link

        # 4. Local storage link if offline
        local_ref = f"file:///{os.path.abspath(file_path)}"
        db.log("INFO", "Storage", f"Stored locally: {local_ref}")
        return local_ref

storage_uploader = StorageUploader()

