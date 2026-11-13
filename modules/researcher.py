import re
import html
import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime
from modules.database import db

# -----------------------------------------------------------------------------
# 1. CURATED INTELLIGENCE FEEDS
# -----------------------------------------------------------------------------

# Curated AI Feeds (4 Categories: US/EU Labs, China Labs, Tech CEOs, Top AI Builders)
AI_FEEDS = [
    {
        "name": "NVIDIA AI Blog",
        "url": "https://blogs.nvidia.com/feed/",
        "category": "Frontier AI",
        "subcategory": "AI Hardware & GPUs (Jensen Huang / Blackwell)"
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "Frontier AI",
        "subcategory": "US & Europe AI Companies (OpenAI, Anthropic, Meta)"
    },
    {
        "name": "Simon Willison AI",
        "url": "https://simonwillison.net/atom/everything/",
        "category": "Frontier AI",
        "subcategory": "AI Researchers & Builders (Simon Willison / Tools)"
    },
    {
        "name": "Lilian Weng Research",
        "url": "https://lilianweng.github.io/index.xml",
        "category": "Frontier AI",
        "subcategory": "AI Researchers (Lilian Weng / Deep Dives)"
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "category": "Frontier AI",
        "subcategory": "Frontier AI Breakthroughs"
    },
    {
        "name": "Ars Technica Tech Lab",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "category": "Frontier AI",
        "subcategory": "AI & Tech Architecture"
    },
    {
        "name": "Reddit r/LocalLLaMA",
        "url": "https://www.reddit.com/r/LocalLLaMA/hot/.rss",
        "category": "Frontier AI",
        "subcategory": "Open Source & China AI (DeepSeek, Qwen, Llama)"
    }
]

# Curated Offensive Cybersecurity & Exploit Feeds
CYBER_FEEDS = [
    {
        "name": "The Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "category": "Offensive Cybersecurity",
        "subcategory": "Zero-Day Exploits & Vulnerabilities"
    },
    {
        "name": "BleepingComputer",
        "url": "https://www.bleepingcomputer.com/feed/",
        "category": "Offensive Cybersecurity",
        "subcategory": "Malware, Ransomware & Botnets"
    },
    {
        "name": "PortSwigger Web Security",
        "url": "https://portswigger.net/research/rss",
        "category": "Offensive Cybersecurity",
        "subcategory": "Web Penetration Testing & Auth Bypass"
    },
    {
        "name": "Dark Reading",
        "url": "https://www.darkreading.com/rss.xml",
        "category": "Offensive Cybersecurity",
        "subcategory": "Threat Intelligence & Cyber Warfare"
    },
    {
        "name": "CVE Alert Feed",
        "url": "https://cvefeed.io/rssfeed/latest.xml",
        "category": "Offensive Cybersecurity",
        "subcategory": "CVE Vulnerability Disclosures"
    }
]

# Targeted Focus Keywords for Scoring & Radar
AI_FOCUS_ENTITIES = [
    # Category 1: US & Europe AI Companies
    "openai", "chatgpt", "gpt-4", "gpt-5", "o1", "o3", "sora", "anthropic", "claude",
    "deepmind", "gemini", "meta ai", "llama", "microsoft", "copilot", "nvidia", "blackwell",
    "b200", "cuda", "hugging face", "perplexity", "mistral", "safe superintelligence", "ssi",
    # Category 2: China AI Companies
    "deepseek", "deepseek-r1", "deepseek-v3", "moonshot", "kimi", "bytedance", "doubao", "qwen", "alibaba",
    # Category 3: CEOs & Leaders
    "sam altman", "satya nadella", "elon musk", "grok", "xai", "jensen huang", "sundar pichai", "yann lecun",
    # Category 4: AI Researchers & Tech Explainers
    "andrej karpathy", "karpathy", "lilian weng", "simon willison", "jianlin su", "prompt injection",
    "jailbreak", "authenticator", "totp", "transistor", "semiconductor", "pixel binning", "sim swap"
]

CYBER_FOCUS_ENTITIES = [
    "zero-day", "0-day", "exploit", "critical", "vulnerability", "bypass",
    "rce", "remote code execution", "sql injection", "authentication bypass",
    "backdoor", "breach", "hacked", "malware", "ransomware", "pegasus", "spyware",
    "kernel", "privilege escalation", "sim swap", "reverse shell", "cve-"
]

def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ")
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def score_article(title: str, summary: str, category: str, base_score: int = 0) -> int:
    score = base_score
    content = f"{title} {summary}".lower()

    if category == "Frontier AI":
        for entity in AI_FOCUS_ENTITIES:
            if entity in content:
                score += 15
        if any(w in content for w in ["breakthrough", "releases", "crushes", "beats", "open-source", "cheaper", "new model"]):
            score += 25
    else:
        for entity in CYBER_FOCUS_ENTITIES:
            if entity in content:
                score += 15
        if any(w in content for w in ["warning", "alert", "millions", "critical", "danger", "active attack", "zero-click"]):
            score += 25

    return score

class ContentResearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 CyberShorts/2.0"
        })

    def fetch_rss_feed_list(self, feed_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        articles = []
        for feed in feed_list:
            try:
                db.log("INFO", "Researcher", f"Scanning {feed['category']}: {feed['name']}")
                parsed = feedparser.parse(feed["url"], agent=self.session.headers["User-Agent"])
                for entry in parsed.entries[:8]:
                    title = clean_html(entry.get("title", ""))
                    link = entry.get("link", "")
                    if not link or not title:
                        continue

                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    summary = clean_html(raw_summary)
                    published = entry.get("published", "") or datetime.utcnow().isoformat()

                    viral_score = score_article(title, summary, feed["category"])

                    articles.append({
                        "url": link,
                        "title": title,
                        "source": feed["name"],
                        "category": feed["category"],
                        "summary": summary[:600],
                        "published_at": published,
                        "score": viral_score
                    })
            except Exception as e:
                db.log("WARNING", "Researcher", f"Failed scraping {feed['name']}: {e}")
        return articles

    def fetch_huggingface_daily_papers(self) -> List[Dict[str, Any]]:
        """Scrapes Hugging Face Daily Papers API for cutting-edge AI breakthroughs."""
        articles = []
        try:
            url = "https://huggingface.co/api/daily_papers"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                papers = resp.json()
                for paper in papers[:10]:
                    title = paper.get("title", "").strip()
                    paper_id = paper.get("id", "")
                    summary = paper.get("summary", "") or paper.get("abstract", "")
                    upvotes = paper.get("upvotes", 0)

                    if not title or not paper_id:
                        continue

                    link = f"https://huggingface.co/papers/{paper_id}"
                    viral_score = score_article(title, summary, "Frontier AI", base_score=min(40, upvotes * 3))

                    articles.append({
                        "url": link,
                        "title": f"New AI Architecture: {title}",
                        "source": "Hugging Face Daily Papers",
                        "category": "Frontier AI",
                        "summary": clean_html(summary)[:500],
                        "published_at": datetime.utcnow().isoformat(),
                        "score": viral_score
                    })
        except Exception as e:
            db.log("WARNING", "Researcher", f"HuggingFace Daily Papers scan warning: {e}")
        return articles

    def fetch_hacker_news_trends(self) -> List[Dict[str, Any]]:
        """Scrapes top Hacker News stories filtered for AI and Cybersecurity breakthroughs."""
        articles = []
        try:
            top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            resp = self.session.get(top_ids_url, timeout=10)
            if resp.status_code == 200:
                top_ids = resp.json()[:30]
                for item_id in top_ids:
                    item_resp = self.session.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=4)
                    if item_resp.status_code == 200:
                        item = item_resp.json()
                        title = item.get("title", "")
                        link = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                        score_val = item.get("score", 0)

                        title_lower = title.lower()
                        # Categorize
                        is_ai = any(kw in title_lower for kw in AI_FOCUS_ENTITIES + ["llm", "deepseek", "gpt", "claude", "gemini", "ai model", "benchmark"])
                        is_cyber = any(kw in title_lower for kw in CYBER_FOCUS_ENTITIES + ["security", "vulnerability", "hack", "bypass", "exploit", "cve"])

                        if is_ai or is_cyber:
                            cat = "Frontier AI" if is_ai else "Offensive Cybersecurity"
                            articles.append({
                                "url": link,
                                "title": title,
                                "source": "Hacker News Top",
                                "category": cat,
                                "summary": f"Viral discussion on Hacker News with {item.get('descendants', 0)} comments and {score_val} points.",
                                "published_at": datetime.utcnow().isoformat(),
                                "score": score_article(title, "", cat, base_score=min(40, score_val // 4))
                            })
        except Exception as e:
            db.log("WARNING", "Researcher", f"Hacker News scan warning: {e}")
        return articles

    def discover_and_save_trending(self) -> List[Dict[str, Any]]:
        """
        Gathers intelligence across both Frontier AI and Offensive Cybersecurity feeds,
        ranks them by viral resonance, and stores novel stories into database.
        """
        db.log("INFO", "Researcher", "Starting dual-track intelligence research (Frontier AI + Offensive Cybersecurity)...")
        all_candidates = []

        # 1. Frontier AI Feeds
        all_candidates.extend(self.fetch_rss_feed_list(AI_FEEDS))
        all_candidates.extend(self.fetch_huggingface_daily_papers())

        # 2. Offensive Cybersecurity Feeds
        all_candidates.extend(self.fetch_rss_feed_list(CYBER_FEEDS))

        # 3. Hacker News Filtered Feed (Both AI & Cyber)
        all_candidates.extend(self.fetch_hacker_news_trends())

        # Sort by viral score descending
        all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

        newly_saved = []
        for candidate in all_candidates:
            if not db.article_exists(candidate["url"]):
                if db.insert_article(candidate):
                    newly_saved.append(candidate)

        ai_count = sum(1 for a in newly_saved if a["category"] == "Frontier AI")
        cyber_count = sum(1 for a in newly_saved if a["category"] == "Offensive Cybersecurity")
        db.log("INFO", "Researcher", f"Discovered {len(all_candidates)} candidates. Saved {len(newly_saved)} fresh stories (Frontier AI: {ai_count}, Offensive Cyber: {cyber_count}).")
        return newly_saved

researcher = ContentResearcher()
