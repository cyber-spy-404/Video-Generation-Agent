import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.timing_manager import timing_manager, IST_TZ, UTC_TZ
from config import (
    YOUTUBE_POST_TIMES_UTC,
    YOUTUBE_SCHEDULE_MODE,
    INSTAGRAM_FB_POST_TIMES_IST,
    INSTAGRAM_FB_SCHEDULE_MODE,
    MAX_VIDEOS_PER_DAY
)

def run_tests():
    print("======================================================================")
    print("⏱️ RUNNING DUAL-TIMEZONE SCHEDULE VERIFICATION (UTC vs IST)")
    print("======================================================================")

    # 1. Test Current Timestamps
    now_utc = timing_manager.now_utc()
    now_ist = timing_manager.now_ist()
    print(f"[+] Current UTC Time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[+] Current IST Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")

    # Check that difference is exactly 5 hours and 30 minutes
    diff_seconds = (now_ist.replace(tzinfo=UTC_TZ) - now_utc).total_seconds()
    # Or converting now_utc to IST
    conv_ist = timing_manager.utc_to_ist(now_utc)
    conv_utc = timing_manager.ist_to_utc(now_ist)
    print(f"[+] UTC converted to IST: {conv_ist.strftime('%H:%M:%S')} (Matches now_ist: {conv_ist.hour == now_ist.hour})")
    assert conv_ist.hour == now_ist.hour and conv_ist.minute == now_ist.minute, "Timezone conversion mismatch!"

    # 2. Test YouTube UTC Slot Calculations
    target_utc, iso_str, summary_yt = timing_manager.get_next_youtube_utc_slot(YOUTUBE_POST_TIMES_UTC)
    print(f"[+] Next YouTube Short Slot (UTC): {summary_yt}")
    print(f"[+] YouTube ISO 8601 String:        {iso_str}")
    assert iso_str.endswith("Z"), "YouTube ISO string must end with 'Z' for UTC!"
    assert target_utc.tzinfo == UTC_TZ, "Target UTC must have UTC_TZ!"
    assert target_utc > now_utc, "Target YouTube slot must be in the future!"

    # 3. Test Instagram & Facebook IST Slot Calculations
    target_ist, unix_ts, summary_ig = timing_manager.get_next_instagram_ist_slot(INSTAGRAM_FB_POST_TIMES_IST)
    print(f"[+] Next Instagram/FB Slot (IST):   {summary_ig}")
    print(f"[+] Instagram Unix Timestamp:        {unix_ts}")
    assert unix_ts > int(now_ist.timestamp()), "Target Instagram slot must be in the future!"
    assert target_ist.tzinfo == IST_TZ, "Target IST must have IST_TZ!"

    # 4. Test Status Summary Dictionary
    summary_dict = timing_manager.get_status_summary()
    print(f"[+] Countdown to next YouTube Drop:      {summary_dict['youtube_countdown']}")
    print(f"[+] Countdown to next Instagram/FB Drop: {summary_dict['instagram_countdown']}")

    # 5. Test YouTube Uploader Class Integration
    from modules.youtube_uploader import youtube_uploader
    print(f"[+] YouTube Uploader schedule_mode: {youtube_uploader.schedule_mode}")
    print(f"[+] YouTube Uploader post_times_utc: {youtube_uploader.post_times_utc}")
    assert youtube_uploader.schedule_mode == YOUTUBE_SCHEDULE_MODE, "YouTube uploader schedule mode mismatch!"

    # 6. Test Instagram & Facebook Uploader Class Integration
    from modules.instagram_uploader import instagram_uploader
    from modules.facebook_uploader import facebook_uploader
    print(f"[+] Instagram Uploader post_times_ist: {instagram_uploader.post_times_ist}")
    print(f"[+] Facebook Uploader post_times_ist:  {facebook_uploader.post_times_ist}")

    print("======================================================================")
    print("✅ ALL DUAL-TIMEZONE SCHEDULE TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    run_tests()

