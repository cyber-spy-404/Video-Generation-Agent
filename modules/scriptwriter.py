import re
import json
import requests
from typing import Dict, Any, Tuple, List
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

GEMINI_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]

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

    def generate_with_gemini_key(self, article: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Calls Gemini API using a specific key with automatic model fallback."""
        cat = article.get("category", "Cybersecurity")
        is_ai = "ai" in cat.lower() or "frontier" in cat.lower()
        active_prompt = VIRAL_PROMPT_AI if is_ai else VIRAL_PROMPT_CYBER

        user_content = f"""News Title: {article['title']}
Source: {article.get('source', 'Security Feed')}
Category: {cat}
Details: {article.get('summary', '')}

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

    def generate_procedural_fallback(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """High-retention fallback scriptwriter when no API key is available or all keys exhausted."""
        title = article["title"].strip()
        category = article.get("category", "Cybersecurity")

        if article.get("source") == "Custom Owner Prompt" or "prompt" in article.get("url", ""):
            hook = f"Here is the shocking truth about {title[:55]} that everyone is talking about."
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
                "key_used": "Built-in Procedural Tech Generator (Zero Quota)"
            }

        if "ai" in category.lower() or "frontier" in category.lower():
            hook = f"A massive breakthrough in artificial intelligence just shook the entire tech industry."
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
                "key_used": "Built-in Procedural Tech Generator (Zero Quota)"
            }

        # Extract core subject
        subject = re.sub(r"(?i)\b(vulnerability|critical|exploit|in|flaw|alert|patch|update)\b", "", title).strip()
        subject = re.sub(r"\s+", " ", subject)[:50]

        hook = f"Security researchers just uncovered a critical exploit exposing millions of systems."
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
            "key_used": "Built-in Procedural Tech Generator (Zero Quota)"
        }

    def generate_with_freellmapi(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls FreeLLMAPI's OpenAI-compatible /v1/chat/completions endpoint.
        FreeLLMAPI automatically aggregates and rotates across 87 free providers (Groq, Cerebras, Google, Mistral, NVIDIA, DeepSeek).
        """
        import config
        url = f"{config.FREELLMAPI_BASE_URL}/chat/completions"
        cat = article.get("category", "Cybersecurity")
        is_ai = "ai" in cat.lower() or "frontier" in cat.lower()
        active_prompt = VIRAL_PROMPT_AI if is_ai else VIRAL_PROMPT_CYBER

        user_content = f"""News Title: {article['title']}
Source: {article.get('source', 'Tech Intelligence')}
Category: {cat}
Details: {article.get('summary', '')}

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

    def generate_script(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts script generation with:
        1. FreeLLMAPI Unified Gateway (if enabled and configured)
        2. Automatic key rotation across all configured Gemini API keys
        3. Procedural high-retention tech engine (guarantees zero-failure uptime)
        """
        db.log("INFO", "ScriptWriter", f"Generating script for: {article['title']}")

        # 1. FreeLLMAPI Unified Gateway
        import config
        if config.FREELLMAPI_ENABLED and (config.FREELLMAPI_API_KEY or "localhost" in config.FREELLMAPI_BASE_URL or "127.0.0.1" in config.FREELLMAPI_BASE_URL):
            try:
                db.log("INFO", "ScriptWriter", f"Attempting generation via FreeLLMAPI Gateway ({config.FREELLMAPI_BASE_URL})...")
                result = self.generate_with_freellmapi(article)
                db.log("INFO", "ScriptWriter", "Script successfully generated via FreeLLMAPI!")
                return result
            except Exception as fe:
                db.log("WARNING", "ScriptWriter", f"FreeLLMAPI gateway failed: {fe}. Falling back to configured API keys...")

        # 2. Configured Gemini API Keys with failover
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
                    db.log("INFO", "ScriptWriter", "Hindi/Hinglish script generated with FreeLLMAPI Unified Gateway.")
                    return res
            except Exception as fe:
                db.log("WARNING", "ScriptWriter", f"FreeLLMAPI Hindi generation failed: {fe}. Falling back to configured keys...")

        if self.keys:
            attempts = 0
            max_attempts = len(self.keys)

            while attempts < max_attempts:
                current_key = self.get_active_key()
                try:
                    result = self.generate_with_gemini_key(article, current_key)
                    db.log("INFO", "ScriptWriter", f"Script generated successfully using Key #{self.current_idx + 1}.")
                    return result
                except Exception as e:
                    err_msg = str(e)
                    db.log("WARNING", "ScriptWriter", f"Key #{self.current_idx + 1} failed: {err_msg[:120]}")
                    self.rotate_to_next_key(reason=err_msg[:60])
                    attempts += 1

            db.log("WARNING", "ScriptWriter", "All configured Gemini keys were exhausted. Switching to procedural engine.")

        # 3. Fallback procedural generation (never fails)
        result = self.generate_procedural_fallback(article)
        db.log("INFO", "ScriptWriter", "Script generated via procedural engine.")
        return result

    def generate_hindi_hinglish_script(self, english_script: Dict[str, Any], article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapts the English script into:
        1. 'hindi_speech': Authentic spoken Hindi (Devanagari) for Edge-TTS neural voiceover.
        2. 'hinglish_subtitles': 100% matched Roman/Latin script (Hinglish) for kinetic captions on Instagram.
        Guaranteed zero-failure failover.
        """
        db.log("INFO", "ScriptWriter", "Generating Hindi Voiceover & Hinglish Subtitles for Instagram Reels...")
        
        prompt = f"""You are a viral Hindi/Hinglish Instagram Reels creator specializing in Cybersecurity and Ethical Hacking.
Convert this English tech short script into:
1. 'hindi_speech': Natural, conversational spoken Hindi written in Devanagari for text-to-speech voiceover. Keep tech words in common parlance (hackers, server, login bypass, root access, exploit, firewall, patch).
2. 'hinglish_subtitles': The EXACT SAME spoken Hindi sentences, but written in Roman/Latin script (Hinglish) word-for-word so users can easily read on screen.
Example:
hindi_speech: "एक छोटी सी भूल ने पचास मिलियन बैंक खातों को लीक कर दिया।"
hinglish_subtitles: "Ek choti si bhool ne 50 million bank accounts ko leak kar diya."

English Script:
{english_script.get('script', '')}

Title: {english_script.get('title', '')}

Output pure JSON only:
{{
  "title": "Viral 50-char Hinglish title with #Reels #Shorts",
  "hook": "First 10 words in Hinglish",
  "hindi_speech": "Spoken text in Devanagari Hindi",
  "hinglish_subtitles": "Matching spoken text in Latin Hinglish",
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
                    db.log("INFO", "ScriptWriter", "Hindi/Hinglish script generated with FreeLLMAPI Unified Gateway.")
                    return res
            except Exception as fe:
                db.log("WARNING", "ScriptWriter", f"FreeLLMAPI Hindi generation failed: {fe}. Falling back to configured keys...")

        if self.keys:
            attempts = 0
            while attempts < len(self.keys):
                api_key = self.get_active_key()
                success = False
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
                            db.log("INFO", "ScriptWriter", f"Hindi/Hinglish script generated with Key #{self.current_idx + 1} ({model})")
                            return res
                    except Exception:
                        pass
                self.rotate_to_next_key(reason="Models exhausted on key")
                attempts += 1

        # Fallback procedural generator for Hindi & Hinglish
        title = article.get("title", "Critical Vulnerability")

        if article.get("source") == "Custom Owner Prompt" or "prompt" in article.get("url", ""):
            hindi_speech = (
                f"आज हम बात कर रहे हैं {title[:45]} के बारे में, जो इस वक्त काफी चर्चा में है। "
                f"साइबर एक्सपर्ट्स और एथिकल हैकर्स ने इसके खतरनाक इनफिल्ट्रेशन और अटैक वेक्टर्स का खुलासा किया है। "
                f"अटैकर्स नए लूपहोल्स का फायदा उठाकर डेटा और प्राइवेसी को बड़ा नुकसान पहुंचा सकते हैं। "
                f"साइबर खतरों से सुरक्षित रहने के लिए The Spy को फॉलो करें और अपने सिस्टम्स को हमेशा अपडेट रखें।"
            )
            hinglish_subtitles = (
                f"Aaj hum baat kar rahe hain {title[:45]} ke baare mein, jo is waqt kafi charcha mein hai. "
                f"Cyber experts aur ethical hackers ne iske dangerous infiltration attack vectors ka khulasa kiya hai. "
                f"Attackers naye loopholes ka fayda uthakar data aur privacy ko bada nuksan pahuncha sakte hain. "
                f"Cyber threats se safe rehne ke liye The Spy ko follow karein aur apne systems ko update rakhein."
            )
            return {
                "title": f"🚨 {title[:40]} Breakdown! #Shorts #Reels",
                "hook": f"Aaj hum baat kar rahe hain {title[:30]} ke baare mein",
                "hindi_speech": hindi_speech,
                "hinglish_subtitles": hinglish_subtitles,
                "caption": f"Full security breakdown on {title}. Stay protected against zero-day exploits! #CyberSecurity #Hacking #Shorts #Tech #Reels"
            }

        clean_title = re.sub(r"(?i)\b(vulnerability|critical|exploit|in|flaw|alert)\b", "", title).strip()[:40]

        if "ai" in article.get("category", "").lower() or "frontier" in article.get("category", "").lower():
            hindi_speech = (
                f"आर्टिफिशियल इंटेलिजेंस की दुनिया में एक ऐसा बड़ा धमाका हुआ है जिसने सिलिकॉन वैली को हिला कर रख दिया है। "
                f"हम बात कर रहे हैं {clean_title} के बारे में। रिसर्चर्स ने ऐसा आर्किटेक्चर तैयार किया है जो पुराने सभी मॉडल्स को पीछे छोड़ रहा है। "
                f"कम लागत और ज्यादा एक्यूरेसी के साथ यह टेक्नोलॉजी एआई के भविष्य को पूरी तरह से बदल रही है। "
                f"डेली एआई अपडेट्स और टेक ब्रेकडाउन के लिए The Spy को जरूर फॉलो करें।"
            )
            hinglish_subtitles = (
                f"Artificial intelligence ki duniya mein ek aisa bada dhamaka hua hai jisne Silicon Valley ko hila kar rakh diya hai. "
                f"Hum baat kar rahe hain {clean_title} ke baare mein. Researchers ne aisa architecture launch kiya hai jo puraane sabhi models ko peeche chhod raha hai. "
                f"Kam cost aur high accuracy ke sath yeh technology AI ke future ko badal rahi hai. "
                f"Daily AI updates aur tech breakdowns ke liye The Spy ko zaroor follow karein."
            )
            return {
                "title": f"🚨 {clean_title} AI Shock! #Shorts #Reels",
                "hook": "Artificial intelligence ki duniya mein ek aisa bada dhamaka hua hai",
                "hindi_speech": hindi_speech,
                "hinglish_subtitles": hinglish_subtitles,
                "caption": f"Breaking frontier AI analysis on {clean_title}. Follow The Spy for daily AI and tech insights! #AI #DeepSeek #ChatGPT #Shorts #Tech #Reels"
            }

        hindi_speech = (
            f"सिक्योरिटी रिसर्चर्स ने एक ऐसा खतरनाक जीरो डे एक्सप्लॉइट खोजा है जिसने लाखों सर्वर्स को खतरे में डाल दिया है। "
            f"हमलावर सिर्फ एक क्राफ्टेड रिक्वेस्ट भेजकर बिना किसी पासवर्ड के पूरे सर्वर का रूट एडमिन कंट्रोल हासिल कर रहे हैं। "
            f"यह बग सीधे तौर पर बड़े प्रोडक्शन सर्वर्स को टारगेट कर रहा है। "
            f"अगर आप यह सिस्टम चलाते हैं, तो तुरंत ऑफिशियल सिक्योरिटी पैच और फायरवॉल रूल्स अपडेट करें, इससे पहले कि आपका डेटा पूरी तरह से कंप्रोमाइज हो जाए।"
        )
        hinglish_subtitles = (
            f"Security researchers ne ek aisa khatarnak zero-day exploit khoja hai jisne millions servers ko khatre mein daal diya hai. "
            f"Attackers sirf ek crafted request bhejkar bina kisi password ke pure server ka root admin control le rahe hain. "
            f"Yeh dangerous loophole seedhe production servers ko target kar raha hai. "
            f"Agar aap yeh systems run karte hain, toh turant official security patch aur firewall rules apply karein, isse pehle ki aapka data compromise ho jaye."
        )

        return {
            "title": f"🚨 {clean_title} Alert! #Shorts #Reels",
            "hook": "Security researchers ne ek aisa khatarnak exploit khoja hai",
            "hindi_speech": hindi_speech,
            "hinglish_subtitles": hinglish_subtitles,
            "caption": f"Breaking security alert on {clean_title}. Stay safe and update your systems! #CyberSecurity #Hacking #Shorts #Tech #Reels"
        }

scriptwriter = ScriptWriter()
