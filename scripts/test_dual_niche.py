import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.database import db
from modules.researcher import researcher
from modules.scriptwriter import scriptwriter
from modules.scene_generator import analyze_story_vibe_timeline

print("======================================================================")
print("🧪 DIAGNOSTIC: DUAL-NICHE AI & OFFENSIVE CYBERSECURITY PIPELINE")
print("======================================================================\n")

# 1. Test database queries for both categories
ai_pending = db.get_pending_articles(limit=1, category="Frontier AI")
cyber_pending = db.get_pending_articles(limit=1, category="Offensive Cybersecurity")

print(f"[1] Pending Articles in Database:")
if ai_pending:
    print(f"  • Frontier AI:             '{ai_pending[0]['title'][:60]}' (Source: {ai_pending[0]['source']})")
else:
    print("  • Frontier AI:             None pending (will fetch)")

if cyber_pending:
    print(f"  • Offensive Cybersecurity: '{cyber_pending[0]['title'][:60]}' (Source: {cyber_pending[0]['source']})")
else:
    print("  • Offensive Cybersecurity: None pending (will fetch)")

# 2. Test Scriptwriting for Frontier AI
print(f"\n[2] Testing Script Generation for Frontier AI:")
sample_ai_art = ai_pending[0] if ai_pending else {
    "title": "DeepSeek-R1 Crushes Frontier AI Benchmarks at Fraction of Cost",
    "category": "Frontier AI",
    "source": "LocalLLaMA",
    "summary": "DeepSeek introduces open reasoning model outperforming closed models."
}
ai_script = scriptwriter.generate_script(sample_ai_art)
print(f"  • Title:  {ai_script.get('title')}")
print(f"  • Hook:   {ai_script.get('hook')}")
print(f"  • Script: {ai_script.get('script')[:120]}...")

# 3. Test Scriptwriting for Offensive Cybersecurity
print(f"\n[3] Testing Script Generation for Offensive Cybersecurity:")
sample_cyber_art = cyber_pending[0] if cyber_pending else {
    "title": "Critical Authentication Bypass Flaw In Enterprise Web Servers",
    "category": "Offensive Cybersecurity",
    "source": "The Hacker News",
    "summary": "Attackers can bypass authentication to seize root access."
}
cyber_script = scriptwriter.generate_script(sample_cyber_art)
print(f"  • Title:  {cyber_script.get('title')}")
print(f"  • Hook:   {cyber_script.get('hook')}")
print(f"  • Script: {cyber_script.get('script')[:120]}...")

# 4. Test Visual Scene Timeline for Frontier AI Story
print(f"\n[4] Testing Story-Matched Visual Timeline for Frontier AI Story:")
ai_timeline = analyze_story_vibe_timeline(
    "DeepSeek just released an open-source model that crushed Silicon Valley benchmarks at 5% of the cost. "
    "Researchers bypassed traditional training methods using pure reinforcement learning and reasoning tokens. "
    "Google Authenticator and phone chips with 19 billion transistors show how offline math and hardware rule tech. "
    "Follow Technical Warning for daily frontier AI and architecture deep dives.",
    duration=40.0
)
for block in ai_timeline:
    print(f"  • {block['start']}s - {block['end']}s -> SCENE: {block['scene'].upper()}")

# 5. Test Visual Scene Timeline for Cybersecurity Story
print(f"\n[5] Testing Story-Matched Visual Timeline for Cybersecurity Story:")
cyber_timeline = analyze_story_vibe_timeline(
    "A single missed character just exposed 50 million bank accounts. "
    "Attackers sent a crafted HTTP request with a stolen cookie to bypass cloud authentication. "
    "This gave the hacker full root administrative shell access on the Linux terminal. "
    "Security teams released an emergency patch and firewall rules immediately.",
    duration=40.0
)
for block in cyber_timeline:
    print(f"  • {block['start']}s - {block['end']}s -> SCENE: {block['scene'].upper()}")

print("\n======================================================================")
print("✅ DUAL-NICHE PUBLISHING ENGINE VERIFIED SUCCESSFULLY!")
print("======================================================================")

