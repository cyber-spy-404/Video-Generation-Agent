import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import config
from config import (
    BASE_DIR,
    VIDEOS_DIR,
    MAX_VIDEOS_PER_DAY,
    YOUTUBE_POST_TIMES_UTC,
    INSTAGRAM_FB_POST_TIMES_IST,
    ROTATE_STYLES,
    TARGET_TOPICS,
    FREELLMAPI_ENABLED,
    YOUTUBE_SCHEDULE_MODE,
    INSTAGRAM_FB_SCHEDULE_MODE
)
from modules.database import db
from modules.pipeline import pipeline
from modules.researcher import researcher
from modules.sheets_sync import sheets_sync
from modules.timing_manager import timing_manager
from modules.telegram_agent import telegram_agent

app = FastAPI(title="CyberShorts AI VPS Mission Control", version="2.0.0")

templates_dir = BASE_DIR / "web" / "templates"
static_dir = BASE_DIR / "web" / "static"
templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    stats = db.get_stats()
    videos = db.get_all_videos(limit=50)
    logs = db.get_recent_logs(limit=30)
    sheet_url = sheets_sync.get_sheet_link()
    
    completed_today = db.get_completed_videos_count_today()
    completed_categories = db.get_completed_categories_today()
    schedule_data = timing_manager.get_status_summary()

    system_state = {
        "paused": telegram_agent.auto_post_paused,
        "completed_today": completed_today,
        "max_videos_per_day": MAX_VIDEOS_PER_DAY,
        "completed_categories": completed_categories,
        "has_ai": any("ai" in c.lower() or "frontier" in c.lower() for c in completed_categories),
        "has_cyber": any("cyber" in c.lower() or "offensive" in c.lower() or "pentest" in c.lower() for c in completed_categories),
        "schedule": schedule_data,
        "stats": stats,
        "config": {
            "max_videos_per_day": MAX_VIDEOS_PER_DAY,
            "youtube_slots_utc": YOUTUBE_POST_TIMES_UTC,
            "youtube_mode": YOUTUBE_SCHEDULE_MODE,
            "instagram_slots_ist": INSTAGRAM_FB_POST_TIMES_IST,
            "instagram_mode": INSTAGRAM_FB_SCHEDULE_MODE,
            "rotate_styles": ROTATE_STYLES,
            "freellmapi_enabled": FREELLMAPI_ENABLED,
            "target_topics": TARGET_TOPICS
        }
    }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stats": stats,
            "videos": videos,
            "logs": logs,
            "sheet_url": sheet_url,
            "state": system_state
        }
    )

@app.post("/api/run-now")
async def trigger_run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(pipeline.run_cycle, limit=1)
    return JSONResponse({
        "status": "success",
        "message": "Automated pipeline cycle initiated! Generating video in background..."
    })

@app.post("/api/scrape-now")
async def trigger_scrape_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(researcher.discover_and_save_trending)
    return JSONResponse({
        "status": "success",
        "message": "Scraper initiated across 40+ AI and Cybersecurity radar feeds."
    })

@app.post("/api/create-prompt")
async def create_prompt_api(request: Request, background_tasks: BackgroundTasks):
    """
    On-Demand Video Creation from Web UI.
    Generates English + Hindi editions and publishes immediately today.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    prompt_text = body.get("prompt", "").strip()
    category = body.get("category", "Frontier AI & Cybersecurity")

    if not prompt_text:
        return JSONResponse({"status": "error", "message": "Please enter a valid topic or prompt."}, status_code=400)

    # Launch background generation
    background_tasks.add_task(pipeline.create_video_from_prompt, prompt=prompt_text, bypass_daily_cap=True)
    db.log("INFO", "WebDashboard", f"Custom video creation requested from Web UI: '{prompt_text}' ({category})")

    return JSONResponse({
        "status": "success",
        "message": f"Video production started for: '{prompt_text[:50]}'! Monitor progress in Live Telemetry."
    })

@app.post("/api/toggle-pause")
async def toggle_pause_api():
    """Toggles global auto-publishing state (holding in storage vs live release)."""
    telegram_agent.auto_post_paused = not telegram_agent.auto_post_paused
    state_str = "PAUSED (Holding public uploads)" if telegram_agent.auto_post_paused else "ACTIVE (Auto-publishing)"
    db.log("INFO", "WebDashboard", f"Publishing state updated via Web UI: {state_str}")
    return JSONResponse({
        "status": "success",
        "paused": telegram_agent.auto_post_paused,
        "message": f"Auto-publishing is now {state_str}"
    })

@app.get("/api/system-state")
async def get_system_state_api():
    completed_today = db.get_completed_videos_count_today()
    completed_categories = db.get_completed_categories_today()
    schedule_data = timing_manager.get_status_summary()
    return JSONResponse({
        "paused": telegram_agent.auto_post_paused,
        "completed_today": completed_today,
        "max_videos_per_day": MAX_VIDEOS_PER_DAY,
        "completed_categories": completed_categories,
        "has_ai": any("ai" in c.lower() or "frontier" in c.lower() for c in completed_categories),
        "has_cyber": any("cyber" in c.lower() or "offensive" in c.lower() or "pentest" in c.lower() for c in completed_categories),
        "schedule": schedule_data,
        "stats": db.get_stats()
    })

@app.get("/api/video/{job_id}/stream")
async def stream_video_api(job_id: int, edition: str = "global"):
    """Streams rendered MP4 video directly to browser player."""
    filename = f"short_{job_id}.mp4" if edition == "global" else f"short_instagram_{job_id}.mp4"
    video_path = VIDEOS_DIR / filename
    
    if not video_path.exists():
        # Fallback to standard short_{job_id}.mp4
        video_path = VIDEOS_DIR / f"short_{job_id}.mp4"
        
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found or still rendering.")
        
    return FileResponse(str(video_path), media_type="video/mp4", filename=filename)

@app.get("/api/video/{job_id}/details")
async def video_details_api(job_id: int):
    """Returns detailed metadata, script, and prompt info for a job."""
    video = db.get_video(job_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found.")
    return JSONResponse(dict(video))

@app.delete("/api/video/{job_id}")
async def delete_video_api(job_id: int):
    """Deletes a video record and its associated physical files from disk."""
    video = db.get_video(job_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found.")

    # Remove physical media files from disk if they exist
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
        except Exception as fe:
            db.log("WARNING", "WebDashboard", f"Could not remove file {p.name}: {fe}")

    deleted = db.delete_video(job_id)
    db.log("INFO", "WebDashboard", f"Deleted video job #{job_id} ('{video.get('title', '')[:40]}')")
    return JSONResponse({
        "status": "success",
        "message": f"Video job #{job_id} and all rendered media files have been deleted successfully."
    })

@app.post("/api/video/{job_id}/retry")
async def retry_video_api(job_id: int, background_tasks: BackgroundTasks):
    """Re-initiates and reruns a failed video job in the background."""
    video = db.get_video(job_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video job #{job_id} not found.")

    background_tasks.add_task(pipeline.retry_video_job, job_id=job_id)
    db.log("INFO", "WebDashboard", f"Re-initiate requested for Job #{job_id} ('{video.get('title', '')[:40]}')")

    return JSONResponse({
        "status": "success",
        "message": f"Job #{job_id} has been re-initiated! Production is running in the background."
    })

@app.post("/api/video/{job_id}/publish/{platform}")
async def publish_video_platform_api(job_id: int, platform: str, background_tasks: BackgroundTasks):
    """
    Manually publishes a video to a specific platform (or all) immediately without fixed scheduled times.
    platform: 'youtube' | 'instagram' | 'facebook' | 'all'
    """
    video = db.get_video(job_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video job #{job_id} not found.")

    target = platform.lower().strip()
    valid_platforms = ["youtube", "instagram", "facebook", "all"]
    if target not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Invalid platform '{platform}'. Choose from: {valid_platforms}")

    background_tasks.add_task(pipeline.publish_video_to_platform, job_id=job_id, platform=target, immediate=True)
    db.log("INFO", "WebDashboard", f"Manual publish triggered for Job #{job_id} to {target.upper()} (Immediate, no fixed times)")

    return JSONResponse({
        "status": "success",
        "message": f"Publishing Job #{job_id} to {target.upper()} immediately without fixed times! Check Live Telemetry for updates."
    })

@app.get("/api/stats")
async def get_stats_api():
    return JSONResponse(db.get_stats())

@app.get("/api/videos")
async def get_videos_api(limit: int = 50):
    return JSONResponse(db.get_all_videos(limit=limit))

@app.get("/api/logs")
async def get_logs_api(limit: int = 30):
    return JSONResponse(db.get_recent_logs(limit=limit))

@app.get("/api/schedule")
async def get_schedule_api():
    return JSONResponse(timing_manager.get_status_summary())

