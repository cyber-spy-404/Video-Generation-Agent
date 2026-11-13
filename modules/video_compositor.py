import os
import subprocess
import random
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from config import VIDEOS_DIR, ASSETS_DIR, FONTS_DIR, AUDIO_SFX_DIR, CACHE_DIR
from modules.database import db

class VideoCompositor:
    def __init__(self):
        self.output_dir = VIDEOS_DIR
        self.cache_dir = CACHE_DIR
        self.ffmpeg_bin = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        """Locates ffmpeg executable in PATH or standard VPS/Windows locations."""
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        # Windows Winget, local bundled, npm ffmpeg-static & Linux VPS paths
        import glob
        winget_candidates = glob.glob(
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
        )
        candidates = [
            str(BASE_DIR / "node_modules" / "ffmpeg-static" / "ffmpeg"),
            str(BASE_DIR / "ffmpeg"),
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\ffmpeg.exe")
        ] + winget_candidates
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return "ffmpeg"

    def _find_ffprobe(self) -> str:
        """Locates ffprobe executable."""
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            return ffprobe
        import glob
        winget_candidates = glob.glob(
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffprobe.exe")
        )
        candidates = winget_candidates + [
            "/usr/bin/ffprobe",
            "/usr/local/bin/ffprobe",
            r"C:\ffmpeg\bin\ffprobe.exe",
            os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\ffprobe.exe")
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return "ffprobe"

    def create_headline_card(
        self,
        title: str,
        category: str,
        job_id: int,
        font_path: Optional[Any] = None,
        border_color: tuple = (0, 229, 255, 180)
    ) -> str:
        """Creates an attractive modern tech card overlay (1080x400 PNG) with themed font & accents."""
        card_path = self.cache_dir / f"headline_{job_id}.png"
        img = Image.new("RGBA", (1080, 420), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Load bold font
        font_headline = None
        font_badge = None

        candidate_fonts = []
        if font_path and os.path.exists(str(font_path)):
            candidate_fonts.append(font_path)
        candidate_fonts.extend([
            FONTS_DIR / "Anton.ttf",
            FONTS_DIR / "Impact.ttf",
            FONTS_DIR / "ArialBlack.ttf",
            FONTS_DIR / "BebasNeue.ttf",
            FONTS_DIR / "ArchivoBlack.ttf",
            FONTS_DIR / "SansBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ])

        for font_candidate in candidate_fonts:
            if os.path.exists(str(font_candidate)):
                try:
                    font_headline = ImageFont.truetype(str(font_candidate), 52)
                    break
                except Exception:
                    pass

        try:
            font_badge = ImageFont.truetype(str(FONTS_DIR / "SansBold.ttf"), 26)
        except Exception:
            font_badge = font_headline

        # Card container (Glassmorphic dark slate with themed neon border)
        card_box = [60, 40, 1020, 380]
        draw.rounded_rectangle(card_box, radius=24, fill=(10, 15, 29, 235), outline=border_color, width=3)

        # Badge: Category / Alert
        badge_box = [90, 65, 450, 115]
        is_ai = "ai" in category.lower() or "frontier" in category.lower()
        badge_fill = (168, 85, 247, 240) if is_ai else (239, 68, 68, 240)
        badge_icon = "🤖" if is_ai else "🔴"
        draw.rounded_rectangle(badge_box, radius=12, fill=badge_fill)
        draw.text((105, 75), f"{badge_icon} {category.upper()}", fill=(255, 255, 255, 255), font=font_badge)

        # Channel Branding Tag matching reference reel (>_ TECHNICAL WARNING)
        accent_rgb = border_color[:3] if len(border_color) >= 3 else (168, 85, 247)
        draw.rounded_rectangle([470, 65, 840, 115], radius=12, fill=(20, 28, 48, 240), outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 180), width=1)
        draw.text((485, 75), ">_ TECHNICAL WARNING", fill=accent_rgb, font=font_badge)

        # Two-Tone Headline text wrapping
        words = title.split()
        lines = []
        cur_line = []
        for w in words:
            if len(" ".join(cur_line + [w])) <= 28:
                cur_line.append(w)
            else:
                lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        y = 145
        for line_idx, line in enumerate(lines[:3]):
            line_words = line.split()
            if line_idx == 0 and len(line_words) >= 2:
                # Two-tone: word 1 white, word 2 accent neon color
                x = 95
                for w_i, lw in enumerate(line_words):
                    col = accent_rgb if w_i == 1 else (255, 255, 255)
                    draw.text((x, y), lw + " ", fill=col, font=font_headline)
                    bbox = draw.textbbox((x, y), lw + " ", font=font_headline)
                    x = bbox[2]
            else:
                draw.text((95, y), line, fill=(255, 255, 255, 255), font=font_headline)
            y += 68

        img.save(card_path, "PNG")
        return str(card_path)

    def generate_cyber_background_loop(
        self,
        duration: float,
        job_id: int,
        script_text: str = None,
        word_timings: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generates dynamic multi-scene 9:16 background cutting between 7 high-tech scenes
        with visual cuts dynamically synchronized to the storytelling vibe.
        """
        from modules.scene_generator import generate_multi_scene_video
        bg_video = self.cache_dir / f"cyber_bg_{job_id}.mp4"
        generate_multi_scene_video(
            duration=duration,
            output_path=str(bg_video),
            ffmpeg_bin=self.ffmpeg_bin,
            script_text=script_text,
            word_timings=word_timings
        )
        return str(bg_video)

    def get_audio_duration(self, audio_path: str) -> float:
        """Extracts exact duration in seconds from audio file using ffprobe."""
        ffprobe_bin = self._find_ffprobe()
        cmd = [
            ffprobe_bin, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            # Fallback estimation based on file size if ffprobe is absent
            size = os.path.getsize(audio_path)
            return max(15.0, size / 16000.0)

    def compose_video(
        self,
        job_id: int,
        title: str,
        category: str,
        audio_path: str,
        subtitles_path: str,
        font_path: Optional[Any] = None,
        border_color: tuple = (0, 229, 255, 180),
        script_text: str = None,
        word_timings: List[Dict[str, Any]] = None,
        output_filename: str = None
    ) -> str:
        """
        Renders the complete 9:16 high-retention video:
        1. Procedural cyber background with story-matched scene cuts
        2. Animated headline badge card with themed font & accent
        3. Burned word-by-word viral subtitles with themed font & kinetic pop
        4. High-quality audio track
        """
        if not shutil.which("ffmpeg") and not os.path.exists(self.ffmpeg_bin):
            err_msg = (
                "FFmpeg is not installed or not in system PATH. "
                "On Ubuntu/Debian VPS, run: 'sudo apt install ffmpeg'. "
                "On Windows, download from https://www.gyan.dev/ffmpeg/builds/ and add bin to PATH."
            )
            db.log("ERROR", "VideoCompositor", err_msg)
            raise FileNotFoundError(err_msg)

        db.log("INFO", "VideoCompositor", f"Composing video for job #{job_id}")
        duration = self.get_audio_duration(audio_path) + 0.8  # Slight trailing breathing room
        out_name = output_filename or f"short_{job_id}.mp4"
        output_file = self.output_dir / out_name

        # 1. Background video with story-matched visual vibe
        bg_video = self.generate_cyber_background_loop(
            duration,
            job_id,
            script_text=script_text,
            word_timings=word_timings
        )

        # 2. Headline card with matching theme font & border
        headline_png = self.create_headline_card(title, category, job_id, font_path=font_path, border_color=border_color)

        # 3. Escape subtitle and font paths for FFmpeg filter syntax
        escaped_sub_path = subtitles_path.replace("\\", "/").replace(":", "\\:")
        escaped_headline = headline_png.replace("\\", "/").replace(":", "\\:")
        escaped_fonts_dir = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")

        # Complex filter:
        # - Overlays headline card at top (y=120) during initial 4.5s hook, then reveals full cyber visuals
        # - Burns ASS word-highlighted subtitles with bundled font directory
        filter_complex = (
            f"[0:v][1:v]overlay=0:120:enable='between(t,0,4.5)'[with_card];"
            f"[with_card]subtitles='{escaped_sub_path}':fontsdir='{escaped_fonts_dir}'[outv]"
        )

        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", bg_video,
            "-loop", "1", "-i", headline_png,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_file)
        ]

        db.log("INFO", "VideoCompositor", f"Rendering with FFmpeg: {output_file.name}")
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode != 0:
            db.log("ERROR", "VideoCompositor", f"FFmpeg failed: {process.stderr[-500:]}")
            raise RuntimeError(f"Video composition failed: {process.stderr[-400:]}")

        db.log("INFO", "VideoCompositor", f"Video render successful: {output_file.name}")
        return str(output_file)

video_compositor = VideoCompositor()
