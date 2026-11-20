import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Directories
STORAGE_DIR = BASE_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"
AUDIO_DIR = STORAGE_DIR / "audio"
SUBTITLES_DIR = STORAGE_DIR / "subtitles"
CACHE_DIR = STORAGE_DIR / "cache"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
AUDIO_SFX_DIR = ASSETS_DIR / "audio"
TEMPLATES_DIR = ASSETS_DIR / "templates"
LOGS_DIR = BASE_DIR / "logs"

# Ensure all critical runtime directories exist
for directory in [VIDEOS_DIR, AUDIO_DIR, SUBTITLES_DIR, CACHE_DIR, FONTS_DIR, AUDIO_SFX_DIR, TEMPLATES_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = STORAGE_DIR / "pipeline.db"

# AI Script Generation (Supports key rotation: KEY1,KEY2,KEY3)
raw_gemini_keys = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS = [k.strip() for k in raw_gemini_keys.split(",") if k.strip()]
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

# FreeLLMAPI Gateway (https://github.com/tashfeenahmed/freellmapi - 87 Free Providers & 10.1B Tokens/mo)
FREELLMAPI_ENABLED = os.getenv("FREELLMAPI_ENABLED", "false").lower() in ("true", "1", "yes")
FREELLMAPI_BASE_URL = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3001/v1").rstrip("/")
FREELLMAPI_API_KEY = os.getenv("FREELLMAPI_API_KEY", "").strip()
FREELLMAPI_MODEL = os.getenv("FREELLMAPI_MODEL", "auto").strip()

# Scheduling & Differentiated Posting Times
# YouTube Shorts: Global tech audience in UTC Peak Timings (15:00 UTC = 10:00 AM EST, 20:00 UTC = 3:00 PM EST)
# Instagram Reels & Facebook: Indian & South Asian audience in IST Peak Timings (13:00 IST & 20:00 IST)
SCHEDULE_MODE = os.getenv("SCHEDULE_MODE", "best_times").lower()
BEST_POST_TIMES_RAW = os.getenv("BEST_POST_TIMES", "13:00,20:00")
BEST_POST_TIMES = [t.strip() for t in BEST_POST_TIMES_RAW.split(",") if t.strip()]
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
MAX_VIDEOS_PER_DAY = int(os.getenv("MAX_VIDEOS_PER_DAY", "2"))

# YouTube Timing (UTC Best Times or Direct Immediate)
YOUTUBE_POST_TIMES_UTC_RAW = os.getenv("YOUTUBE_POST_TIMES_UTC", "15:00,20:00")
YOUTUBE_POST_TIMES_UTC = [t.strip() for t in YOUTUBE_POST_TIMES_UTC_RAW.split(",") if t.strip()]
YOUTUBE_SCHEDULE_MODE = os.getenv("YOUTUBE_SCHEDULE_MODE", "immediate").lower()  # "immediate" (direct public) or "scheduled" (UTC peak slots)

# Instagram & Facebook Timing (IST Best Times or Direct Immediate)
INSTAGRAM_FB_POST_TIMES_IST_RAW = os.getenv("INSTAGRAM_FB_POST_TIMES_IST", "13:00,20:00")
INSTAGRAM_FB_POST_TIMES_IST = [t.strip() for t in INSTAGRAM_FB_POST_TIMES_IST_RAW.split(",") if t.strip()]
INSTAGRAM_FB_SCHEDULE_MODE = os.getenv("INSTAGRAM_FB_SCHEDULE_MODE", "immediate").lower()  # "immediate" (direct live) or "scheduled" (IST peak slots)

# Voice & Typography Dynamic Rotation (Rotates voices, fonts & neon accents daily & per video)
ROTATE_STYLES = os.getenv("ROTATE_STYLES", "true").lower() in ("true", "1", "yes")
VOICE_NAME = os.getenv("VOICE_NAME", "en-US-ChristopherNeural")
VOICE_RATE = os.getenv("VOICE_RATE", "+15%")
VOICE_PITCH = os.getenv("VOICE_PITCH", "+0Hz")

# Content Topics
TARGET_TOPICS_RAW = os.getenv("TARGET_TOPICS", "Cybersecurity,Web Penetration Testing,Zero-Day Exploits,Bug Bounty,Tech News")
TARGET_TOPICS = [t.strip() for t in TARGET_TOPICS_RAW.split(",") if t.strip()]
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "180"))
AUTO_GENERATE_COUNT = int(os.getenv("AUTO_GENERATE_COUNT", "1"))

# Free Cloud Storage (Telegram Bot)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Channel Branding & Identity
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "The Spy").strip()

# YouTube Studio
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "28")  # Science & Technology
YOUTUBE_AUTO_UPLOAD = os.getenv("YOUTUBE_AUTO_UPLOAD", "true").lower() in ("true", "1", "yes")

# Instagram Reels
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "").strip()
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "").strip()
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "").strip()
INSTAGRAM_AUTO_POST = os.getenv("INSTAGRAM_AUTO_POST", "false").lower() in ("true", "1", "yes")

# Facebook Page Reels / Videos (Meta Graph API)
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
FACEBOOK_AUTO_POST = os.getenv("FACEBOOK_AUTO_POST", "false").lower() in ("true", "1", "yes")

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "google_sheets_creds.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "AI Video Automation Logs")
GOOGLE_SHEET_WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()

# Discord Webhook Notification Alerts
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# VPS Server & Dashboard Port (Auto-detects Pterodactyl SERVER_PORT or cloud PORT)
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("SERVER_PORT") or os.getenv("PORT") or os.getenv("DASHBOARD_PORT", "8000"))
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "cyber-ai-video-secret-key")
CONCURRENT_WORKERS = int(os.getenv("CONCURRENT_WORKERS", "2"))

