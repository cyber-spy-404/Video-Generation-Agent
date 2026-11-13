import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR
from modules.database import db
from modules.pipeline import pipeline
from modules.researcher import researcher
from modules.sheets_sync import sheets_sync

app = FastAPI(title="CyberShorts AI VPS Control", version="1.0.0")

templates_dir = BASE_DIR / "web" / "templates"
static_dir = BASE_DIR / "web" / "static"
templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    stats = db.get_stats()
    videos = db.get_all_videos(limit=25)
    logs = db.get_recent_logs(limit=20)
    sheet_url = sheets_sync.get_sheet_link()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "videos": videos,
        "logs": logs,
        "sheet_url": sheet_url
    })

@app.post("/api/run-now")
async def trigger_run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(pipeline.run_cycle, limit=2)
    return JSONResponse({
        "status": "success",
        "message": "Pipeline cycle initiated in background! Check terminal logs."
    })

@app.post("/api/scrape-now")
async def trigger_scrape_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(researcher.discover_and_save_trending)
    return JSONResponse({
        "status": "success",
        "message": "Scraper initiated across Tech & Cybersecurity feeds."
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
    from modules.timing_manager import timing_manager
    return JSONResponse(timing_manager.get_status_summary())

