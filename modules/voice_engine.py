import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from config import AUDIO_DIR, VOICE_NAME, VOICE_RATE, VOICE_PITCH
from modules.database import db

class VoiceEngine:
    def __init__(self, voice: str = VOICE_NAME, rate: str = VOICE_RATE, pitch: str = VOICE_PITCH):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def _synthesize_async(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        import edge_tts
        v = voice or self.voice
        r = rate or self.rate
        p = pitch or self.pitch
        communicate = edge_tts.Communicate(text, v, rate=r, pitch=p)
        raw_word_boundaries = []
        sentence_boundaries = []

        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                chunk_type = chunk.get("type")
                if chunk_type == "audio":
                    f.write(chunk["data"])
                elif chunk_type == "WordBoundary":
                    offset_sec = chunk["offset"] / 10_000_000.0
                    duration_sec = chunk["duration"] / 10_000_000.0
                    raw_word_boundaries.append({
                        "word": chunk["text"],
                        "start": offset_sec,
                        "end": offset_sec + duration_sec
                    })
                elif chunk_type == "SentenceBoundary":
                    offset_sec = chunk["offset"] / 10_000_000.0
                    duration_sec = chunk["duration"] / 10_000_000.0
                    sentence_boundaries.append({
                        "sentence": chunk["text"],
                        "start": offset_sec,
                        "end": offset_sec + duration_sec
                    })

        # If edge-tts provided exact WordBoundary events, use them
        if raw_word_boundaries:
            return raw_word_boundaries

        # Otherwise, synthesize word timings accurately from SentenceBoundaries using weighted character distribution
        computed_word_timings = []
        for sb in sentence_boundaries:
            words = sb["sentence"].split()
            if not words:
                continue

            total_chars = sum(max(1, len(w)) for w in words)
            sent_start = sb["start"]
            sent_duration = max(0.2, sb["end"] - sb["start"])

            current_time = sent_start
            for w in words:
                w_len = max(1, len(w))
                w_duration = sent_duration * (w_len / total_chars)
                computed_word_timings.append({
                    "word": w,
                    "start": round(current_time, 3),
                    "end": round(current_time + w_duration, 3)
                })
                current_time += w_duration

        return computed_word_timings

    def generate_speech(
        self,
        text: str,
        job_id: int,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Synthesizes text into high-quality studio speech with automatic voice failover.
        Supports dynamic per-job voice selection for multi-speaker daily variety.
        Returns: (audio_file_path, word_timings)
        """
        import re
        import time

        chosen_voice = voice or self.voice
        chosen_rate = rate or self.rate
        chosen_pitch = pitch or self.pitch

        # Clean text of markdown formatting and normalize whitespace
        clean_text = re.sub(r"[\*\_#`]", "", text or "").strip()
        clean_text = re.sub(r"\s+", " ", clean_text)
        if not clean_text or len(clean_text) < 3:
            clean_text = "Breaking cybersecurity intelligence and technology update."

        # Candidate voices with automated fallback ladder
        voice_candidates = [
            (chosen_voice, chosen_rate, chosen_pitch),
        ]
        if "hi-IN" in chosen_voice:
            alt_hi = "hi-IN-SwaraNeural" if "Madhur" in chosen_voice else "hi-IN-MadhurNeural"
            voice_candidates.append((alt_hi, "+0%", chosen_pitch))
            voice_candidates.append((chosen_voice, "+0%", chosen_pitch))
            voice_candidates.append(("en-US-ChristopherNeural", "+15%", "+0Hz"))
        else:
            if chosen_voice != self.voice:
                voice_candidates.append((self.voice, self.rate, self.pitch))
            voice_candidates.append(("en-US-ChristopherNeural", "+0%", "+0Hz"))
            voice_candidates.append(("en-US-GuyNeural", "+0%", "+0Hz"))

        output_file = AUDIO_DIR / f"speech_{job_id}.mp3"
        last_exception = None

        for v_curr, r_curr, p_curr in voice_candidates:
            try:
                db.log("INFO", "VoiceEngine", f"Synthesizing voiceover for job #{job_id} using {v_curr} ({r_curr})")
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        word_timings = pool.submit(
                            asyncio.run,
                            self._synthesize_async(clean_text, output_file, v_curr, r_curr, p_curr)
                        ).result()
                else:
                    word_timings = loop.run_until_complete(
                        self._synthesize_async(clean_text, output_file, v_curr, r_curr, p_curr)
                    )

                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    db.log("INFO", "VoiceEngine", f"Speech generated successfully: {output_file.name} ({len(word_timings)} words timed)")
                    return str(output_file), word_timings
                else:
                    raise RuntimeError("Generated audio file is empty or below threshold size.")

            except Exception as e:
                last_exception = e
                db.log("WARNING", "VoiceEngine", f"Synthesis with {v_curr} failed ({e}). Attempting next candidate in fallback ladder...")
                time.sleep(1.0)

        db.log("ERROR", "VoiceEngine", f"All voice candidates exhausted for job #{job_id}: {last_exception}")
        raise last_exception

voice_engine = VoiceEngine()
