import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from config import FONTS_DIR, VOICE_NAME, VOICE_RATE, VOICE_PITCH

# Curated High-Retention Style Presets for Tech & Cybersecurity Shorts
STYLE_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "cyber_yellow_impact",
        "name": "Electric Yellow & Deep Authoritative",
        "voice": "en-US-ChristopherNeural",
        "voice_rate": "+15%",
        "voice_pitch": "+0Hz",
        "font_name": "Impact",
        "font_file": "Impact.ttf",
        "font_size": 86,
        "highlight_color": "&H0000D7FF&",       # ASS BGR: Yellow (RGB 255, 215, 0)
        "badge_border_rgb": (255, 215, 0, 220), # Yellow/Gold
        "persona": "Lead Security Analyst"
    },
    {
        "id": "neon_cyan_anton",
        "name": "Electric Cyan & Rapid Explainer",
        "voice": "en-US-GuyNeural",
        "voice_rate": "+16%",
        "voice_pitch": "+0Hz",
        "font_name": "Anton",
        "font_file": "Anton.ttf",
        "font_size": 88,
        "highlight_color": "&H00FFFF00&",       # ASS BGR: Cyan (RGB 0, 255, 255)
        "badge_border_rgb": (0, 229, 255, 220), # Electric Cyan
        "persona": "Rapid Tech Explainer"
    },
    {
        "id": "matrix_green_bebas",
        "name": "Matrix Green & Tech Anchor",
        "voice": "en-US-AriaNeural",
        "voice_rate": "+14%",
        "voice_pitch": "+0Hz",
        "font_name": "Bebas Neue",
        "font_file": "BebasNeue.ttf",
        "font_size": 92,
        "highlight_color": "&H0000FF66&",       # ASS BGR: Matrix Green (RGB 102, 255, 0)
        "badge_border_rgb": (0, 255, 102, 220), # Matrix Green
        "persona": "Cyber Operations Anchor"
    },
    {
        "id": "cyber_orange_archivo",
        "name": "Cyber Orange & Threat Hunter",
        "voice": "en-US-EricNeural",
        "voice_rate": "+15%",
        "voice_pitch": "+0Hz",
        "font_name": "Archivo Black",
        "font_file": "ArchivoBlack.ttf",
        "font_size": 80,
        "highlight_color": "&H000078FF&",       # ASS BGR: Orange (RGB 255, 120, 0)
        "badge_border_rgb": (255, 120, 0, 220), # Cyber Orange
        "persona": "Incident Commander"
    },
    {
        "id": "neon_magenta_arialblack",
        "name": "Neon Magenta & Exploit Researcher",
        "voice": "en-US-BrianNeural",
        "voice_rate": "+15%",
        "voice_pitch": "+0Hz",
        "font_name": "Arial Black",
        "font_file": "ArialBlack.ttf",
        "font_size": 80,
        "highlight_color": "&H00FF3399&",       # ASS BGR: Magenta / Violet
        "badge_border_rgb": (220, 50, 255, 220),# Neon Magenta
        "persona": "Exploit Researcher"
    },
    {
        "id": "ice_gold_british_ryan",
        "name": "Amber Gold & British Intelligence",
        "voice": "en-GB-RyanNeural",
        "voice_rate": "+14%",
        "voice_pitch": "+0Hz",
        "font_name": "Anton",
        "font_file": "Anton.ttf",
        "font_size": 88,
        "highlight_color": "&H0000E5FF&",       # ASS BGR: Bright Gold
        "badge_border_rgb": (255, 200, 0, 220), # Gold
        "persona": "Global Intel Wire"
    },
    {
        "id": "aqua_cyan_british_sonia",
        "name": "Electric Aqua & Tech Broadcaster",
        "voice": "en-GB-SoniaNeural",
        "voice_rate": "+14%",
        "voice_pitch": "+0Hz",
        "font_name": "Impact",
        "font_file": "Impact.ttf",
        "font_size": 86,
        "highlight_color": "&H00FFFF33&",       # ASS BGR: Aqua Cyan
        "badge_border_rgb": (50, 240, 255, 220),# Aqua Cyan
        "persona": "Security Broadcaster"
    }
]

class StyleRotator:
    def __init__(self):
        self.presets = STYLE_PRESETS

    def get_style_for_job(self, job_id: int = 1) -> Dict[str, Any]:
        """
        Selects a unique, fresh voice, font, and color theme for each video.
        Ensures variety across days of the week and consecutive videos on the same day.
        """
        rotate_enabled = os.getenv("ROTATE_STYLES", "true").lower() in ("true", "1", "yes")
        
        if not rotate_enabled:
            # Fallback to fixed settings from .env
            font_path = FONTS_DIR / "Impact.ttf"
            return {
                "id": "fixed",
                "name": "Fixed Profile",
                "voice": VOICE_NAME,
                "voice_rate": VOICE_RATE,
                "voice_pitch": VOICE_PITCH,
                "font_name": "Impact",
                "font_file": font_path,
                "font_size": 86,
                "highlight_color": "&H0000D7FF&",
                "badge_border_rgb": (0, 229, 255, 220),
                "persona": "Default Host",
                "style_summary": f"Voice: {VOICE_NAME} | Font: Impact"
            }

        day_of_year = datetime.utcnow().timetuple().tm_yday
        # Rotate based on day of year and job ID so every day starts fresh and intra-day videos vary
        idx = (day_of_year * 3 + int(job_id)) % len(self.presets)
        preset = dict(self.presets[idx])

        font_filename = preset["font_file"]
        font_path = FONTS_DIR / font_filename
        if not font_path.exists():
            # Fallback to Impact or any existing font
            for alt in [FONTS_DIR / "Impact.ttf", FONTS_DIR / "ArialBlack.ttf"]:
                if alt.exists():
                    font_path = alt
                    break

        preset["font_path"] = font_path
        preset["style_summary"] = (
            f"Voice: {preset['voice']} ({preset['voice_rate']}) | "
            f"Font: {preset['font_name']} | Theme: {preset['name']}"
        )
        return preset

style_rotator = StyleRotator()

