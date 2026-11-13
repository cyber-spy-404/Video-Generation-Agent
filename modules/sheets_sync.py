import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from config import BASE_DIR, GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_NAME, GOOGLE_SHEET_WEBHOOK_URL
from modules.database import db

# Public Google Sheet Template Link with headers and styling configured
DEFAULT_TEMPLATE_URL = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/copy"

SHEET_COLUMNS = [
    "Timestamp (UTC)",
    "Job ID",
    "Category",
    "Title / Headline",
    "Script Hook",
    "Duration",
    "Word Count",
    "AI Engine / Key",
    "Voice Engine",
    "Free Storage (Telegram)",
    "YouTube Shorts Link",
    "Instagram Link",
    "Facebook Link",
    "Status",
    "Execution Log",
    "Source URL"
]

class SheetsSyncManager:
    def __init__(self):
        self.creds_file = BASE_DIR / GOOGLE_SERVICE_ACCOUNT_FILE
        self.sheet_name = GOOGLE_SHEET_NAME
        self.webhook_url = GOOGLE_SHEET_WEBHOOK_URL
        self.client = None
        self._init_client()

    def _init_client(self):
        """Attempts to initialize gspread client if credentials file exists."""
        if self.creds_file.exists():
            try:
                import gspread
                self.client = gspread.service_account(filename=str(self.creds_file))
                db.log("INFO", "SheetsSync", "Authenticated with Google Sheets via Service Account.")
            except Exception as e:
                db.log("WARNING", "SheetsSync", f"Failed to initialize gspread: {e}")

    def append_row_via_webhook(self, row_data: Dict[str, Any]) -> bool:
        """Appends row via Google Apps Script Webhook (Zero GCP Config)."""
        if not self.webhook_url:
            return False

        try:
            resp = requests.post(self.webhook_url, json=row_data, timeout=15)
            if resp.status_code in (200, 302):
                db.log("INFO", "SheetsSync", "Row successfully synced to Google Sheet via Webhook.")
                return True
            else:
                db.log("WARNING", "SheetsSync", f"Webhook responded HTTP {resp.status_code}")
        except Exception as e:
            db.log("ERROR", "SheetsSync", f"Sheets webhook failed: {e}")
        return False

    def append_row_via_gspread(self, row_values: list) -> bool:
        """Appends row using gspread API."""
        if not self.client:
            return False

        try:
            sheet = self.client.open(self.sheet_name).sheet1
            # Check if headers exist
            existing_records = sheet.get_all_values()
            if not existing_records:
                sheet.append_row(SHEET_COLUMNS)

            sheet.append_row(row_values)
            db.log("INFO", "SheetsSync", f"Row appended to sheet '{self.sheet_name}' via gspread.")
            return True
        except Exception as e:
            db.log("ERROR", "SheetsSync", f"gspread append failed: {e}")
            return False

    def log_video_to_sheet(self, video_data: Dict[str, Any], article_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Logs detailed video production and distribution telemetry to the Google Sheet.
        """
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        category = article_data.get("category", "Cybersecurity") if article_data else "Cybersecurity"
        source_url = article_data.get("url", "") if article_data else ""
        job_id = video_data.get("job_id", video_data.get("id", ""))
        job_str = f"#{job_id}" if job_id else "-"
        duration = video_data.get("duration", "-")
        word_count = video_data.get("word_count", "-")
        key_used = video_data.get("key_used", "AI Model")
        voice = video_data.get("voice", "en-US-ChristopherNeural")
        exec_log = video_data.get("execution_log", video_data.get("status", "completed"))

        row_payload = {
            "timestamp": now,
            "job_id": job_str,
            "category": category,
            "title": video_data.get("title", ""),
            "hook": video_data.get("hook", ""),
            "duration": str(duration),
            "word_count": str(word_count),
            "key_used": str(key_used),
            "voice": str(voice),
            "storage_url": video_data.get("storage_url", ""),
            "youtube_url": video_data.get("youtube_url", ""),
            "instagram_url": video_data.get("instagram_url", ""),
            "facebook_url": video_data.get("facebook_url", ""),
            "status": video_data.get("status", "completed"),
            "execution_log": str(exec_log),
            "source_url": source_url
        }

        # 1. Try Webhook first if configured
        if self.webhook_url:
            if self.append_row_via_webhook(row_payload):
                return True

        # 2. Try gspread service account
        row_list = [
            row_payload["timestamp"],
            row_payload["job_id"],
            row_payload["category"],
            row_payload["title"],
            row_payload["hook"],
            row_payload["duration"],
            row_payload["word_count"],
            row_payload["key_used"],
            row_payload["voice"],
            row_payload["storage_url"],
            row_payload["youtube_url"],
            row_payload["instagram_url"],
            row_payload["facebook_url"],
            row_payload["status"],
            row_payload["execution_log"],
            row_payload["source_url"]
        ]
        if self.append_row_via_gspread(row_list):
            return True

        # 3. If neither is active, log local CSV fallback
        self._append_local_csv(row_list)
        return False

    def _append_local_csv(self, row_values: list):
        """Maintains local offline CSV sync if Google credentials are not yet connected."""
        csv_file = BASE_DIR / "storage" / "google_sheets_backup.csv"
        file_exists = csv_file.exists()
        with open(csv_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write(",".join([f'"{col}"' for col in SHEET_COLUMNS]) + "\n")
            escaped = [f'"{str(val).replace(chr(34), chr(34)+chr(34))}"' for val in row_values]
            f.write(",".join(escaped) + "\n")
        db.log("INFO", "SheetsSync", f"Saved locally to {csv_file.name}. Ready for Google Sheets sync.")

    def get_sheet_link(self) -> str:
        """Returns the configured or default Google Sheet template link."""
        if self.sheet_name.startswith("http"):
            return self.sheet_name
        return DEFAULT_TEMPLATE_URL

sheets_sync = SheetsSyncManager()

