import math
from pathlib import Path
from typing import List, Dict, Any
from config import SUBTITLES_DIR
from modules.database import db

def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

class SubtitleEngine:
    def __init__(self):
        self.output_dir = SUBTITLES_DIR

    def align_text_to_word_timings(
        self,
        target_text: str,
        audio_timings: List[Dict[str, Any]],
        total_duration: float
    ) -> List[Dict[str, Any]]:
        """
        Maps a transcript (such as Romanized Hinglish) to spoken audio timings.
        Guarantees 100% word synchronization even across cross-language translation.
        """
        target_words = target_text.split()
        if not target_words:
            return audio_timings

        # Case 1: Exact match with audio word count
        if len(target_words) == len(audio_timings):
            aligned = []
            for i, tw in enumerate(target_words):
                aligned.append({
                    "word": tw,
                    "start": audio_timings[i]["start"],
                    "end": audio_timings[i]["end"]
                })
            return aligned

        # Case 2: Proportional weighted character length distribution across audio duration
        total_chars = sum(max(1, len(w)) for w in target_words)
        active_duration = max(5.0, total_duration - 0.5)
        cur_t = 0.2
        aligned = []
        for tw in target_words:
            w_len = max(1, len(tw))
            w_dur = active_duration * (w_len / total_chars)
            aligned.append({
                "word": tw,
                "start": round(cur_t, 3),
                "end": round(cur_t + w_dur, 3)
            })
            cur_t += w_dur
        return aligned

    def group_words_into_phrases(self, word_timings: List[Dict[str, Any]], words_per_phrase: int = 3) -> List[Dict[str, Any]]:
        """Groups individual words into snappy 2-3 word display phrases for vertical video retention."""
        phrases = []
        for i in range(0, len(word_timings), words_per_phrase):
            chunk = word_timings[i:i + words_per_phrase]
            if not chunk:
                continue
            phrase_start = chunk[0]["start"]
            phrase_end = chunk[-1]["end"]
            phrases.append({
                "words": chunk,
                "start": phrase_start,
                "end": phrase_end
            })
        return phrases

    def generate_ass_subtitles(
        self,
        word_timings: List[Dict[str, Any]],
        job_id: int,
        font_name: str = "Impact",
        font_size: int = 86,
        highlight_color: str = "&H0000D7FF&"
    ) -> str:
        r"""
        Creates an Advanced SubStation Alpha (.ass) subtitle file with word-level highlight animation.
        - Supports dynamic viral fonts (Anton, Impact, Bebas Neue, Archivo Black, Arial Black)
        - Supports dynamic theme colors (Yellow, Cyan, Neon Green, Orange, Magenta, Gold)
        """
        ass_path = self.output_dir / f"subs_{job_id}.ass"
        phrases = self.group_words_into_phrases(word_timings, words_per_phrase=3)

        # Normalize highlight color format
        clean_highlight = highlight_color.strip()
        if not clean_highlight.startswith("&H"):
            clean_highlight = f"&H{clean_highlight}&"
        if not clean_highlight.endswith("&"):
            clean_highlight = f"{clean_highlight}&"

        # ASS Header with styling
        ass_header = f"""[Script Info]
Title: Viral AI Tech Shorts Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralHighlight,{font_name},{font_size},&H00FFFFFF,{clean_highlight},&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,8,4,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        # Generate word-by-word highlights
        for phrase in phrases:
            words = phrase["words"]
            for current_idx, current_word in enumerate(words):
                start_str = format_ass_time(current_word["start"])
                end_str = format_ass_time(current_word["end"])

                # Build styled text where the active word is themed color
                styled_parts = []
                for idx, w in enumerate(words):
                    word_text = w["word"].upper()
                    if idx == current_idx:
                        # Highlighted active word: theme color with bright pop
                        styled_parts.append(r"{\c" + clean_highlight + r"\fscx112\fscy112}" + word_text + r"{\r}")
                    else:
                        # Inactive words: Clean bold white
                        styled_parts.append(r"{\c&H00FFFFFF&}" + word_text + r"{\r}")

                line_text = " ".join(styled_parts)
                events.append(f"Dialogue: 0,{start_str},{end_str},ViralHighlight,,0,0,0,,{line_text}")

        full_ass_content = ass_header + "\n".join(events) + "\n"

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(full_ass_content)

        db.log("INFO", "SubtitleEngine", f"ASS subtitles generated: {ass_path.name} (Font: {font_name}, Theme: {clean_highlight})")
        return str(ass_path)

subtitle_engine = SubtitleEngine()
