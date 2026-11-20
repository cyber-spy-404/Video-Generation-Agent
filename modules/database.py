import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH

class Database:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT,
                published_at TEXT,
                discovered_at TEXT NOT NULL,
                status TEXT DEFAULT 'discovered'
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_url TEXT,
                title TEXT NOT NULL,
                hook TEXT,
                script TEXT,
                audio_path TEXT,
                subtitles_path TEXT,
                video_path TEXT,
                storage_url TEXT,
                youtube_id TEXT,
                youtube_url TEXT,
                instagram_id TEXT,
                instagram_url TEXT,
                facebook_id TEXT,
                facebook_url TEXT,
                sheet_synced INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued',
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (article_url) REFERENCES articles(url)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL
            )
            """)

            # Auto-migrate any new columns
            for col in ["facebook_id", "facebook_url"]:
                try:
                    cursor.execute(f"ALTER TABLE videos ADD COLUMN {col} TEXT;")
                except Exception:
                    pass

            conn.commit()

    def log(self, level: str, module: str, message: str):
        now = datetime.utcnow().isoformat()
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO system_logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)",
                    (now, level.upper(), module, str(message))
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to write log: {e}")

    # Articles
    def article_exists(self, url: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def insert_article(self, article: Dict[str, Any]) -> bool:
        if self.article_exists(article["url"]):
            return False
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO articles (url, title, source, category, summary, published_at, discovered_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article["url"],
                    article["title"],
                    article["source"],
                    article.get("category", "Cybersecurity"),
                    article.get("summary", ""),
                    article.get("published_at", now),
                    now,
                    "discovered"
                )
            )
            conn.commit()
            return True

    def get_pending_articles(self, limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM articles WHERE status = 'discovered' AND category LIKE ? ORDER BY discovered_at DESC LIMIT ?",
                    (f"%{category}%", limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM articles WHERE status = 'discovered' ORDER BY discovered_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_article(self, url: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM articles WHERE url = ?", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_article_status(self, url: str, status: str):
        with self.get_connection() as conn:
            conn.execute("UPDATE articles SET status = ? WHERE url = ?", (status, url))
            conn.commit()

    def get_completed_categories_today(self, date_prefix: Optional[str] = None) -> List[str]:
        """Returns list of categories for videos completed today to enforce 1 AI + 1 Cybersecurity split."""
        if not date_prefix:
            date_prefix = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.category FROM videos v
                LEFT JOIN articles a ON v.article_url = a.url
                WHERE v.status = 'completed' AND (v.created_at LIKE ? OR v.updated_at LIKE ?)
                """,
                (f"{date_prefix}%", f"{date_prefix}%")
            )
            return [row[0] for row in cursor.fetchall() if row[0]]

    # Videos
    def create_video_job(self, title: str, article_url: Optional[str] = None) -> int:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO videos (article_url, title, status, created_at, updated_at)
                VALUES (?, ?, 'queued', ?, ?)
                """,
                (article_url, title, now, now)
            )
            conn.commit()
            return cursor.lastrowid

    def update_video(self, video_id: int, **kwargs):
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        set_clauses = [f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values())
        values.append(video_id)

        sql = f"UPDATE videos SET {', '.join(set_clauses)} WHERE id = ?"
        with self.get_connection() as conn:
            conn.execute(sql, values)
            conn.commit()

    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_video(self, video_id: int) -> bool:
        """Deletes a video job record from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_videos(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_unsynced_videos(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE sheet_synced = 0 AND status = 'uploaded'")
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_logs(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_completed_videos_count_today(self, date_prefix: Optional[str] = None) -> int:
        """Counts how many completed videos were created/published on a given date (default: today)."""
        if not date_prefix:
            date_prefix = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM videos WHERE status = 'completed' AND (created_at LIKE ? OR updated_at LIKE ?)",
                (f"{date_prefix}%", f"{date_prefix}%")
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_stats(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM videos")
            total_videos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM videos WHERE status = 'uploaded'")
            total_published = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM videos WHERE status = 'queued' OR status = 'rendering'")
            active_jobs = cursor.fetchone()[0]

            return {
                "total_articles": total_articles,
                "total_videos": total_videos,
                "total_published": total_published,
                "active_jobs": active_jobs
            }

db = Database.get_instance()

