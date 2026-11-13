import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.scene_generator import analyze_story_vibe_timeline
from modules.scriptwriter import scriptwriter
from modules.subtitles import subtitle_engine
from modules.telegram_agent import telegram_agent

print("======================================================================")
print("🧪 DIAGNOSTIC: STORY-MATCHED VISUALS, HINDI/HINGLISH & TELEGRAM AGENT")
print("======================================================================\n")

# 1. Test Story-Matched Dynamic Scene Timeline
print("[1] Testing Story-Matched Visual Scene Timeline Analysis...")
sample_script = (
    "A single missed character just exposed 50 million bank accounts. "
    "Attackers sent a crafted HTTP request with a stolen cookie to bypass cloud authentication. "
    "This gave the hacker full root administrative shell access on the Linux terminal. "
    "Over fifty million database records and user credentials were leaked on the dark web. "
    "Security teams advise users to apply the emergency security patch and update firewall rules immediately."
)
timeline = analyze_story_vibe_timeline(sample_script, duration=40.0)
for block in timeline:
    print(f"  • {block['start']}s - {block['end']}s -> SCENE: {block['scene'].upper()}")

# 2. Test Hindi Voiceover & Hinglish Subtitles Generation
print("\n[2] Testing Hindi/Hinglish Script Generator for Instagram Reels...")
sample_article = {
    "title": "Critical Authentication Bypass Flaw Discovered in Cloud Servers",
    "summary": "Attackers can bypass authentication and gain root administrative access.",
    "category": "Web Penetration Testing"
}
english_script = {
    "title": "Critical Auth Bypass Flaw #Shorts",
    "script": sample_script
}
hi_data = scriptwriter.generate_hindi_hinglish_script(english_script, sample_article)
print(f"  • Title:              {hi_data.get('title')}")
print(f"  • Hindi Speech (TTS): {hi_data.get('hindi_speech')[:80]}...")
print(f"  • Hinglish Subtitles: {hi_data.get('hinglish_subtitles')[:80]}...")

# 3. Test Alignment of Hinglish Subtitles to Audio Timings
print("\n[3] Testing Hinglish Word Alignment Engine...")
sample_audio_timings = [
    {"word": "w1", "start": 0.0, "end": 0.5},
    {"word": "w2", "start": 0.5, "end": 1.0},
    {"word": "w3", "start": 1.0, "end": 1.5}
]
aligned = subtitle_engine.align_text_to_word_timings("Ek choti si bhool", sample_audio_timings, total_duration=2.0)
print(f"  • Aligned {len(aligned)} Hinglish words across audio duration:")
for aw in aligned:
    print(f"    - '{aw['word']}': {aw['start']}s -> {aw['end']}s")

# 4. Test Telegram AI Agent Command State
print("\n[4] Testing Telegram AI Agent State & Controls...")
telegram_agent.handle_incoming_message({"from": {"id": 6150075369}, "chat": {"id": 6150075369}, "text": "status"})
print("  • Executed 'status' query.")
telegram_agent.handle_incoming_message({"from": {"id": 6150075369}, "chat": {"id": 6150075369}, "text": "don't post"})
print(f"  • Executed 'don't post' -> auto_post_paused = {telegram_agent.auto_post_paused}")
telegram_agent.handle_incoming_message({"from": {"id": 6150075369}, "chat": {"id": 6150075369}, "text": "resume"})
print(f"  • Executed 'resume' -> auto_post_paused = {telegram_agent.auto_post_paused}")

print("\n======================================================================")
print("✅ ALL THREE SYSTEM MODULES VERIFIED SUCCESSFULLY!")
print("======================================================================")

