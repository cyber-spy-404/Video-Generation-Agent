import asyncio
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from config import AUDIO_DIR, VOICE_NAME, VOICE_RATE, VOICE_PITCH
from modules.database import db

# Dynamic Sentence-by-Sentence Tonal Modulation Presets
# Modeled after viral Indian creator cadence (e.g. alex.cyberx)
SENTENCE_TONES: Dict[str, Dict[str, Any]] = {
    "hook": {
        "rate": "+24%",
        "pitch": "+5Hz",
        "pause_after_ms": 220,
        "label": "Hook (Curiosity / High Energy)"
    },
    "pivot": {
        "rate": "+12%",
        "pitch": "-4Hz",
        "pause_after_ms": 280,
        "label": "Pivot / Transition (Intense / Focused)"
    },
    "warning": {
        "rate": "+16%",
        "pitch": "-3Hz",
        "pause_after_ms": 220,
        "label": "Warning / Danger (Suspenseful)"
    },
    "outro": {
        "rate": "+22%",
        "pitch": "+3Hz",
        "pause_after_ms": 0,
        "label": "Outro (Resolute Call-to-Action)"
    },
    "explain": {
        "rate": "+20%",
        "pitch": "+0Hz",
        "pause_after_ms": 150,
        "label": "Explanation (Clear / Rapid Flow)"
    }
}

class VoiceEngine:
    def __init__(self, voice: str = VOICE_NAME, rate: str = VOICE_RATE, pitch: str = VOICE_PITCH):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    def _detect_sentence_tone(self, sentence: str, idx: int, total_sentences: int) -> Dict[str, Any]:
        """Classifies each sentence into its emotional beat and prosody parameters."""
        text_lower = sentence.lower().strip()
        
        # 1. First sentence is always the curiosity hook
        if idx == 0:
            return SENTENCE_TONES["hook"]
        
        # 2. Last sentence or CTA is the authoritative outro
        if idx == total_sentences - 1 or any(k in text_lower for k in ["follow", "the spy", "subscribe", "surakshit", "safe rahein", "update rakhein"]):
            return SENTENCE_TONES["outro"]
        
        # 3. Pivot / Dramatic transition words (like alex.cyberx "Suno...", "Lekin...")
        pivot_keywords = [
            "suno", "dekho", "samjho", "lekin", "twist", "wait", "listen",
            "par sach", "sach yeh", "magar", "twist yeh", "reality yeh",
            "सुनो", "देखो", "लेकिन", "मगर", "ट्विस्ट", "सच यह"
        ]
        if any(k in text_lower for k in pivot_keywords):
            return SENTENCE_TONES["pivot"]
            
        # 4. Warning / Danger / Threat cues
        warning_keywords = [
            "khatarnak", "khatre", "danger", "warning", "leak", "hack", "compromise",
            "nuksan", "bada nuksan", "attackers", "malware", "ransomware", "arrest",
            "jail", "police", "fir", "bina password", "bypass", "exploit",
            "खतरनाक", "खतरे", "लीक", "हैक", "नुकसान", "अटैक"
        ]
        if any(k in text_lower for k in warning_keywords):
            return SENTENCE_TONES["warning"]
            
        # 5. Default: Informative explanation flow
        return SENTENCE_TONES["explain"]

    def _get_audio_file_duration(self, file_path: Path) -> float:
        """Measures exact audio duration in seconds via ffprobe."""
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                capture_output=True, text=True, check=True
            )
            return float(probe.stdout.strip())
        except Exception:
            # Fallback estimation if ffprobe fails
            size = os.path.getsize(file_path)
            return max(0.5, size / 6000.0)

    def _stitch_segments_with_pauses(self, segments_with_pauses: List[Tuple[Path, int]], output_path: Path) -> None:
        """Stitches multiple audio segments with millisecond-precise micro-pauses using ffmpeg."""
        inputs = []
        filter_parts = []
        for idx, (seg_file, pause_ms) in enumerate(segments_with_pauses):
            inputs.extend(["-i", str(seg_file)])
            if pause_ms > 0:
                filter_parts.append(f"[{idx}:a]apad=pad_dur={pause_ms / 1000.0}[a{idx}];")
            else:
                filter_parts.append(f"[{idx}:a]anull[a{idx}];")

        concat_inputs = "".join([f"[a{k}]" for k in range(len(segments_with_pauses))])
        filter_complex = "".join(filter_parts) + f"{concat_inputs}concat=n={len(segments_with_pauses)}:v=0:a=1[outa]"

        cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[outa]", "-c:a", "libmp3lame", "-b:a", "192k", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)

    async def _synthesize_tonal_async(
        self,
        clean_text: str,
        output_path: Path,
        voice: str,
        job_id: int
    ) -> List[Dict[str, Any]]:
        """
        Dynamically modulates speech tones sentence-by-sentence.
        Adjusts pitch, rate, and pacing to match emotional cues (Hook, Pivot, Warning, Explain, Outro).
        Computes synchronized word timings for subtitles.
        """
        import edge_tts
        
        # Split on sentence boundaries (standard punctuation or Hindi danda)
        raw_sentences = re.split(r'(?<=[.!?।\n])\s+', clean_text)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 1]
        
        if len(sentences) < 2:
            return await self._synthesize_async(clean_text, output_path, voice, self.rate, self.pitch)

        temp_dir = AUDIO_DIR / f"tones_{job_id}_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        audio_segments: List[Tuple[Path, int]] = []
        combined_words: List[Dict[str, Any]] = []
        current_time_offset = 0.0

        try:
            for i, sent in enumerate(sentences):
                tone = self._detect_sentence_tone(sent, i, len(sentences))
                seg_file = temp_dir / f"seg_{i}.mp3"
                
                comm = edge_tts.Communicate(sent, voice, rate=tone["rate"], pitch=tone["pitch"])
                seg_words = []
                seg_sentences = []
                
                with open(seg_file, "wb") as f:
                    async for chunk in comm.stream():
                        chunk_type = chunk.get("type")
                        if chunk_type == "audio":
                            f.write(chunk["data"])
                        elif chunk_type == "WordBoundary":
                            offset_sec = chunk["offset"] / 10_000_000.0
                            duration_sec = chunk["duration"] / 10_000_000.0
                            seg_words.append({
                                "word": chunk["text"],
                                "start": round(current_time_offset + offset_sec, 3),
                                "end": round(current_time_offset + offset_sec + duration_sec, 3)
                            })
                        elif chunk_type == "SentenceBoundary":
                            offset_sec = chunk["offset"] / 10_000_000.0
                            duration_sec = chunk["duration"] / 10_000_000.0
                            seg_sentences.append({
                                "start": offset_sec,
                                "end": offset_sec + duration_sec,
                                "sentence": chunk["text"]
                            })

                duration = self._get_audio_file_duration(seg_file)

                # Fallback: estimate word timings if WordBoundary was missing
                if not seg_words:
                    words = sent.split()
                    if words:
                        total_chars = sum(max(1, len(w)) for w in words)
                        c_time = current_time_offset
                        for w in words:
                            w_len = max(1, len(w))
                            w_dur = duration * (w_len / total_chars)
                            seg_words.append({
                                "word": w,
                                "start": round(c_time, 3),
                                "end": round(c_time + w_dur, 3)
                            })
                            c_time += w_dur

                combined_words.extend(seg_words)
                audio_segments.append((seg_file, tone["pause_after_ms"]))
                
                pause_sec = tone["pause_after_ms"] / 1000.0
                current_time_offset += duration + pause_sec

            # Stitch all tonal audio segments with precise pauses
            self._stitch_segments_with_pauses(audio_segments, output_path)
            return combined_words

        finally:
            # Clean up temporary segments directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

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

        # 1. Attempt dynamic sentence-by-sentence tonal modulation first
        try:
            raw_sentences = re.split(r'(?<=[.!?।\n])\s+', clean_text)
            sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 1]
            if len(sentences) >= 2:
                db.log("INFO", "VoiceEngine", f"Synthesizing dynamic sentence-by-sentence tonal voiceover for job #{job_id} ({len(sentences)} beats)...")
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
                            self._synthesize_tonal_async(clean_text, output_file, chosen_voice, job_id)
                        ).result()
                else:
                    word_timings = loop.run_until_complete(
                        self._synthesize_tonal_async(clean_text, output_file, chosen_voice, job_id)
                    )

                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    db.log("INFO", "VoiceEngine", f"Tonal speech generated successfully: {output_file.name} ({len(word_timings)} words timed)")
                    return str(output_file), word_timings
        except Exception as tonal_err:
            db.log("WARNING", "VoiceEngine", f"Dynamic tonal synthesis fallback ({tonal_err}). Reverting to standard synthesis...")

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
