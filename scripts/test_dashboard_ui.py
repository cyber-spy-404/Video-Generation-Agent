import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.dashboard import app

def test_dashboard():
    print("======================================================================")
    print("🧪 TESTING WEB MISSION CONTROL DASHBOARD UI & API ENDPOINTS")
    print("======================================================================")

    client = TestClient(app)

    # 1. Test Home Page HTML Render
    print("[*] Testing GET / (HTML Dashboard)...")
    resp = client.get("/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.text
    assert "CyberShorts AI Mission Control" in html, "Dashboard title missing in HTML!"
    assert "btn-run" in html, "DOM ID #btn-run missing!"
    assert "btn-scrape" in html, "DOM ID #btn-scrape missing!"
    assert "terminal-logs" in html, "DOM ID #terminal-logs missing!"
    assert "modal-video-preview" in html, "Video preview modal missing in HTML!"
    assert "input-prompt" in html, "Custom prompt input missing in HTML!"
    print("[+] GET / rendered successfully with all mandatory DOM IDs and components!")

    # 2. Test GET /api/system-state
    print("[*] Testing GET /api/system-state...")
    resp = client.get("/api/system-state")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    state = resp.json()
    assert "paused" in state, "State missing 'paused' key!"
    assert "schedule" in state, "State missing 'schedule' key!"
    assert "youtube_countdown" in state["schedule"], "Schedule missing countdown!"
    print(f"[+] GET /api/system-state verified: (Paused: {state['paused']}, Cap: {state['max_videos_per_day']})")

    # 3. Test POST /api/toggle-pause
    print("[*] Testing POST /api/toggle-pause...")
    resp = client.post("/api/toggle-pause")
    assert resp.status_code == 200
    p1 = resp.json()
    print(f"[+] Toggle 1: Paused = {p1['paused']}")
    resp = client.post("/api/toggle-pause")
    assert resp.status_code == 200
    p2 = resp.json()
    print(f"[+] Toggle 2: Paused = {p2['paused']}")
    assert p1['paused'] != p2['paused'], "Toggle pause failed to switch state!"

    # 4. Test POST /api/create-prompt validation
    print("[*] Testing POST /api/create-prompt (Validation)...")
    resp = client.post("/api/create-prompt", json={"prompt": ""})
    assert resp.status_code == 400, "Empty prompt should return 400!"
    resp = client.post("/api/create-prompt", json={"prompt": "Test AI Breakthrough", "category": "Frontier AI"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.json()["status"] == "success"
    print("[+] POST /api/create-prompt verified!")

    # 5. Test GET /api/schedule
    print("[*] Testing GET /api/schedule...")
    resp = client.get("/api/schedule")
    assert resp.status_code == 200
    sched = resp.json()
    assert "next_youtube_slot_utc" in sched
    assert "next_instagram_slot_ist" in sched
    print(f"[+] GET /api/schedule verified: YouTube next: {sched['next_youtube_slot_utc']} | Instagram next: {sched['next_instagram_slot_ist']}")

    print("======================================================================")
    print("✅ ALL DASHBOARD WEB MANAGEMENT TESTS PASSED SUCCESSFULLY (100%)!")
    print("======================================================================")

if __name__ == "__main__":
    test_dashboard()

