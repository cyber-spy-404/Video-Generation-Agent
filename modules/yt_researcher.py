import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import CACHE_DIR
from modules.database import db

class MediaExtractor:
    """
    Video & Audio Intelligence Extractor powered by yt-dlp, FFmpeg, and Whisper.
    Can inspect, scrape, and transcribe reference videos or trending tech shorts.
    """
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extracts complete metadata from a video URL using yt-dlp."""
        try:
            import yt_dlp
            ydl_opts = {
                "skip_download": True,
                "quiet": True,
                "no_warnings": True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title") or info.get("description", "")[:60],
                    "uploader": info.get("uploader", ""),
                    "duration": info.get("duration", 0),
                    "description": info.get("description", ""),
                    "tags": info.get("tags", []),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0)
                }
        except Exception as e:
            db.log("WARNING", "MediaExtractor", f"yt-dlp info extraction failed for {url}: {e}")
            return None

    def download_audio_track(self, url: str, output_name: str = "ref_audio.mp3") -> Optional[str]:
        """Downloads audio track of a video using yt-dlp and FFmpeg."""
        out_path = self.cache_dir / output_name
        try:
            import yt_dlp
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(self.cache_dir / "%(id)s.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True,
                "no_warnings": True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = self.cache_dir / f"{info['id']}.mp3"
                if downloaded_file.exists():
                    shutil.move(str(downloaded_file), str(out_path))
                    return str(out_path)
        except Exception as e:
            db.log("WARNING", "MediaExtractor", f"yt-dlp audio download failed: {e}")
        return None

    def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribes audio using faster-whisper or openai-whisper if available,
        returning full transcript and word-level timestamps.
        """
        # 1. Try faster-whisper
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, word_timestamps=True)
            word_timings = []
            full_text = []
            for segment in segments:
                full_text.append(segment.text)
                for word in segment.words:
                    word_timings.append({
                        "word": word.word.strip(),
                        "start": round(word.start, 3),
                        "end": round(word.end, 3)
                    })
            return {
                "text": " ".join(full_text).strip(),
                "language": info.language,
                "word_timings": word_timings
            }
        except Exception:
            pass

        # 2. Try openai-whisper
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, word_timestamps=True)
            word_timings = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    word_timings.append({
                        "word": w.get("word", "").strip(),
                        "start": round(w.get("start", 0), 3),
                        "end": round(w.get("end", 0), 3)
                    })
            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "en"),
                "word_timings": word_timings
            }
        except Exception:
            pass

        return None

media_extractor = MediaExtractor()

