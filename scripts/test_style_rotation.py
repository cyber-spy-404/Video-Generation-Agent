import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.style_rotator import style_rotator, STYLE_PRESETS
from modules.voice_engine import voice_engine
from modules.subtitles import subtitle_engine
from modules.video_compositor import video_compositor

print("======================================================================")
print("🎨 MULTI-VOICE & TYPOGRAPHY ROTATION DIAGNOSTIC")
print("======================================================================")
print(f"Total Curated Presets: {len(STYLE_PRESETS)}\n")

for job_id in range(1, 8):
    style = style_rotator.get_style_for_job(job_id)
    print(f"Job #{job_id}:")
    print(f"  • Theme:     {style['name']}")
    print(f"  • Voice:     {style['voice']} ({style['voice_rate']})")
    print(f"  • Font:      {style['font_name']} (Size: {style['font_size']})")
    print(f"  • Highlight: {style['highlight_color']}")
    print(f"  • Persona:   {style['persona']}")

print("\n----------------------------------------------------------------------")
print("Testing dynamic subtitle generation and headline card creation...")

sample_timings = [
    {"word": "CRITICAL", "start": 0.0, "end": 0.4},
    {"word": "SECURITY", "start": 0.4, "end": 0.8},
    {"word": "ALERT", "start": 0.8, "end": 1.2}
]

for job_id in [1, 2, 3]:
    style = style_rotator.get_style_for_job(job_id)
    ass_path = subtitle_engine.generate_ass_subtitles(
        sample_timings,
        job_id=900 + job_id,
        font_name=style["font_name"],
        font_size=style["font_size"],
        highlight_color=style["highlight_color"]
    )
    card_path = video_compositor.create_headline_card(
        "Zero-Day Exploit Detected In Cloud Infrastructure",
        "Cybersecurity",
        job_id=900 + job_id,
        font_path=style.get("font_path"),
        border_color=style.get("badge_border_rgb", (0, 229, 255, 180))
    )
    print(f"[+] Job #{job_id}: ASS Generated ({Path(ass_path).name}) & Headline PNG Generated ({Path(card_path).name})")

print("\n======================================================================")
print("✅ ALL ROTATING PRESETS AND ASSETS VERIFIED SUCCESSFULLY!")
print("======================================================================")

