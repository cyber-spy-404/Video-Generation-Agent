import sys
import time
import argparse
import threading
import schedule
import uvicorn

from config import (
    FETCH_INTERVAL_MINUTES,
    AUTO_GENERATE_COUNT,
    MAX_VIDEOS_PER_DAY,
    DASHBOARD_HOST,
    DASHBOARD_PORT,
    SCHEDULE_MODE,
    BEST_POST_TIMES,
    TIMEZONE,
    YOUTUBE_POST_TIMES_UTC,
    YOUTUBE_SCHEDULE_MODE,
    INSTAGRAM_FB_POST_TIMES_IST,
    INSTAGRAM_FB_SCHEDULE_MODE
)
from modules.database import db
from modules.researcher import researcher
from modules.pipeline import pipeline
from modules.timing_manager import timing_manager, IST_TZ, UTC_TZ

def run_scheduled_job():
    """Periodic worker job executed by scheduler."""
    completed_today = db.get_completed_videos_count_today()
    if completed_today >= MAX_VIDEOS_PER_DAY:
        db.log("INFO", "Scheduler", f"Daily cap reached ({completed_today}/{MAX_VIDEOS_PER_DAY} videos). Standing by for next day.")
        print(f"[*] Daily limit reached ({completed_today}/{MAX_VIDEOS_PER_DAY} videos today). Skipping scheduled trigger.")
        return

    db.log("INFO", "Scheduler", f"Periodic trigger: starting production cycle ({completed_today}/{MAX_VIDEOS_PER_DAY} completed today).")
    try:
        pipeline.run_cycle(limit=AUTO_GENERATE_COUNT)
    except Exception as e:
        db.log("ERROR", "Scheduler", f"Automated cycle encountered an exception: {e}")

def scheduler_thread():
    """Background daemon loop that executes dual-timezone scheduled runs."""
    from datetime import datetime, timedelta
    triggered_slots_today = set()
    last_cleanup_day = None

    timing_summary = timing_manager.get_status_summary()
    print("[*] ==================================================================")
    print("[*] 🌐 DUAL-TIMEZONE AUTONOMOUS SCHEDULER ARMED")
    print(f"[*] • YouTube Shorts (UTC Peak Timings):       {YOUTUBE_POST_TIMES_UTC} -> Next: {timing_summary['next_youtube_slot_utc']}")
    print(f"[*] • Instagram & Facebook (IST Peak Timings): {INSTAGRAM_FB_POST_TIMES_IST} -> Next: {timing_summary['next_instagram_slot_ist']}")
    print(f"[*] • Daily Balance: Exactly 1 Frontier AI + 1 Offensive Cyber (Max: {MAX_VIDEOS_PER_DAY}/day)")
    print("[*] ==================================================================")

    db.log(
        "INFO",
        "Scheduler",
        f"Armed Dual-Timezone Scheduler: YouTube UTC {YOUTUBE_POST_TIMES_UTC} | Instagram/FB IST {INSTAGRAM_FB_POST_TIMES_IST} (Max {MAX_VIDEOS_PER_DAY}/day)"
    )

    # Initial research scan on boot
    try:
        researcher.discover_and_save_trending()
    except Exception as e:
        db.log("WARNING", "Scheduler", f"Initial scan warning: {e}")

    # Set up periodic news scraping in schedule
    schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(lambda: researcher.discover_and_save_trending())

    while True:
        try:
            # 1. Run standard schedule jobs (e.g. interval scraper)
            schedule.run_pending()

            # 2. Timezone-aware IST Posting Slot Check
            now_i = timing_manager.now_ist()
            today_str = now_i.strftime("%Y-%m-%d")

            # Daily cleanup of fired triggers at midnight
            if last_cleanup_day != today_str:
                triggered_slots_today.clear()
                last_cleanup_day = today_str

            for slot_str in INSTAGRAM_FB_POST_TIMES_IST:
                try:
                    slot_parts = slot_str.strip().split(":")
                    hour = int(slot_parts[0])
                    minute = int(slot_parts[1]) if len(slot_parts) > 1 else 0
                    slot_dt = datetime(now_i.year, now_i.month, now_i.day, hour, minute, 0, tzinfo=IST_TZ)

                    # Trigger if current IST time is between slot_dt and slot_dt + 15 minutes
                    if slot_dt <= now_i < (slot_dt + timedelta(minutes=15)):
                        key = (today_str, slot_str)
                        if key not in triggered_slots_today:
                            triggered_slots_today.add(key)
                            print(f"[+] 🎯 IST Peak Time Slot Triggered: {slot_str} IST! Launching automated production cycle...")
                            db.log("INFO", "Scheduler", f"IST Peak Posting Slot Triggered: {slot_str} IST.")
                            run_scheduled_job()
                except Exception as slot_err:
                    db.log("WARNING", "Scheduler", f"Error evaluating slot {slot_str}: {slot_err}")

        except Exception as loop_err:
            db.log("ERROR", "Scheduler", f"Scheduler loop error: {loop_err}")

        time.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="CyberShorts AI - Autonomous VPS Video Automation Engine")
    parser.add_argument("--now", action="store_true", help="Run one full generation cycle right now and exit")
    parser.add_argument("--prompt", type=str, help="Generate a video on a custom topic/prompt and publish today")
    parser.add_argument("--scrape", action="store_true", help="Scrape trending Tech/Cybersecurity feeds and exit")
    parser.add_argument("--test-all", action="store_true", help="Run diagnostics on all engine components")
    parser.add_argument("--daemon", action="store_true", default=True, help="Run background scheduler & web dashboard (default)")

    args = parser.parse_args()

    print("======================================================================")
    print("⚡ CYBERSHORTS AI: VPS AUTONOMOUS VIDEO PRODUCTION ENGINE")
    print("======================================================================")

    if args.prompt:
        print(f"[*] Custom prompt requested: \"{args.prompt}\"")
        print("[*] Generating 9:16 vertical video & publishing today...")
        res = pipeline.create_video_from_prompt(args.prompt, bypass_daily_cap=True)
        if res and res.get("status") == "completed":
            print(f"[+] Successfully produced and published video: {res.get('title')}")
            print(f"[+] YouTube: {res.get('youtube_url')}")
            print(f"[+] Instagram: {res.get('instagram_url')}")
            print(f"[+] Cloud Storage: {res.get('storage_url')}")
        else:
            print(f"[-] Video production failed or returned incomplete status.")
        return

    if args.scrape:
        print("[*] Scraping Tech, Cybersecurity & Web Pentesting feeds...")
        saved = researcher.discover_and_save_trending()
        print(f"[+] Found and saved {len(saved)} new trending stories to database.")
        return

    if args.now:
        print("[*] Running immediate production cycle...")
        completed = pipeline.run_cycle(limit=1)
        print(f"[+] Completed {completed} video(s). Check storage and dashboard.")
        return

    if args.test_all:
        from scripts.test_pipeline import run_diagnostics
        run_diagnostics()
        return

    # Default: Daemon mode
    print(f"[*] Starting background scheduler (Interval: {FETCH_INTERVAL_MINUTES}m)...")
    s_thread = threading.Thread(target=scheduler_thread, daemon=True)
    s_thread.start()

    # Start 2-Way Interactive Telegram AI Agent
    from modules.telegram_agent import telegram_agent
    telegram_agent.start_polling()
    print("[*] 2-Way Telegram AI Agent online (Listening for commands from owner)...")

    print(f"[*] Starting Web Mission Control on http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print("[*] Access this URL in your browser to monitor jobs and view metrics.")
    print("----------------------------------------------------------------------")

    from modules.dashboard import app
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="info")

if __name__ == "__main__":
    main()

