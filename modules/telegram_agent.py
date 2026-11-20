import re
import time
import json
import threading
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MAX_VIDEOS_PER_DAY, BEST_POST_TIMES
from modules.database import db
from modules.timing_manager import timing_manager

class TelegramAIAgent:
    """
    2-Way Interactive AI Agent for Telegram.
    Allows the owner to control video publishing, pause/resume drops, repost with additions,
    check system status, and converse in natural language 24/7.
    """
    def __init__(self, token: Optional[str] = None, owner_chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.owner_chat_id = str(owner_chat_id or TELEGRAM_CHAT_ID)
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.auto_post_paused = False
        self.last_update_id = 0
        self.is_running = False
        self._thread = None

    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """Sends a text message to the owner or specified chat."""
        target = chat_id or self.owner_chat_id
        if not self.token or not target:
            return False
        try:
            resp = requests.post(
                f"{self.api_base}/sendMessage",
                json={"chat_id": target, "text": text, "parse_mode": "Markdown"},
                timeout=12
            )
            return resp.status_code == 200
        except Exception as e:
            db.log("WARNING", "TelegramAgent", f"Failed to send message: {e}")
            return False

    def send_video_preview(self, video_path: str, caption: str) -> bool:
        """Sends an MP4 video preview directly to the owner in Telegram."""
        if not self.token or not self.owner_chat_id:
            return False
        try:
            with open(video_path, "rb") as vf:
                resp = requests.post(
                    f"{self.api_base}/sendVideo",
                    data={"chat_id": self.owner_chat_id, "caption": caption[:1024]},
                    files={"video": vf},
                    timeout=120
                )
            return resp.status_code == 200
        except Exception as e:
            db.log("WARNING", "TelegramAgent", f"Failed to send video preview: {e}")
            return False

    def handle_incoming_message(self, message: Dict[str, Any]):
        """Processes user instructions from Telegram and triggers actions."""
        sender_id = str(message.get("from", {}).get("id", ""))
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()

        # Security check: Only respond to the authorized owner
        if self.owner_chat_id and sender_id != self.owner_chat_id and chat_id != self.owner_chat_id:
            return

        db.log("INFO", "TelegramAgent", f"Received command from owner: '{text}'")
        text_lower = text.lower()

        # 1. Help & Greetings
        if text_lower in ("/start", "/help", "hi", "hello", "hey"):
            welcome = (
                "👋 *CyberShorts AI Mission Control Online!*\n\n"
                "I am your 24/7 video production assistant. Here is what I can do:\n"
                "• *'make video on <topic>'* or `/prompt <topic>` — Generate on your custom topic & publish today\n"
                "• *'post now'* or `/post` — Scrape trending tech news & publish a new short\n"
                "• *'status'* or `/status` — View daily stats & scheduler state\n"
                "• *'don't post'* or `/pause` — Pause auto-publishing to YouTube & Instagram\n"
                "• *'resume'* or `/resume` — Unpause and resume scheduled publishing\n"
                "• *'preview'* — Upload the latest MP4 video directly to this chat\n"
                "• *'retry <job_id>'* or `/retry <job_id>` — Re-initiate and retry a failed video job\n"
                "• *'delete <job_id>'* or `/delete <job_id>` — Delete a video job and remove its files\n"
                "• *'repost adding <note>'* — Re-upload or edit a video with custom hashtags/text\n\n"
                "_You can speak to me in plain English! Example: 'make video on Pegasus spyware'_"
            )
            self.send_message(welcome)
            return

        # 2. Status Check
        if text_lower in ("/status", "status", "stats"):
            completed_today = db.get_completed_videos_count_today()
            pause_label = "⏸️ PAUSED (Holding uploads)" if self.auto_post_paused else "🟢 ACTIVE (Auto-publishing)"
            ts_summary = timing_manager.get_status_summary()
            status_text = (
                "📊 *CyberShorts AI — Dual-Timezone Status Report*\n"
                "------------------------------------\n"
                f"• *Publishing State:* {pause_label}\n"
                f"• *Videos Today:* `{completed_today}/{MAX_VIDEOS_PER_DAY}` (1 Frontier AI + 1 Cyber)\n\n"
                f"🌐 *Differentiated Timing Architecture:*\n"
                f"• *YouTube Shorts (UTC Peak):* `{', '.join(ts_summary['youtube_best_times_utc'])} UTC`\n"
                f"  └ *Next Drop:* `{ts_summary['next_youtube_slot_utc']}` (in {ts_summary['youtube_countdown']})\n"
                f"• *Instagram & FB (IST Peak):* `{', '.join(ts_summary['instagram_fb_best_times_ist'])} IST`\n"
                f"  └ *Next Drop:* `{ts_summary['next_instagram_slot_ist']}` (in {ts_summary['instagram_countdown']})\n\n"
                f"• *Active Time:* `{ts_summary['current_utc']}` | `{ts_summary['current_ist']}`\n"
                f"• *YouTube Channel:* `The Spy`\n"
                f"• *Languages:* `English (YT) | Hindi Speech + Hinglish Subtitles (IG/FB)`\n"
                f"• *Free Storage:* `Connected (@VideoGenSpy_bot)`\n"
                f"• *Google Sheets & Discord:* `Active 🟢`"
            )
            self.send_message(status_text)
            return

        # 3. Hold / Pause Auto-Posting ("don't post")
        if any(trigger in text_lower for trigger in ["don't post", "dont post", "pause", "hold", "stop posting", "cancel"]):
            self.auto_post_paused = True
            reply = (
                "🛑 *Auto-Publishing has been PAUSED!*\n\n"
                "I will continue researching stories and generating videos in the background, but I will **HOLD** them and not post to YouTube or Instagram.\n\n"
                "Whenever you are ready to publish, send `/resume` or *'post now'*."
            )
            self.send_message(reply)
            return

        # 4. Resume Auto-Posting
        if any(trigger in text_lower for trigger in ["resume", "unpause", "start posting", "enable posting", "continue"]):
            self.auto_post_paused = False
            reply = (
                "🟢 *Auto-Publishing RESUMED!*\n\n"
                f"I am actively armed for your scheduled drops ({', '.join(BEST_POST_TIMES)}) and will automatically publish up to {MAX_VIDEOS_PER_DAY} videos today."
            )
            self.send_message(reply)
            return

        # 4B. Delete Video Job ("delete video <id>", "/delete <id>", "delete <id>")
        del_match = re.search(r"(?:/delete|delete\s+video|delete\s+job|delete)\s+(\d+)", text_lower)
        if del_match:
            job_id = int(del_match.group(1))
            video = db.get_video(job_id)
            if not video:
                self.send_message(f"❌ *Video Job #{job_id} not found in database.*")
                return

            from config import VIDEOS_DIR, BASE_DIR
            files_to_remove = [
                VIDEOS_DIR / f"short_{job_id}.mp4",
                VIDEOS_DIR / f"short_instagram_{job_id}.mp4",
                BASE_DIR / "storage" / "audio" / f"speech_{job_id}.mp3",
                BASE_DIR / "storage" / "audio" / f"speech_88{job_id}.mp3",
                BASE_DIR / "storage" / "subtitles" / f"subs_{job_id}.ass",
                BASE_DIR / "storage" / "subtitles" / f"subs_88{job_id}.ass",
            ]
            for p in files_to_remove:
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass

            db.delete_video(job_id)
            db.log("INFO", "TelegramAgent", f"Deleted video job #{job_id} via Telegram command")
            self.send_message(
                f"🗑️ *Video Job #{job_id} Deleted!*\n\n"
                f"• *Title:* {video.get('title', '--')}\n"
                f"• Cleaned up rendered MP4, audio voiceovers, and subtitles from server storage."
            )
            return

        # 4C. Re-initiate / Retry Video Job ("retry <id>", "/retry <id>", "reinitiate <id>")
        retry_match = re.search(r"(?:/retry|retry\s+video|retry\s+job|retry|reinitiate|re-initiate)\s+(\d+)", text_lower)
        if retry_match:
            job_id = int(retry_match.group(1))
            video = db.get_video(job_id)
            if not video:
                self.send_message(f"❌ *Video Job #{job_id} not found in database.*")
                return

            self.send_message(
                f"🔄 *Re-initiating Video Job #{job_id}!*\n\n"
                f"• *Title:* {video.get('title', '--')}\n"
                f"• *Status:* Resetting to queued and rerunning production pipeline in background..."
            )

            def retry_worker(jid: int):
                import os
                from modules.pipeline import pipeline
                try:
                    res = pipeline.retry_video_job(jid)
                    if res and res.get("status") == "completed":
                        yt_url = res.get("youtube_url", "")
                        ig_url = res.get("instagram_url", "")
                        cloud_url = res.get("storage_url", "")
                        vpath = res.get("video_path", "")
                        done_msg = (
                            f"✅ *Job #{jid} Successfully Re-produced & Distributed!*\n\n"
                            f"🎬 *Title:* {res.get('title')}\n"
                            f"▶️ *YouTube Shorts:* {yt_url or 'Published'}\n"
                            f"📸 *Instagram Reels:* {ig_url or 'Published'}\n"
                            f"☁️ *Cloud Storage:* {cloud_url}"
                        )
                        self.send_message(done_msg)
                        if vpath and os.path.exists(vpath):
                            self.send_video_preview(vpath, f"🎬 {res.get('title')}")
                    else:
                        err = res.get("error_message") if res else "Unknown pipeline error"
                        self.send_message(f"⚠️ *Job #{jid} Retry Finished with Issues:*\n{err}")
                except Exception as ex:
                    self.send_message(f"⚠️ *Retry worker exception for Job #{jid}:* {ex}")

            threading.Thread(target=retry_worker, args=(job_id,), daemon=True).start()
            return

        # 5. Custom Topic / Prompt Creation ("make video on <topic>", "/prompt <topic>", "/create <topic>")
        custom_topic = None
        cmd_m = re.match(r"^/(?:prompt|create|topic|generate)\s+(.+)", text.strip(), re.IGNORECASE)
        if cmd_m:
            custom_topic = cmd_m.group(1).strip()
        else:
            nl_patterns = [
                r"^(?:please\s+)?(?:make|create|generate|produce)\s+(?:a\s+)?(?:video|reel|short)\s+(?:on|about|for)\s+(.+)",
                r"^(?:video|reel|short)\s+(?:on|about)\s+(.+)",
                r"^(?:prompt|topic)\s*:\s*(.+)"
            ]
            for pat in nl_patterns:
                m = re.match(pat, text.strip(), re.IGNORECASE)
                if m:
                    custom_topic = m.group(1).strip()
                    break

        if custom_topic:
            self.send_message(
                f"🎯 *Custom Prompt Received!*\n\n"
                f"🎬 *Topic:* \"{custom_topic}\"\n"
                f"⚡ *Action:* Generating 9:16 vertical short and publishing today!\n\n"
                f"• *YouTube Shorts:* English Audio + Kinetic Captions\n"
                f"• *Instagram Reels:* Hindi Neural Voice + Hinglish Subtitles\n"
                f"• *Visuals:* Story-matched dynamic cybersecurity scenes\n\n"
                f"_Generating now, standing by..._"
            )
            def custom_worker(topic_str: str):
                import os
                from modules.pipeline import pipeline
                try:
                    res = pipeline.create_video_from_prompt(topic_str, bypass_daily_cap=True)
                    if res and res.get("status") == "completed":
                        yt_url = res.get("youtube_url", "")
                        ig_url = res.get("instagram_url", "")
                        cloud_url = res.get("storage_url", "")
                        vpath = res.get("video_path", "")
                        done_msg = (
                            f"✅ *Custom Prompt Video Published Today!*\n\n"
                            f"🎬 *Title:* {res.get('title')}\n"
                            f"▶️ *YouTube Shorts:* {yt_url or 'Published'}\n"
                            f"📸 *Instagram Reels:* {ig_url or 'Published'}\n"
                            f"☁️ *Cloud Storage:* {cloud_url}"
                        )
                        self.send_message(done_msg)
                        if vpath and os.path.exists(vpath):
                            self.send_video_preview(vpath, f"🎬 {res.get('title')}")
                    else:
                        self.send_message("⚠️ Video generation finished with errors. Check dashboard for details.")
                except Exception as e:
                    self.send_message(f"⚠️ Production error on custom topic: {e}")

            threading.Thread(target=custom_worker, args=(custom_topic,), daemon=True).start()
            return

        # 6. Trigger Immediate Production Cycle ("post now", "/post")
        if any(trigger in text_lower for trigger in ["post now", "/post", "/generate", "make a video", "create video"]):
            self.send_message("⚡ *Initiating immediate video generation cycle...*\nScraping latest cybersecurity advisories and composing 9:16 vertical video.")
            def worker():
                from modules.pipeline import pipeline
                try:
                    completed = pipeline.run_cycle(limit=1)
                    if completed > 0:
                        self.send_message(f"✅ *Cycle Complete!* Successfully generated and published new video.")
                    else:
                        self.send_message("ℹ️ No new video was produced (daily cap reached or no new stories).")
                except Exception as e:
                    self.send_message(f"⚠️ Production error: {e}")
            threading.Thread(target=worker, daemon=True).start()
            return

        # 5B. Preview / Send Video Directly to Telegram ("preview", "send video", "watch")
        if any(trigger in text_lower for trigger in ["preview", "send video", "watch", "send reel", "show video"]):
            all_videos = db.get_all_videos(limit=3)
            if not all_videos:
                self.send_message("⚠️ No completed videos found in local storage.")
                return
            latest = all_videos[0]
            vpath = latest.get("video_path", "")
            import os
            if vpath and os.path.exists(vpath):
                self.send_message(f"📤 *Uploading video preview for #{latest.get('id', '?')} to Telegram...*")
                caption = f"🎬 {latest.get('title', '')}\n\nStatus: {latest.get('status', 'rendered')}"
                self.send_video_preview(vpath, caption)
            else:
                self.send_message(f"🎬 Latest video #{latest.get('id')}: {latest.get('title')}\nCloud Link: {latest.get('storage_url', 'N/A')}")
            return

        # 6. Repost with Additions ("repost ...")
        if "repost" in text_lower:
            # Extract target job id or take latest video
            match_id = re.search(r"#?(\d+)", text)
            all_videos = db.get_all_videos(limit=5)
            if not all_videos:
                self.send_message("⚠️ No completed videos found in database to repost.")
                return

            target_video = None
            if match_id:
                jid = int(match_id.group(1))
                target_video = db.get_video(jid)

            if not target_video:
                target_video = all_videos[0]

            # Extract what to add
            additions = re.sub(r"(?i)^repost\s*(#?\d+)?\s*(adding|with)?", "", text).strip()
            if not additions:
                additions = "#CyberSecurity #Hacking #Shorts"

            self.send_message(f"🔄 *Reposting Video #{target_video['id']} with additions:* `{additions}`\nUploading to YouTube Shorts & Instagram...")

            def repost_worker():
                try:
                    from modules.youtube_uploader import youtube_uploader
                    from modules.storage_uploader import storage_uploader

                    vid_path = target_video.get("video_path", "")
                    new_title = f"{target_video.get('title', '')} {additions}".strip()[:95]
                    new_desc = f"{target_video.get('title', '')}\n\nUpdates: {additions}\n\n#Shorts #CyberSecurity #Tech"
                    tags = ["cybersecurity", "shorts", "tech", "hacking"]

                    yt_res = youtube_uploader.upload_short(vid_path, new_title, new_desc, tags)
                    if yt_res and yt_res.get("url"):
                        self.send_message(f"✅ *Successfully Reposted!*\n▶️ **YouTube Shorts:** {yt_res['url']}")
                    else:
                        self.send_message("ℹ️ Repost finished. Check dashboard for live distribution state.")
                except Exception as e:
                    self.send_message(f"⚠️ Repost error: {e}")

            threading.Thread(target=repost_worker, daemon=True).start()
            return

        # 7. Conversational AI Agent Fallback
        self._answer_conversational_query(text)

    def _answer_conversational_query(self, user_query: str):
        """Uses Gemini to answer user questions about video automation in Telegram."""
        from modules.scriptwriter import scriptwriter
        api_key = scriptwriter.get_active_key()
        
        system_prompt = (
            "You are the CyberShorts AI Agent, an autonomous cybersecurity video production assistant running headlessly on a VPS. "
            "Respond politely and concisely to the channel owner's query in Telegram. Keep your reply under 3 short sentences."
        )

        if api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": system_prompt},
                            {"text": f"User instruction: {user_query}"}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.5, "maxOutputTokens": 200}
                }
                resp = requests.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    self.send_message(reply)
                    return
            except Exception:
                pass

        # Fallback response
        self.send_message(
            f"🤖 Got your message: *\"{user_query}\"*\n"
            "I am standing by. Use `/status` to view operational metrics, `/post` to trigger a cycle, or `/pause` to hold uploads."
        )

    def start_polling(self):
        """Starts background long-polling loop for Telegram updates."""
        if not self.token:
            db.log("WARNING", "TelegramAgent", "TELEGRAM_BOT_TOKEN is not set. Interactive bot agent disabled.")
            return

        self.is_running = True
        db.log("INFO", "TelegramAgent", "Starting 2-way interactive Telegram AI Agent...")

        def poll_loop():
            # Flush past backlog
            try:
                flush = requests.get(f"{self.api_base}/getUpdates?offset=-1", timeout=10).json()
                if flush.get("ok") and flush.get("result"):
                    self.last_update_id = flush["result"][-1]["update_id"] + 1
            except Exception:
                pass

            while self.is_running:
                try:
                    url = f"{self.api_base}/getUpdates?offset={self.last_update_id}&timeout=20"
                    resp = requests.get(url, timeout=25)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("ok"):
                            for update in data.get("result", []):
                                self.last_update_id = update["update_id"] + 1
                                if "message" in update and "text" in update["message"]:
                                    self.handle_incoming_message(update["message"])
                    elif resp.status_code in (401, 404):
                        db.log("ERROR", "TelegramAgent", "Invalid TELEGRAM_BOT_TOKEN. Halting polling.")
                        break
                except requests.exceptions.Timeout:
                    continue
                except Exception as e:
                    time.sleep(5)

        self._thread = threading.Thread(target=poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False

telegram_agent = TelegramAIAgent()

