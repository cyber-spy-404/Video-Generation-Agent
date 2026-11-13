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
        Synthesizes text into high-quality studio speech.
        Supports dynamic per-job voice selection for multi-speaker daily variety.
        Returns: (audio_file_path, word_timings)
        """
        chosen_voice = voice or self.voice
        chosen_rate = rate or self.rate
        chosen_pitch = pitch or self.pitch

        db.log("INFO", "VoiceEngine", f"Synthesizing voiceover for job #{job_id} using {chosen_voice} ({chosen_rate})")
        output_file = AUDIO_DIR / f"speech_{job_id}.mp3"

        try:
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
                        self._synthesize_async(text, output_file, chosen_voice, chosen_rate, chosen_pitch)
                    ).result()
            else:
                word_timings = loop.run_until_complete(
                    self._synthesize_async(text, output_file, chosen_voice, chosen_rate, chosen_pitch)
                )

            db.log("INFO", "VoiceEngine", f"Speech generated successfully: {output_file.name} ({len(word_timings)} words timed)")
            return str(output_file), word_timings

        except Exception as e:
            db.log("ERROR", "VoiceEngine", f"Voice generation failed: {str(e)}")
            raise

voice_engine = VoiceEngine()
