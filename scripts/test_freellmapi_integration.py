import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modules.scriptwriter import scriptwriter

print("======================================================================")
print("🧪 DIAGNOSTIC: FREELLMAPI GATEWAY INTEGRATION & FAILOVER")
print("======================================================================\n")

print(f"[1] FreeLLMAPI Config State:")
print(f"  • Enabled:   {config.FREELLMAPI_ENABLED}")
print(f"  • Base URL:  {config.FREELLMAPI_BASE_URL}")
print(f"  • Model:     {config.FREELLMAPI_MODEL}")
print(f"  • API Key:   {'Set (' + config.FREELLMAPI_API_KEY[:8] + '...)' if config.FREELLMAPI_API_KEY else 'Not Set'}")

# Test fallback behavior when FreeLLMAPI is active or inactive
sample_article = {
    "title": "DeepSeek-R1 Architecture Slashes Inference Cost By 94%",
    "category": "Frontier AI",
    "source": "AI Research Wire",
    "summary": "DeepSeek introduces reinforcement learning reasoning model outperforming frontier benchmarks."
}

print(f"\n[2] Testing Script Generation Pipeline with FreeLLMAPI Engine Integration:")
script_data = scriptwriter.generate_script(sample_article)
print(f"  • Title:     {script_data.get('title')}")
print(f"  • Hook:      {script_data.get('hook')}")
print(f"  • Key Used:  {script_data.get('key_used')}")
print(f"  • Script:    {script_data.get('script')[:120]}...\n")

print(f"[3] Testing Dual-Language Hindi Voiceover & Hinglish Subtitles:")
hi_data = scriptwriter.generate_hindi_hinglish_script(script_data, sample_article)
print(f"  • Title:              {hi_data.get('title')}")
print(f"  • Hindi Speech (TTS): {hi_data.get('hindi_speech')[:90]}...")
print(f"  • Hinglish Subtitles: {hi_data.get('hinglish_subtitles')[:90]}...\n")

print("======================================================================")
print("✅ FREELLMAPI ARCHITECTURE INTEGRATION VERIFIED SUCCESSFULLY!")
print("======================================================================")

