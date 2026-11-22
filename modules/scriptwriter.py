from __future__ import annotations
import re
import json
import requests
from typing import Dict, Any, Tuple, List, Optional
from config import GEMINI_API_KEYS
from modules.database import db

VIRAL_PROMPT_CYBER = """You are a viral YouTube Shorts and Instagram Reels scriptwriter specializing in Cybersecurity, Web Penetration Testing, and Tech Exploits.
Write an ultra-high-retention 35-to-45 second spoken video script based on the provided news item.

MANDATORY RULES:
1. CUT THE INTRO: Never say "Hey guys", "In this video", or "Today we look at". Start directly with the punchline and crazy hook.
2. 0-2 SECOND HOOK: Shock the viewer immediately with high stakes (e.g., "A single missed character just exposed 50 million bank accounts...").
3. THE MECHANISM (EXPLOIT): Explain clearly in plain, gripping English how the bug or breach happened (SQL injection, cookie hijacking, memory overflow, API auth bypass). No boring academic jargon.
4. ACTIONABLE IMPACT: Tell developers, tech fans, or everyday users what it means and how it was patched.
5. COMPLETE CONCLUSION: Deliver an authoritative, actionable closing advice line so the thought is 100% complete.
6. WORD COUNT: 85 to 110 words total (aiming for roughly 35-42 seconds at 150 words per minute).
7. CLEAN OUTPUT: No stage directions, no [music], no (sound effect), no asterisks. ONLY the spoken words.

Output format must be valid JSON:
{
  "title": "Shocking 50-char viral title with #Shorts",
  "hook": "First 10 words of the script",
  "script": "The complete spoken script text without any bracketed notes",
  "tags": ["cybersecurity", "ethicalhacking", "pentesting", "infosec", "tech"],
  "description": "2-sentence compelling YouTube/Instagram description with #Shorts #CyberSecurity"
}
"""

VIRAL_PROMPT_AI = """You are a viral YouTube Shorts and Instagram Reels scriptwriter specializing in Frontier AI, LLM Breakthroughs (DeepSeek, OpenAI, Claude, Llama, Gemini), AI Hardware (NVIDIA Blackwell, microchips), and Tech Architecture.
Write an ultra-high-retention 35-to-45 second spoken video script based on the provided news item.

MANDATORY RULES:
1. CUT THE INTRO: Never say "Hey guys", "In this video", or "Today we look at". Start directly with a shocking curiosity hook (e.g. "DeepSeek just released a model that crushed Silicon Valley at 5% of the cost...", or "Your phone chip is literally made of sand, yet contains 19 billion switches...").
2. THE SECRET / HOW IT WORKS: Explain clearly how the breakthrough, architecture, or hardware works (Mixture of Experts, reasoning tokens, 3nm EUV lithography, TOTP clock math). No boring academic filler.
3. WHY IT MATTERS: Tell viewers what this changes for developers, tech fans, and the future of AI.
4. COMPLETE CONCLUSION: Authoritative takeaway line so the story feels 100% finished.
5. WORD COUNT: 85 to 110 words total (aiming for roughly 35-42 seconds).
6. CLEAN OUTPUT: No stage directions, no [music], no (sound effect), no asterisks. ONLY the spoken words.

Output format must be valid JSON:
{
  "title": "Shocking 50-char viral title with #Shorts",
  "hook": "First 10 words of the script",
  "script": "The complete spoken script text without any bracketed notes",
  "tags": ["artificialintelligence", "ai", "deepseek", "chatgpt", "tech", "shorts"],
  "description": "2-sentence compelling YouTube/Instagram description with #Shorts #AI #Tech"
}
"""

# -----------------------------------------------------------------------------
# 10-HOOK VIRAL ROTATION LOOP (Cycles 1 to 10 perpetually per video)
# -----------------------------------------------------------------------------
VIRAL_HOOK_ARCHETYPES_CYBER = [
    {
        "id": 1,
        "name": "The Hidden Loophole",
        "pattern_en": "Hackers just uncovered a hidden loophole that developers pray you never discover.",
        "pattern_hi": "हैकर्स ने एक ऐसा खतरनाक लूपहोल खोज निकाला है जिसे सब छिपाना चाहते थे।",
        "pattern_hinglish": "Hackers ne ek aisa hidden loophole dhoondh nikala hai jise sab chupana chahte the."
    },
    {
        "id": 2,
        "name": "The High-Stakes Exposure",
        "pattern_en": "A single missed character in this code just exposed millions of private accounts.",
        "pattern_hi": "कोड में एक छोटी सी गलती ने लाखों पर्सनल अकाउंट्स को सीधे ओपन इंटरनेट पर लीक कर दिया।",
        "pattern_hinglish": "Code mein ek choti si galti ne lakho accounts ko open internet par leak kar diya."
    },
    {
        "id": 3,
        "name": "The Immediate Danger Warning",
        "pattern_en": "If your system or phone is running this software, you are in immediate danger.",
        "pattern_hi": "अगर आपका सर्वर या फोन इस वर्जन पर चल रहा है, तो आप तुरंत गंभीर खतरे में हैं।",
        "pattern_hinglish": "Agar aapka server ya phone is software par chal raha hai, toh aap turant khatre mein hain."
    },
    {
        "id": 4,
        "name": "Zero-Password Bypass",
        "pattern_en": "Attackers can now completely bypass authentication without typing a single password.",
        "pattern_hi": "हमलावर बिना कोई पासवर्ड डाले सीधे सर्वर का एडमिन कंट्रोल हासिल कर रहे हैं।",
        "pattern_hinglish": "Attackers bina kisi password ke direct server ka root admin control le rahe hain."
    },
    {
        "id": 5,
        "name": "The Memory Ghost Steal",
        "pattern_en": "Your encrypted data was stolen without touching your hard drive or triggering any alerts.",
        "pattern_hi": "बिना हार्ड ड्राइव को छुए और बिना कोई अलर्ट ट्रिगर किए, सारा सीक्रेट डेटा चोरी हो गया।",
        "pattern_hinglish": "Bina hard drive ko chhue aur bina alert trigger kiye, encrypted data seedhe memory se chori ho gaya."
    },
    {
        "id": 6,
        "name": "The Built-In Backdoor",
        "pattern_en": "The most trusted security layer in the world had a fatal backdoor hidden inside.",
        "pattern_hi": "दुनिया के सबसे भरोसेमंद सिस्टम में एक ऐसा सीक्रेट बैकडोर निकला जिसने सबको हैरान कर दिया।",
        "pattern_hinglish": "Duniya ke sabse trusted security system mein ek aisa fatal backdoor nikla jisne sabko shock kar diya."
    },
    {
        "id": 7,
        "name": "Zero-Click Infiltration",
        "pattern_en": "No clicking links, no opening files—just receiving a single packet crashed the server.",
        "pattern_hi": "ना कोई लिंक क्लिक किया, ना कोई फाइल खोली—सिर्फ एक पैकेट से पूरा सिस्टम क्रैश हो गया।",
        "pattern_hinglish": "Na koi link click kiya, na file open ki—sirf ek malicious packet se pura server hack ho gaya."
    },
    {
        "id": 8,
        "name": "The Underdog Strike",
        "pattern_en": "A lone security researcher just took down an entire global cyber army with one exploit.",
        "pattern_hi": "एक अकेले सिक्योरिटी रिसर्चर ने एक स्क्रिप्ट से पूरे ग्लोबल हैकर नेटवर्क को बेनकाब कर दिया।",
        "pattern_hinglish": "Ek akele security researcher ne ek single script se pure global hacker syndicate ko expose kar diya."
    },
    {
        "id": 9,
        "name": "The Urgent Hold Warning",
        "pattern_en": "Do NOT install this update until you watch this critical zero-day security alert.",
        "pattern_hi": "इस नए सॉफ्टवेयर अपडेट को इनस्टॉल करने से पहले यह खतरनाक सिक्योरिटी सच जरूर जान लें।",
        "pattern_hinglish": "Is naye update ko install karne se pehle yeh critical zero-day threat zaroor jaan lein."
    },
    {
        "id": 10,
        "name": "The Direct Reality Check",
        "pattern_en": "Think your two-factor authentication and passwords are safe? Watch this crazy exploit.",
        "pattern_hi": "अगर आपको लगता है कि आपका टू-फैक्टर ऑथेंटिकेशन सेफ है, तो इस नए अटैक को ध्यान से देखिए।",
        "pattern_hinglish": "Agar aapko lagta hai ki aapka 2FA aur passwords safe hain, toh is crazy exploit ko dhyan se dekhiye."
    }
]

VIRAL_HOOK_ARCHETYPES_AI = [
    {
        "id": 1,
        "name": "The Silicon Valley Secret",
        "pattern_en": "Silicon Valley giants are quietly scrambling after this shocking AI architecture dropped.",
        "pattern_hi": "सिलिकॉन वैली के बड़े टेक जॉइंट्स में हड़कंप मच गया है क्योंकि यह नया एआई आर्किटेक्चर रिलीज हो चुका है।",
        "pattern_hinglish": "Silicon Valley ke top tech giants panic mein hain kyunki yeh game-changing AI architecture drop ho chuka hai."
    },
    {
        "id": 2,
        "name": "The 5% Cost Disruptor",
        "pattern_en": "A brand new open-source AI model just crushed closed frontier benchmarks at 5% of the cost.",
        "pattern_hi": "एक नए ओपन सोर्स एआई मॉडल ने सिर्फ 5% की लागत में दुनिया के सबसे महंगे मॉडल्स को पछाड़ दिया।",
        "pattern_hinglish": "Ek naye open-source AI model ne sirf 5% cost par duniya ke sabse expensive models ko beat kar diya."
    },
    {
        "id": 3,
        "name": "The Obsolescence Warning",
        "pattern_en": "Stop using traditional coding and prompt tools because what released today changes everything.",
        "pattern_hi": "पुराने टूल्स का इस्तेमाल तुरंत बंद कर दीजिए, क्योंकि आज जो एआई टेक्नोलॉजी रिलीज हुई है उसने सब बदल दिया।",
        "pattern_hinglish": "Purane tools use karna band kar dijiye, kyunki aaj jo AI technology launch hui hai usne sab badal diya."
    },
    {
        "id": 4,
        "name": "The Hardware Reality",
        "pattern_en": "Your phone's microchip is made of pure refined sand, yet runs 19 billion switches a second.",
        "pattern_hi": "आपके फोन की छोटी सी चिप साधारण रेत से बनी है, लेकिन एक सेकंड में 19 बिलियन स्विच चलाती है।",
        "pattern_hinglish": "Aapke phone ki choti si chip ordinary sand se bani hai, lekin har second 19 billion switches operate karti hai."
    },
    {
        "id": 5,
        "name": "The Cloud Free Freedom",
        "pattern_en": "You don't need million-dollar cloud servers anymore to run reasoning models this smart.",
        "pattern_hi": "अब आपको इतने ताकतवर रीजनिंग मॉडल चलाने के लिए महंगे क्लाउड सर्वर की कोई जरूरत नहीं है।",
        "pattern_hinglish": "Ab aapko itne powerful reasoning models run karne ke liye expensive cloud servers ki koi zaroorat nahi hai."
    },
    {
        "id": 6,
        "name": "The Architecture Mystery",
        "pattern_en": "Why did every top researcher pause when this tiny 7-billion parameter paper went public?",
        "pattern_hi": "पूरी दुनिया के एआई रिसर्चर्स क्यों हैरान रह गए जब यह नया रिसर्च पेपर इंटरनेट पर लाइव हुआ?",
        "pattern_hinglish": "Puri duniya ke AI researchers kyun shock reh gaye jab yeh revolutionary research paper live hua?"
    },
    {
        "id": 7,
        "name": "The Moat Breaker",
        "pattern_en": "The moat around proprietary AI just evaporated overnight, and here is the exact proof.",
        "pattern_hi": "बड़ी टेक कंपनियों का एकाधिकार रातों-रात खत्म हो गया, और इसका सीधा सबूत यह रहा।",
        "pattern_hinglish": "Big tech companies ka monopoly moat raaton-raat khatam ho gaya, aur yeh raha iska direct proof."
    },
    {
        "id": 8,
        "name": "The Offline Math Magic",
        "pattern_en": "Google Authenticator generates codes without internet or cell service using pure offline clock math.",
        "pattern_hi": "गूगल ऑथेंटिकेटर बिना इंटरनेट या सिम कार्ड के सिर्फ टाइम मैथ का इस्तेमाल करके सिक्योर कोड्स बनाता है।",
        "pattern_hinglish": "Google Authenticator bina internet ya mobile network ke sirf offline clock math se secure codes banata hai."
    },
    {
        "id": 9,
        "name": "The Future of Developers",
        "pattern_en": "The way software is built just transformed forever, and developers need to see this now.",
        "pattern_hi": "सॉफ्टवेयर बनाने का तरीका हमेशा के लिए बदल चुका है, और हर डेवलपर को यह सच अभी देखना चाहिए।",
        "pattern_hinglish": "Software develop karne ka tareeqa hamesha ke liye badal chuka hai, aur har developer ko yeh dekhna chahiye."
    },
    {
        "id": 10,
        "name": "The Unbelievable Speed Benchmark",
        "pattern_en": "This new chip architecture processes AI reasoning tokens ten times faster than existing silicon.",
        "pattern_hi": "यह नया चिप आर्किटेक्चर पुराने सिलिकॉन से दस गुना तेजी से एआई रीजनिंग टोकन्स प्रोसेस करता है।",
        "pattern_hinglish": "Yeh naya chip architecture traditional silicon se 10 guna zyada speed par AI reasoning process karta hai."
    }
]

GEMINI_MODELS = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-3.5-flash", "gemini-pro-latest", "gemini-flash-lite-latest"]

class ScriptWriter:
    def __init__(self):
        self.keys: List[str] = list(GEMINI_API_KEYS)
        self.current_idx: int = 0

    def get_active_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[self.current_idx % len(self.keys)]

    def rotate_to_next_key(self, reason: str = ""):
        if not self.keys:
            return
        old_idx = self.current_idx
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        db.log(
            "WARNING",
            "ScriptWriter",
            f"Rotated from Key #{old_idx + 1} to Key #{self.current_idx + 1}. Reason: {reason}"
        )

    def get_hook_archetype(self, category: str, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Selects a unique hook archetype from a 10-hook rotating loop (Cycles 1 to 10 perpetually).
        Ensures consecutive videos never repeat the same hook pattern or intro structure.
        """
        is_ai = "ai" in category.lower() or "frontier" in category.lower()
        pool = VIRAL_HOOK_ARCHETYPES_AI if is_ai else VIRAL_HOOK_ARCHETYPES_CYBER

        if job_id is not None:
            try:
                j_int = int(job_id)
                if j_int > 0:
                    idx = (j_int - 1) % len(pool)
                    return pool[idx]
            except Exception:
                pass

        try:
            from modules.database import db
            stats = db.get_stats()
            idx = stats.get("total_videos", 0) % len(pool)
        except Exception:
            idx = 0
        return pool[idx]

    def generate_with_gemini_key(
        self,
        article: Dict[str, Any],
        api_key: str,
        hook_archetype: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calls Gemini API using a specific key with automatic model fallback."""
        cat = article.get("category", "Cybersecurity")
        is_ai = "ai" in cat.lower() or "frontier" in cat.lower()
        active_prompt = VIRAL_PROMPT_AI if is_ai else VIRAL_PROMPT_CYBER

        hook_instruction = ""
        if hook_archetype:
            hook_instruction = f"""

MANDATORY 10-HOOK ROTATION REQUIREMENT (Slot #{hook_archetype['id']} of 10):
Hook Archetype: {hook_archetype['name']}
Required Opening Angle/Hook Pattern: "{hook_archetype['pattern_en']}"
You MUST format your 0-2 second opening hook using this exact formula and tone, tailored specifically to this story. Never open with generic greetings."""

        user_content = f"""News Title: {article['title']}
Source: {article.get('source', 'Security Feed')}
Category: {cat}
Details: {article.get('summary', '')}{hook_instruction}

Write the viral short script according to the mandatory rules. Output pure JSON only."""

        payload = {
            "contents": [{
                "parts": [
                    {"text": active_prompt},
                    {"text": user_content}
                ]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }

        last_err = ""
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    raw_text = re.sub(r"```\s*$", "", raw_text.strip(), flags=re.MULTILINE)
                    return json.loads(raw_text)
                last_err = f"{model} returned HTTP {resp.status_code}: {resp.text[:150]}"
            except Exception as e:
                last_err = str(e)
        raise RuntimeError(last_err)

    def generate_procedural_fallback(
        self,
        article: Dict[str, Any],
        hook_archetype: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """High-retention fallback scriptwriter when no API key is available or all keys exhausted."""
        title = article["title"].strip()
        category = article.get("category", "Cybersecurity")

        if article.get("source") == "Custom Owner Prompt" or "prompt" in article.get("url", ""):
            hook = f"{hook_archetype['pattern_en']} Here is the truth about {title[:50]}." if hook_archetype else f"Here is the shocking truth about {title[:55]} that everyone is talking about."
            body = (
                f"Security analysts and ethical hackers have revealed critical insights into {title[:50]}. "
                f"Attackers use advanced infiltration techniques to bypass standard security filters, exploit hidden loopholes, "
                f"and gain unauthorized administrative control before anyone notices. "
                f"Understanding these attack vectors is the first step to defending your systems and personal accounts. "
                f"Follow The Spy to stay protected against the latest cyber threats and security exploits."
            )
            full_script = f"{hook} {body}".strip()
            clean_title = f"{title[:45]} Breakdown! 🚨 #Shorts"
            return {
                "title": clean_title,
                "hook": hook,
                "script": full_script,
                "tags": ["cybersecurity", "tech", "shorts", "hacking", "infosec"],
                "description": f"Full security breakdown on {title}. Subscribe to The Spy for daily cyber threat alerts! #Shorts #CyberSecurity",
                "key_used": f"Built-in Procedural Tech Generator (Hook #{hook_archetype['id'] if hook_archetype else 1})"
            }

        if "ai" in category.lower() or "frontier" in category.lower():
            hook = f"{hook_archetype['pattern_en']}" if hook_archetype else "A massive breakthrough in artificial intelligence just shook the entire tech industry."
            body = (
                f"Here is why everyone is talking about {title[:50]}. Researchers have introduced a game-changing "
                f"architecture that dramatically slashes compute costs while outperforming closed-source models across key reasoning benchmarks. "
                f"From deep reasoning tokens to open-weights accessibility, this release completely changes how developers build AI applications. "
                f"The moat around big tech is evaporating. Subscribe to The Spy for daily frontier AI and tech breakdowns."
            )
            full_script = f"{hook} {body}".strip()
            clean_title = f"{title[:45]} Breakdown! 🤖 #Shorts"
            return {
                "title": clean_title,
                "hook": hook,
                "script": full_script,
                "tags": ["artificialintelligence", "ai", "deepseek", "llm", "shorts", "tech"],
                "description": f"Frontier AI analysis on {title}. Subscribe to The Spy! #Shorts #AI #Technology",
                "key_used": f"Built-in Procedural Tech Generator (Hook #{hook_archetype['id'] if hook_archetype else 1})"
            }

        # Extract core subject
        subject = re.sub(r"(?i)\b(vulnerability|critical|exploit|in|flaw|alert|patch|update)\b", "", title).strip()
        subject = re.sub(r"\s+", " ", subject)[:50]

        hook = f"{hook_archetype['pattern_en']}" if hook_archetype else "Security researchers just uncovered a critical exploit exposing millions of systems."
        body = (
            f"Here is how this crazy flaw works. Attackers discovered that by sending a specially crafted "
            f"request, they can completely bypass authentication and seize full root administrative control without needing any password. "
            f"This dangerous loophole actively targets servers running {subject}. Security teams are scrambling to patch "
            f"the vulnerability before automated botnets weaponize it across the internet. "
            f"If you run these systems, apply the official security patch and update your firewall rules immediately before your data is compromised."
        )
        full_script = f"{hook} {body}".strip()

        clean_title = f"Critical Exploit Discovered! 🚨 #Shorts"
        if len(title) < 55:
            clean_title = f"{title} #Shorts"

        return {
            "title": clean_title,
            "hook": hook,
            "script": full_script,
            "tags": ["cybersecurity", "pentesting", "ethicalhacking", "zero_day", "shorts"],
            "description": f"Breaking security analysis on {title}. Stay protected! #Shorts #CyberSecurity #Hacking",
            "key_used": f"Built-in Procedural Tech Generator (Hook #{hook_archetype['id'] if hook_archetype else 1})"
        }

    def generate_with_freellmapi(
        self,
        article: Dict[str, Any],
        hook_archetype: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calls FreeLLMAPI's OpenAI-compatible /v1/chat/completions endpoint.
        FreeLLMAPI automatically aggregates and rotates across 87 free providers (Groq, Cerebras, Google, Mistral, NVIDIA, DeepSeek).
        """
        import config
        url = f"{config.FREELLMAPI_BASE_URL}/chat/completions"
        cat = article.get("category", "Cybersecurity")
        is_ai = "ai" in cat.lower() or "frontier" in cat.lower()
        active_prompt = VIRAL_PROMPT_AI if is_ai else VIRAL_PROMPT_CYBER

        hook_instruction = ""
        if hook_archetype:
            hook_instruction = f"""

MANDATORY 10-HOOK ROTATION REQUIREMENT (Slot #{hook_archetype['id']} of 10):
Hook Archetype: {hook_archetype['name']}
Required Opening Angle/Hook Pattern: "{hook_archetype['pattern_en']}"
You MUST format your 0-2 second opening hook using this exact formula and tone, tailored specifically to this story."""

        user_content = f"""News Title: {article['title']}
Source: {article.get('source', 'Tech Intelligence')}
Category: {cat}
Details: {article.get('summary', '')}{hook_instruction}

Write the viral short script according to the mandatory rules. Output pure JSON only."""

        headers = {"Content-Type": "application/json"}
        if config.FREELLMAPI_API_KEY:
            headers["Authorization"] = f"Bearer {config.FREELLMAPI_API_KEY}"

        payload = {
            "model": config.FREELLMAPI_MODEL or "auto",
            "messages": [
                {"role": "system", "content": active_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
            raw_text = re.sub(r"```\s*$", "", raw_text.strip(), flags=re.MULTILINE)
            res = json.loads(raw_text)
            res["key_used"] = f"FreeLLMAPI Gateway ({config.FREELLMAPI_MODEL})"
            return res
        else:
            raise RuntimeError(f"FreeLLMAPI HTTP {resp.status_code}: {resp.text[:120]}")

    def generate_script(self, article: Dict[str, Any], job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Attempts script generation with:
        1. 10-Hook Viral Rotation Loop (Cycles 1 to 10 perpetually)
        2. FreeLLMAPI Unified Gateway (if enabled and configured)
        3. Automatic key rotation across all configured Gemini API keys
        4. Procedural high-retention tech engine (guarantees zero-failure uptime)
        """
        cat = article.get("category", "Cybersecurity")
        hook_archetype = self.get_hook_archetype(cat, job_id)
        db.log("INFO", "ScriptWriter", f"Generating script for: '{article['title'][:50]}' (Using Hook #{hook_archetype['id']}: {hook_archetype['name']})")

        # 1. FreeLLMAPI Unified Gateway
        import config
        if config.FREELLMAPI_ENABLED and (config.FREELLMAPI_API_KEY or "localhost" in config.FREELLMAPI_BASE_URL or "127.0.0.1" in config.FREELLMAPI_BASE_URL):
            try:
                db.log("INFO", "ScriptWriter", f"Attempting generation via FreeLLMAPI Gateway ({config.FREELLMAPI_BASE_URL})...")
                result = self.generate_with_freellmapi(article, hook_archetype=hook_archetype)
                db.log("INFO", "ScriptWriter", f"Script successfully generated via FreeLLMAPI (Hook #{hook_archetype['id']})!")
                return result
            except Exception as fe:
                db.log("WARNING", "ScriptWriter", f"FreeLLMAPI gateway failed: {fe}. Falling back to configured API keys...")

        # 2. Configured Gemini API Keys with failover
        if self.keys:
            attempts = 0
            max_attempts = len(self.keys)

            while attempts < max_attempts:
                current_key = self.get_active_key()
                try:
                    result = self.generate_with_gemini_key(article, current_key, hook_archetype=hook_archetype)
                    db.log("INFO", "ScriptWriter", f"Script generated successfully using Key #{self.current_idx + 1} (Hook #{hook_archetype['id']}).")
                    return result
                except Exception as e:
                    err_msg = str(e)
                    db.log("WARNING", "ScriptWriter", f"Key #{self.current_idx + 1} failed: {err_msg[:120]}")
                    self.rotate_to_next_key(reason=err_msg[:60])
                    attempts += 1

            db.log("WARNING", "ScriptWriter", "All configured Gemini keys were exhausted. Switching to procedural engine.")

        # 3. Fallback procedural generation (never fails)
        result = self.generate_procedural_fallback(article, hook_archetype=hook_archetype)
        db.log("INFO", "ScriptWriter", f"Script generated via procedural engine (Hook #{hook_archetype['id']}).")
        return result

    def generate_hindi_hinglish_script(
        self,
        english_script: Dict[str, Any],
        article: Dict[str, Any],
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Adapts the English script into:
        1. 'hindi_speech': Authentic spoken Hindi (Devanagari) for Edge-TTS neural voiceover.
        2. 'hinglish_subtitles': 100% matched Roman/Latin script (Hinglish) for kinetic captions on Instagram.
        Rotates through 10-Hook Viral Loop (Cycles 1 to 10 perpetually) matching the job.
        Guaranteed zero-failure failover.
        """
        cat = article.get("category", "Cybersecurity")
        hook_archetype = self.get_hook_archetype(cat, job_id)
        db.log(
            "INFO",
            "ScriptWriter",
            f"Generating Hindi Voiceover & Hinglish Subtitles for Instagram Reels (Hook #{hook_archetype['id']}: {hook_archetype['name']})..."
        )
        
        prompt = f"""You are a top viral Indian cybersecurity creator (like alex.cyberx) producing high-retention Instagram Reels and YouTube Shorts.
Your signature voice style is punchy, conversational, and speaks directly to the viewer in modern colloquial Hinglish (e.g. "Fake account bana ke...", "Agar tum sochte ho...", "Suno, cyber cell tum tak kaise pahunchti hai:").

Convert this tech short script into authentic spoken Hindi & kinetic Hinglish subtitles:

MANDATORY ROTATING HOOK (MUST be the opening sentence):
Hindi Hook (Opening): "{hook_archetype['pattern_hi']}"
Hinglish Hook (Opening): "{hook_archetype['pattern_hinglish']}"

Rules:
1. 'hindi_speech': Natural, conversational spoken Hindi written in Devanagari for text-to-speech voiceover.
   - Start directly with the Hindi Hook above or natural variation.
   - Use colloquial creator phrasing: "Suno", "Dekho", "Agar aap sochte ho ki...", "Lekin sach yeh hai...".
   - Keep everyday tech terms in English parlance (hackers, server, login, bypass, root access, exploit, firewall, IP address, patch).
   - Fast, engaging flow without boring academic filler.
   - Conclude with actionable safety advice and "Cyber threats se safe rehne ke liye The Spy ko follow karein."
2. 'hinglish_subtitles': The EXACT SAME spoken sentences, but written in Roman/Latin script (Hinglish) word-for-word.
   - Must match the spoken words 100% so subtitles sync cleanly.
   - Start directly with the Hinglish Hook above.
Example:
hindi_speech: "एक छोटी सी भूल ने पचास मिलियन बैंक खातों को लीक कर दिया। हैकर्स ने सीधे डेटाबेस पर अटैक किया।"
hinglish_subtitles: "Ek choti si bhool ne 50 million bank accounts ko leak kar diya. Hackers ne seedhe database par attack kiya."

English Script:
{english_script.get('script', '')}

Title: {english_script.get('title', '')}

Output pure JSON only:
{{
  "title": "Viral 50-char Hinglish title with #Reels #Shorts",
  "hook": "{hook_archetype['pattern_hinglish'][:50]}",
  "hindi_speech": "Spoken text in Devanagari Hindi starting with the hook",
  "hinglish_subtitles": "Matching spoken text in Latin Hinglish starting with the hook",
  "caption": "Compelling Hinglish Instagram caption with #CyberSecurity #Hacking #Shorts #Tech #Reels"
}}"""

        # 1. Attempt with FreeLLMAPI if active
        import config
        if config.FREELLMAPI_ENABLED and (config.FREELLMAPI_API_KEY or "localhost" in config.FREELLMAPI_BASE_URL or "127.0.0.1" in config.FREELLMAPI_BASE_URL):
            try:
                url = f"{config.FREELLMAPI_BASE_URL}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if config.FREELLMAPI_API_KEY:
                    headers["Authorization"] = f"Bearer {config.FREELLMAPI_API_KEY}"
                payload = {
                    "model": config.FREELLMAPI_MODEL or "auto",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=25)
                if resp.status_code == 200:
                    raw_text = resp.json()["choices"][0]["message"]["content"]
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
                    raw_text = re.sub(r"```\s*$", "", raw_text.strip(), flags=re.MULTILINE)
                    res = json.loads(raw_text)
                    db.log("INFO", "ScriptWriter", f"Hindi/Hinglish script generated with FreeLLMAPI Unified Gateway (Hook #{hook_archetype['id']}).")
                    return res
            except Exception as fe:
                db.log("WARNING", "ScriptWriter", f"FreeLLMAPI Hindi generation failed: {fe}. Falling back to configured keys...")

        if self.keys:
            attempts = 0
            while attempts < len(self.keys):
                api_key = self.get_active_key()
                for model in GEMINI_MODELS:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}
                    }
                    try:
                        resp = requests.post(url, json=payload, timeout=25)
                        if resp.status_code == 200:
                            data = resp.json()
                            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
                            raw_text = re.sub(r"```\s*$", "", raw_text.strip(), flags=re.MULTILINE)
                            res = json.loads(raw_text)
                            db.log("INFO", "ScriptWriter", f"Hindi/Hinglish script generated with Key #{self.current_idx + 1} ({model}, Hook #{hook_archetype['id']})")
                            return res
                    except Exception:
                        pass
                self.rotate_to_next_key(reason="Models exhausted on key")
                attempts += 1

        # Fallback procedural generator for Hindi & Hinglish
        title = article.get("title", "Critical Vulnerability")
        hook_hi = hook_archetype["pattern_hi"]
        hook_hinglish = hook_archetype["pattern_hinglish"]

        if article.get("source") == "Custom Owner Prompt" or "prompt" in article.get("url", ""):
            hindi_speech = (
                f"{hook_hi} आज हम बात कर रहे हैं {title[:45]} के बारे में। "
                f"साइबर एक्सपर्ट्स और एथिकल हैकर्स ने इसके खतरनाक इनफिल्ट्रेशन और अटैक वेक्टर्स का खुलासा किया है। "
                f"अटैकर्स नए लूपहोल्स का फायदा उठाकर डेटा और प्राइवेसी को बड़ा नुकसान पहुंचा सकते हैं। "
                f"साइबर खतरों से सुरक्षित रहने के लिए The Spy को फॉलो करें और अपने सिस्टम्स को हमेशा अपडेट रखें।"
            )
            hinglish_subtitles = (
                f"{hook_hinglish} Aaj hum baat kar rahe hain {title[:45]} ke baare mein. "
                f"Cyber experts aur ethical hackers ne iske dangerous infiltration attack vectors ka khulasa kiya hai. "
                f"Attackers naye loopholes ka fayda uthakar data aur privacy ko bada nuksan pahuncha sakte hain. "
                f"Cyber threats se safe rehne ke liye The Spy ko follow karein aur apne systems ko update rakhein."
            )
            return {
                "title": f"🚨 {title[:40]} Breakdown! #Shorts #Reels",
                "hook": hook_hinglish[:50],
                "hindi_speech": hindi_speech,
                "hinglish_subtitles": hinglish_subtitles,
                "caption": f"Full security breakdown on {title}. Stay protected! #CyberSecurity #Hacking #Shorts #Tech #Reels"
            }

        clean_title = re.sub(r"(?i)\b(vulnerability|critical|exploit|in|flaw|alert)\b", "", title).strip()[:40]

        if "ai" in article.get("category", "").lower() or "frontier" in article.get("category", "").lower():
            hindi_speech = (
                f"{hook_hi} हम बात कर रहे हैं {clean_title} के बारे में जिसने सिलिकॉन वैली को हिला कर रख दिया है। "
                f"रिसर्चर्स ने ऐसा आर्किटेक्चर तैयार किया है जो पुराने सभी मॉडल्स को पीछे छोड़ रहा है। "
                f"कम लागत और ज्यादा एक्यूरेसी के साथ यह टेक्नोलॉजी एआई के भविष्य को पूरी तरह से बदल रही है। "
                f"डेली एआई अपडेट्स और टेक ब्रेकडाउन के लिए The Spy को जरूर फॉलो करें।"
            )
            hinglish_subtitles = (
                f"{hook_hinglish} Hum baat kar rahe hain {clean_title} ke baare mein jisne Silicon Valley ko hila kar rakh diya hai. "
                f"Researchers ne aisa architecture launch kiya hai jo puraane sabhi models ko peeche chhod raha hai. "
                f"Kam cost aur high accuracy ke sath yeh technology AI ke future ko badal rahi hai. "
                f"Daily AI updates aur tech breakdowns ke liye The Spy ko zaroor follow karein."
            )
            return {
                "title": f"🚨 {clean_title} AI Shock! #Shorts #Reels",
                "hook": hook_hinglish[:50],
                "hindi_speech": hindi_speech,
                "hinglish_subtitles": hinglish_subtitles,
                "caption": f"Breaking frontier AI analysis on {clean_title}. Follow The Spy for daily AI and tech insights! #AI #DeepSeek #ChatGPT #Shorts #Tech #Reels"
            }

        hindi_speech = (
            f"{hook_hi} हमलावर सिर्फ एक क्राफ्टेड रिक्वेस्ट भेजकर बिना किसी पासवर्ड के पूरे सर्वर का रूट एडमिन कंट्रोल हासिल कर रहे हैं। "
            f"यह खतरनाक बग सीधे तौर पर {clean_title} और बड़े प्रोडक्शन सर्वर्स को टारगेट कर रहा है। "
            f"अगर आप यह सिस्टम चलाते हैं, तो तुरंत ऑफिशियल सिक्योरिटी पैच और फायरवॉल रूल्स अपडेट करें, इससे पहले कि आपका डेटा कंप्रोमाइज हो जाए। "
            f"डेली साइबर थ्रेट्स से सुरक्षित रहने के लिए The Spy को फॉलो करें।"
        )
        hinglish_subtitles = (
            f"{hook_hinglish} Attackers sirf ek crafted request bhejkar bina kisi password ke pure server ka root admin control le rahe hain. "
            f"Yeh dangerous loophole seedhe {clean_title} aur production servers ko target kar raha hai. "
            f"Agar aap yeh systems run karte hain, toh turant official security patch aur firewall rules apply karein, isse pehle ki aapka data compromise ho jaye. "
            f"Daily cyber threats se safe rehne ke liye The Spy ko follow karein."
        )

        return {
            "title": f"🚨 {clean_title} Alert! #Shorts #Reels",
            "hook": hook_hinglish[:50],
            "hindi_speech": hindi_speech,
            "hinglish_subtitles": hinglish_subtitles,
            "caption": f"Breaking security alert on {clean_title}. Stay safe and update your systems! #CyberSecurity #Hacking #Shorts #Tech #Reels"
        }

scriptwriter = ScriptWriter()
