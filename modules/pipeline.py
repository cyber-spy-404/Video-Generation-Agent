import os
import concurrent.futures
from typing import Dict, Any, Optional
import config
from config import VOICE_NAME, MAX_VIDEOS_PER_DAY
from modules.database import db
from modules.researcher import researcher
from modules.scriptwriter import scriptwriter
from modules.voice_engine import voice_engine
from modules.subtitles import subtitle_engine
from modules.video_compositor import video_compositor
from modules.storage_uploader import storage_uploader
from modules.youtube_uploader import youtube_uploader
from modules.instagram_uploader import instagram_uploader
from modules.facebook_uploader import facebook_uploader
from modules.sheets_sync import sheets_sync
from modules.style_rotator import style_rotator
from modules.discord_notifier import discord_notifier
from modules.timing_manager import timing_manager

class PipelineOrchestrator:
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)

    def process_article(
        self,
        article: Dict[str, Any],
        bypass_daily_cap: bool = False,
        existing_job_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes complete production lifecycle for a single cybersecurity / tech news story:
        1. Scripting -> 2. Audio -> 3. Subtitles -> 4. Composition ->
        5. Cloud Storage -> 6. YouTube Studio -> 7. Instagram -> 8. Google Sheets
        """
        article_url = article["url"]
        title = article["title"]
        category = article.get("category", "Cybersecurity")

        # Check hard daily limit cap
        completed_today = db.get_completed_videos_count_today()
        if not bypass_daily_cap and completed_today >= config.MAX_VIDEOS_PER_DAY:
            db.log(
                "WARNING",
                "Pipeline",
                f"Daily limit reached ({completed_today}/{config.MAX_VIDEOS_PER_DAY} videos completed today). Skipping article: {title[:50]}"
            )
            return None

        if existing_job_id is not None:
            job_id = existing_job_id
            db.update_video(job_id, status="queued", error_message=None)
            db.log("INFO", "Pipeline", f"Re-initiating production for Job #{job_id}: '{title[:50]}'...")
        else:
            job_id = db.create_video_job(title=title, article_url=article_url)
            db.log("INFO", "Pipeline", f"Initiating production for: {title[:60]}... (Today's count: {completed_today}/{config.MAX_VIDEOS_PER_DAY})")

        db.update_article_status(article_url, "processing")

        try:
            # 1. Generate High-Retention Viral Script
            db.update_video(job_id, status="scripting")
            script_data = scriptwriter.generate_script(article, job_id=job_id)
            script_text = script_data["script"]
            hook = script_data.get("hook", "")
            video_title = script_data.get("title", title)
            tags = script_data.get("tags", ["cybersecurity", "shorts", "tech"])
            description = script_data.get("description", "")

            db.update_video(
                job_id,
                title=video_title,
                hook=hook,
                script=script_text,
                status="scripted"
            )

            # Select Daily & Intra-Day Dynamic Style Preset (Rotating Voices, Fonts & Colors)
            style = style_rotator.get_style_for_job(job_id)
            db.log("INFO", "Pipeline", f"Job #{job_id} style: {style['style_summary']}")

            # 2. Synthesize Free Neural Audio + Word Timings (Dynamic Voice Rotation)
            db.update_video(job_id, status="voice_synthesis")
            audio_path, word_timings = voice_engine.generate_speech(
                script_text,
                job_id,
                voice=style["voice"],
                rate=style["voice_rate"],
                pitch=style["voice_pitch"]
            )
            db.update_video(job_id, audio_path=audio_path)

            # 3. Generate Word-by-Word Highlighted Subtitles (.ass) with dynamic font & theme
            db.update_video(job_id, status="subtitling")
            subs_path = subtitle_engine.generate_ass_subtitles(
                word_timings,
                job_id,
                font_name=style["font_name"],
                font_size=style["font_size"],
                highlight_color=style["highlight_color"]
            )
            db.update_video(job_id, subtitles_path=subs_path)

            # 4. Render 9:16 Vertical Video (Themed typography & story-matched visual vibe)
            db.update_video(job_id, status="rendering")
            video_path = video_compositor.compose_video(
                job_id=job_id,
                title=video_title,
                category=category,
                audio_path=audio_path,
                subtitles_path=subs_path,
                font_path=style.get("font_path"),
                border_color=style.get("badge_border_rgb", (0, 229, 255, 180)),
                script_text=script_text,
                word_timings=word_timings,
                output_filename=f"short_{job_id}.mp4"
            )
            db.update_video(job_id, video_path=video_path, status="rendered")

            # 4B. Generate Instagram Edition (Spoken Hindi Language + Hinglish Transcript Subtitles)
            ig_video_path = video_path
            hindi_caption = script_text
            try:
                db.log("INFO", "Pipeline", f"Crafting Hindi Voice + Hinglish Subtitles for Instagram Reels (Job #{job_id})...")
                hindi_script = scriptwriter.generate_hindi_hinglish_script(script_data, article, job_id=job_id)
                audio_hi_path, timings_hi = voice_engine.generate_speech(
                    hindi_script["hindi_speech"],
                    job_id=int(f"88{job_id}"),
                    voice="hi-IN-MadhurNeural",
                    rate=config.VOICE_RATE
                )
                duration_hi = video_compositor.get_audio_duration(audio_hi_path)
                hinglish_timings = subtitle_engine.align_text_to_word_timings(
                    hindi_script["hinglish_subtitles"],
                    timings_hi,
                    duration_hi
                )
                subs_hi_path = subtitle_engine.generate_ass_subtitles(
                    hinglish_timings,
                    job_id=int(f"88{job_id}"),
                    font_name=style["font_name"],
                    font_size=style["font_size"],
                    highlight_color="&H00F755A8&"  # Electric Lavender / Purple matching alex.cyberx reference reel
                )
                ig_video_path = video_compositor.compose_video(
                    job_id=int(f"88{job_id}"),
                    title=hindi_script.get("title", video_title),
                    category=category,
                    audio_path=audio_hi_path,
                    subtitles_path=subs_hi_path,
                    font_path=style.get("font_path"),
                    border_color=style.get("badge_border_rgb", (0, 229, 255, 180)),
                    script_text=hindi_script.get("hinglish_subtitles"),
                    word_timings=hinglish_timings,
                    output_filename=f"short_instagram_{job_id}.mp4"
                )
                hindi_caption = hindi_script.get("caption", script_text)
                db.log("INFO", "Pipeline", f"Instagram Edition rendered: short_instagram_{job_id}.mp4 (Hindi Voice + Hinglish Subtitles)")
            except Exception as hi_err:
                db.log("WARNING", "Pipeline", f"Instagram Hindi/Hinglish generation fallback: {hi_err}")
                ig_video_path = video_path

            # 5. Free Unlimited Cloud Storage (Telegram Bot / Cloud)
            db.update_video(job_id, status="uploading_storage")
            storage_url = storage_uploader.upload_video(video_path, video_title, category)
            db.update_video(job_id, storage_url=storage_url)

            # Upload Instagram/Facebook Hinglish Edition to Cloud Storage if separate
            ig_storage_url = storage_url
            if ig_video_path and ig_video_path != video_path and os.path.exists(ig_video_path):
                db.log("INFO", "Pipeline", f"Uploading Instagram Hinglish edition to Cloud Storage...")
                ig_uploaded = storage_uploader.upload_video(ig_video_path, f"{video_title} (Hinglish)", category)
                if ig_uploaded:
                    ig_storage_url = ig_uploaded
            db.update_video(job_id, ig_storage_url=ig_storage_url, ig_video_path=ig_video_path)

            # 6, 7 & 8: Simultaneous Distribution (YouTube Shorts, Instagram Reels & Facebook)
            yt_res = None
            ig_url = None
            fb_url = None

            # Check if owner requested "don't post" via Telegram Agent
            from modules.telegram_agent import telegram_agent
            if telegram_agent.auto_post_paused:
                db.log("WARNING", "Pipeline", f"Auto-post paused by owner via Telegram. Holding public upload for Job #{job_id}.")
                telegram_agent.send_message(
                    f"🛑 *Video Job #{job_id} Completed & Held!*\n\n"
                    f"🎬 *Title:* {video_title}\n"
                    f"☁️ *Telegram Storage (EN):* {storage_url}\n"
                    f"☁️ *Telegram Storage (Hinglish):* {ig_storage_url}\n\n"
                    f"Public posting is PAUSED. Say *'post now'* or `/resume` to publish."
                )
                yt_url = "Held (Paused by User via Telegram)"
                ig_url = "Held (Paused by User via Telegram)"
            else:
                def task_youtube():
                    return youtube_uploader.upload_short(video_path, video_title, description, tags)

                def task_instagram():
                    return instagram_uploader.post_reel(ig_video_path, ig_storage_url, video_title, hindi_caption)

                def task_facebook():
                    return facebook_uploader.post_video_reel(ig_video_path, ig_storage_url, video_title, hindi_caption)

                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pub_executor:
                    future_yt = pub_executor.submit(task_youtube)
                    future_ig = pub_executor.submit(task_instagram)
                    future_fb = pub_executor.submit(task_facebook)

                    try:
                        yt_res = future_yt.result()
                    except Exception as e:
                        db.log("ERROR", "Pipeline", f"YouTube worker failed: {e}")

                    try:
                        ig_url = future_ig.result()
                    except Exception as e:
                        db.log("ERROR", "Pipeline", f"Instagram worker failed: {e}")

                    try:
                        fb_url = future_fb.result()
                    except Exception as e:
                        db.log("ERROR", "Pipeline", f"Facebook worker failed: {e}")

            yt_id = yt_res.get("id") if yt_res else None
            yt_url = yt_res.get("url") if yt_res else None
            yt_scheduled_info = ""
            if yt_res and yt_res.get("scheduled"):
                yt_scheduled_info = f" [Scheduled: {yt_res.get('schedule_summary')}]"

            # 9. Log Everything to Google Sheets
            word_count = len(script_text.split()) if script_text else 0
            key_used = script_data.get("key_used", "AI Model")
            try:
                duration_val = video_compositor.get_audio_duration(audio_path)
                duration_str = f"{duration_val:.1f}s"
            except Exception:
                duration_str = "40.0s"

            voice_profile = f"{style['voice']} ({style['voice_rate']}) | Font: {style['font_name']}"
            exec_summary = (
                f"Script ({word_count}w, {key_used}) -> Voice ({duration_str}, {style['voice']}) -> "
                f"Subtitles ({style['font_name']}, {style['name'].split('&')[0].strip()}) -> "
                f"Storage (Telegram Bot) -> YouTube ({'Published' + yt_scheduled_info if yt_url else 'Skipped'}) -> "
                f"Instagram ({'Live in IST window' if ig_url else 'Disabled'})"
            )

            video_record = db.get_video(job_id) or {}
            video_record.update({
                "job_id": job_id,
                "storage_url": storage_url,
                "youtube_url": (yt_url + yt_scheduled_info) if yt_url else "Skipped / Disabled",
                "instagram_url": ig_url or "Disabled",
                "facebook_url": fb_url or "Disabled",
                "status": "completed",
                "duration": duration_str,
                "word_count": f"{word_count} words",
                "key_used": key_used,
                "voice": voice_profile,
                "execution_log": exec_summary
            })
            sheets_sync.log_video_to_sheet(video_record, article)

            # 10. Send Rich Notification to Discord
            try:
                discord_notifier.send_video_update(video_record, article)
            except Exception as d_err:
                db.log("WARNING", "Pipeline", f"Discord update error: {d_err}")

            # Mark as completed in database
            db.update_video(
                job_id,
                youtube_id=yt_id,
                youtube_url=yt_url,
                instagram_url=ig_url,
                facebook_url=fb_url,
                sheet_synced=1,
                status="completed"
            )
            db.update_article_status(article_url, "completed")

            # Evaluate distribution success across enabled platforms
            yt_ok = bool(yt_url)
            ig_ok = bool(ig_url) or not config.INSTAGRAM_AUTO_POST
            fb_ok = bool(fb_url) or not config.FACEBOOK_AUTO_POST
            all_clean = (yt_ok and ig_ok and fb_ok)

            if all_clean:
                db.log("INFO", "Pipeline", f"All destination platforms posted successfully for Job #{job_id}. Cleaning up local temporary video files to preserve VPS disk space (permanent backup kept on Telegram Cloud).")
                try:
                    if video_path and os.path.exists(video_path):
                        os.remove(video_path)
                    if ig_video_path and ig_video_path != video_path and os.path.exists(ig_video_path):
                        os.remove(ig_video_path)
                except Exception as clean_err:
                    db.log("WARNING", "Pipeline", f"Cleanup note: {clean_err}")
            else:
                db.log("INFO", "Pipeline", f"Notice: One or more platform uploads encountered an issue (YT:{yt_ok}, IG:{ig_ok}, FB:{fb_ok}). Local video preserved for later retry after fixing credentials.")

            db.log("INFO", "Pipeline", f"Job #{job_id} successfully produced and distributed!")
            return db.get_video(job_id)

        except Exception as e:
            err_msg = str(e)
            db.log("ERROR", "Pipeline", f"Failed processing article: {err_msg}")
            db.update_video(job_id, status="error", error_message=err_msg)
            db.update_article_status(article_url, "failed")

            # Log failure to Google Sheets for full transparency
            fail_record = {
                "job_id": job_id,
                "title": title,
                "hook": "Error during generation",
                "storage_url": "",
                "youtube_url": "Failed",
                "instagram_url": "Failed",
                "facebook_url": "Failed",
                "status": "failed",
                "duration": "-",
                "word_count": "-",
                "key_used": "-",
                "voice": VOICE_NAME,
                "execution_log": f"Pipeline Error: {err_msg[:160]}"
            }
            try:
                sheets_sync.log_video_to_sheet(fail_record, article)
            except Exception:
                pass

            try:
                discord_notifier.send_error_alert(job_id, title, err_msg)
            except Exception:
                pass
            return None

    def run_cycle(self, limit: int = 1) -> int:
        """
        Runs one end-to-end automated cycle:
        1. Checks daily quota cap (MAX_VIDEOS_PER_DAY).
        2. Researches latest trending cybersecurity & tech news.
        3. Spawns worker jobs up to the remaining daily allowance.
        """
        completed_today = db.get_completed_videos_count_today()
        if completed_today >= config.MAX_VIDEOS_PER_DAY:
            db.log(
                "INFO",
                "Pipeline",
                f"Daily limit reached: {completed_today}/{config.MAX_VIDEOS_PER_DAY} videos already completed today. Standing by for next day."
            )
            print(f"[*] Daily limit reached ({completed_today}/{config.MAX_VIDEOS_PER_DAY} videos today). Standing by for next scheduled slot.")
            return 0

        remaining_allowed = config.MAX_VIDEOS_PER_DAY - completed_today
        effective_limit = min(limit, remaining_allowed)

        db.log("INFO", "Pipeline", f"Running automated cycle (Limit: {effective_limit}, Completed today: {completed_today}/{config.MAX_VIDEOS_PER_DAY})...")
        # 1. Trend research across AI and Cybersecurity
        researcher.discover_and_save_trending()

        # 2. Enforce Daily 1-and-1 Split: Once Frontier AI + Once Offensive Cybersecurity
        completed_categories = db.get_completed_categories_today()
        has_ai = any("ai" in cat.lower() or "frontier" in cat.lower() for cat in completed_categories)
        has_cyber = any("cyber" in cat.lower() or "offensive" in cat.lower() or "pentest" in cat.lower() for cat in completed_categories)

        pending = []
        if not has_ai:
            pending = db.get_pending_articles(limit=effective_limit, category="Frontier AI")
            if pending:
                db.log("INFO", "Pipeline", f"Selected daily drop track: Frontier AI ({len(pending)} articles pending).")

        if not pending and not has_cyber:
            pending = db.get_pending_articles(limit=effective_limit, category="Offensive Cybersecurity")
            if pending:
                db.log("INFO", "Pipeline", f"Selected daily drop track: Offensive Cybersecurity ({len(pending)} articles pending).")

        if not pending:
            pending = db.get_pending_articles(limit=effective_limit)

        if not pending:
            db.log("INFO", "Pipeline", "No pending articles found to process.")
            return 0

        db.log("INFO", "Pipeline", f"Processing {len(pending)} articles simultaneously (Workers: {self.max_concurrent})...")
        futures = [self.executor.submit(self.process_article, art) for art in pending]
        completed = 0
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                completed += 1

        db.log("INFO", "Pipeline", f"Cycle completed. Successfully finished {completed}/{len(pending)} videos (Daily total: {completed_today + completed}/{config.MAX_VIDEOS_PER_DAY}).")
        return completed

    def create_video_from_prompt(self, prompt: str, bypass_daily_cap: bool = True) -> Optional[Dict[str, Any]]:
        """
        Creates, renders, and publishes a complete dual-language video based on an on-demand custom user prompt.
        Immediately publishes that day to YouTube Shorts and Instagram Reels.
        """
        import time
        from datetime import datetime
        clean_prompt = prompt.strip()
        custom_url = f"custom://prompt/{int(time.time())}"
        article = {
            "url": custom_url,
            "title": clean_prompt,
            "source": "Custom Owner Prompt",
            "category": "Cybersecurity & Technology",
            "summary": f"In-depth breakdown requested by channel owner on: {clean_prompt}",
            "published_at": datetime.utcnow().isoformat(),
            "discovered_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        db.insert_article(article)
        db.log("INFO", "Pipeline", f"Received custom prompt from owner: '{clean_prompt}'. Launching immediate production cycle...")
        return self.process_article(article, bypass_daily_cap=bypass_daily_cap)

    def retry_video_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Re-initiates and retries a failed (or stalled) video job.
        Bypasses daily limit cap so retrying a failed job is never blocked.
        """
        video = db.get_video(job_id)
        if not video:
            db.log("WARNING", "Pipeline", f"Cannot retry Job #{job_id}: record not found in database.")
            return None

        article_url = video.get("article_url")
        article = None
        if article_url:
            article = db.get_article(article_url)

        if not article:
            import time
            from datetime import datetime
            article = {
                "url": article_url or f"retry://job/{job_id}/{int(time.time())}",
                "title": video.get("title", "Retried Security Report"),
                "source": "Manual Re-initiate",
                "category": "Offensive Cybersecurity",
                "summary": video.get("script") or video.get("title") or "Retried job execution",
                "published_at": datetime.utcnow().isoformat(),
                "discovered_at": datetime.utcnow().isoformat(),
                "status": "processing"
            }

        db.log("INFO", "Pipeline", f"Re-initiating production for failed Job #{job_id} ('{article['title'][:50]}')...")
        return self.process_article(article, bypass_daily_cap=True, existing_job_id=job_id)

    def publish_video_to_platform(self, job_id: int, platform: str = "all", immediate: bool = True) -> Dict[str, Any]:
        """
        Manually publishes an existing video to a specific platform (or all platforms)
        IMMEDIATELY without fixed schedule times.
        platform: 'youtube' | 'instagram' | 'facebook' | 'all'
        """
        from config import VIDEOS_DIR
        video = db.get_video(job_id)
        if not video:
            return {"status": "error", "message": f"Job #{job_id} not found."}

        # Determine video files with auto-restoration from Cloud Storage if deleted
        video_path = video.get("video_path")
        if not video_path or not os.path.exists(video_path):
            video_path = str(VIDEOS_DIR / f"short_{job_id}.mp4")

        ig_video_path = video.get("ig_video_path") or str(VIDEOS_DIR / f"short_instagram_{job_id}.mp4")

        # Auto-restore video from Telegram / Cloud Storage if file was previously cleaned up
        storage_url = video.get("storage_url")
        ig_storage_url = video.get("ig_storage_url") or storage_url

        if not os.path.exists(video_path) and storage_url and storage_url.startswith("http"):
            db.log("INFO", "Pipeline", f"Restoring short_{job_id}.mp4 from Cloud Storage ({storage_url[:50]}...) for retry...")
            try:
                import requests
                r = requests.get(storage_url, stream=True, timeout=120)
                if r.status_code == 200:
                    with open(video_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            f.write(chunk)
                    db.log("INFO", "Pipeline", f"Restored short_{job_id}.mp4 ({os.path.getsize(video_path)} bytes) from Cloud Storage.")
            except Exception as dl_err:
                db.log("WARNING", "Pipeline", f"Could not restore short_{job_id}.mp4 from storage: {dl_err}")

        if not os.path.exists(ig_video_path) and ig_storage_url and ig_storage_url.startswith("http") and ig_storage_url != storage_url:
            db.log("INFO", "Pipeline", f"Restoring short_instagram_{job_id}.mp4 from Cloud Storage for retry...")
            try:
                import requests
                r = requests.get(ig_storage_url, stream=True, timeout=120)
                if r.status_code == 200:
                    with open(ig_video_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            f.write(chunk)
                    db.log("INFO", "Pipeline", f"Restored short_instagram_{job_id}.mp4 from Cloud Storage.")
            except Exception as dl_err:
                db.log("WARNING", "Pipeline", f"Could not restore short_instagram_{job_id}.mp4 from storage: {dl_err}")

        if not os.path.exists(ig_video_path):
            ig_video_path = video_path

        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": f"Rendered video short_{job_id}.mp4 not found on server or cloud storage. Click 'Re-initiate' to rebuild it."
            }

        video_title = video.get("title", "The Spy Cyber Security Report")
        script_text = video.get("script", "")
        description = f"{script_text}\n\n#TheSpy #Shorts #CyberSecurity #Tech #AI #EthicalHacking"
        tags = ["thespy", "cybersecurity", "shorts", "tech", "ai", "hacking"]
        hindi_caption = f"🚨 {video_title}\n\n{script_text[:350]}...\n\n#TheSpy #CyberSecurity #Shorts #Tech #Reels"

        # Ensure cloud storage URL exists (required by Meta Graph API)
        storage_url = video.get("storage_url")
        if not storage_url or not storage_url.startswith("http"):
            db.log("INFO", "Pipeline", f"Uploading short_{job_id}.mp4 to cloud storage for Meta Graph API...")
            storage_url = storage_uploader.upload_video(video_path, video_title, "Cybersecurity")
            if storage_url:
                db.update_video(job_id, storage_url=storage_url)

        ig_storage_url = storage_url
        if ig_video_path != video_path and os.path.exists(ig_video_path):
            db.log("INFO", "Pipeline", f"Ensuring Instagram Hinglish video is uploaded to cloud storage...")
            uploaded_ig = storage_uploader.upload_video(ig_video_path, f"{video_title} (Hinglish)", "Cybersecurity")
            if uploaded_ig:
                ig_storage_url = uploaded_ig

        results = {}
        target = platform.lower().strip()

        # 1. YouTube
        if target in ("youtube", "all", "both"):
            db.log("INFO", "Pipeline", f"Manual immediate upload: Job #{job_id} -> YouTube Shorts...")
            yt_res = youtube_uploader.upload_short(video_path, video_title, description, tags, immediate=immediate)
            if yt_res and yt_res.get("url"):
                yt_url = yt_res["url"]
                db.update_video(job_id, youtube_id=yt_res.get("id"), youtube_url=yt_url)
                results["youtube"] = yt_url
            else:
                results["youtube"] = "Failed (check YouTube credentials or logs)"

        # 2. Instagram
        if target in ("instagram", "all", "both"):
            db.log("INFO", "Pipeline", f"Manual immediate upload: Job #{job_id} -> Instagram Reels...")
            ig_res = instagram_uploader.post_reel(ig_video_path, ig_storage_url, video_title, hindi_caption, immediate=immediate)
            if ig_res:
                db.update_video(job_id, instagram_url=ig_res)
                results["instagram"] = ig_res
            else:
                results["instagram"] = "Failed (check Instagram credentials or logs)"

        # 3. Facebook
        if target in ("facebook", "all", "both"):
            db.log("INFO", "Pipeline", f"Manual immediate upload: Job #{job_id} -> Facebook Page Reels...")
            fb_res = facebook_uploader.post_video_reel(ig_video_path, ig_storage_url, video_title, hindi_caption, immediate=immediate)
            if fb_res:
                db.update_video(job_id, facebook_url=fb_res)
                results["facebook"] = fb_res
            else:
                results["facebook"] = "Failed (check Facebook credentials or logs)"

        # Check if all destination platforms are now successfully published
        latest_video = db.get_video(job_id) or {}
        yt_done = bool(latest_video.get("youtube_url") and latest_video.get("youtube_url", "").startswith("http"))
        ig_done = bool(latest_video.get("instagram_url") and latest_video.get("instagram_url", "").startswith("http")) or not config.INSTAGRAM_AUTO_POST
        fb_done = bool(latest_video.get("facebook_url") and latest_video.get("facebook_url", "").startswith("http")) or not config.FACEBOOK_AUTO_POST

        if yt_done and ig_done and fb_done:
            db.log("INFO", "Pipeline", f"All platforms now published for Job #{job_id}. Cleaning up local MP4 files to preserve VPS space (Telegram Cloud backup preserved).")
            try:
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)
                if ig_video_path and ig_video_path != video_path and os.path.exists(ig_video_path):
                    os.remove(ig_video_path)
            except Exception as ce:
                db.log("WARNING", "Pipeline", f"Cleanup note: {ce}")

        db.log("INFO", "Pipeline", f"Manual publish finished for Job #{job_id}: {results}")
        return {
            "status": "success",
            "job_id": job_id,
            "platform": target,
            "results": results,
            "message": f"Manual immediate publish complete for Job #{job_id} ({target.upper()})!"
        }

pipeline = PipelineOrchestrator()

