from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any

# Zero-dependency, rock-solid fixed timezone definitions
# 100% cross-platform compatible across Windows, Linux, Docker, Pterodactyl, and VPS
IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")
UTC_TZ = timezone.utc

class TimingManager:
    """
    Coordinates differentiated posting schedules across global and regional platforms:
    - YouTube Shorts: UTC Peak Timings (Global Tech Audience: US, Europe, Worldwide)
    - Instagram Reels & Facebook: IST Peak Timings (Indian & South Asian Audience: Hindi/Hinglish)
    """

    def __init__(self, youtube_slots_utc: Optional[List[str]] = None, ist_slots: Optional[List[str]] = None):
        self.youtube_slots_utc = youtube_slots_utc or ["15:00", "20:00"]
        self.ist_slots = ist_slots or ["13:00", "20:00"]

    @staticmethod
    def now_utc() -> datetime:
        """Returns current time in UTC."""
        return datetime.now(UTC_TZ)

    @staticmethod
    def now_ist() -> datetime:
        """Returns current time in IST."""
        return datetime.now(IST_TZ)

    @staticmethod
    def utc_to_ist(dt: datetime) -> datetime:
        """Converts any UTC datetime to IST."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt.astimezone(IST_TZ)

    @staticmethod
    def ist_to_utc(dt: datetime) -> datetime:
        """Converts any IST datetime to UTC."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST_TZ)
        return dt.astimezone(UTC_TZ)

    def get_next_slot(self, current_dt: datetime, slots: List[str], min_lead_minutes: int = 15) -> datetime:
        """
        Finds the next upcoming time slot (today or tomorrow) with at least `min_lead_minutes` of buffer.
        Guarantees that YouTube API or Meta Graph API receives a valid future timestamp.
        """
        tz = current_dt.tzinfo or UTC_TZ
        candidates = []
        for day_offset in range(3):  # Check today, tomorrow, and day after
            base_date = (current_dt + timedelta(days=day_offset)).date()
            for slot_str in slots:
                try:
                    slot_str = slot_str.strip()
                    if not slot_str:
                        continue
                    parts = slot_str.split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    slot_dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute, 0, tzinfo=tz)
                    if slot_dt >= current_dt + timedelta(minutes=min_lead_minutes):
                        candidates.append(slot_dt)
                except Exception:
                    continue

        candidates.sort()
        return candidates[0] if candidates else current_dt + timedelta(minutes=min_lead_minutes)

    def get_next_youtube_utc_slot(self, slots: Optional[List[str]] = None, min_lead_minutes: int = 15) -> Tuple[datetime, str, str]:
        """
        Calculates the next optimal UTC slot for YouTube Shorts.
        Returns:
            (target_dt_utc, iso_string_utc, human_summary)
            Example: (dt, "2026-11-13T15:00:00Z", "15:00 UTC (20:30 IST)")
        """
        active_slots = slots or self.youtube_slots_utc
        now_u = self.now_utc()
        target_utc = self.get_next_slot(now_u, active_slots, min_lead_minutes=min_lead_minutes)
        target_ist = self.utc_to_ist(target_utc)

        iso_str = target_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        summary = f"{target_utc.strftime('%H:%M')} UTC ({target_ist.strftime('%H:%M')} IST on {target_ist.strftime('%b %d')})"
        return target_utc, iso_str, summary

    def get_next_instagram_ist_slot(self, slots: Optional[List[str]] = None, min_lead_minutes: int = 10) -> Tuple[datetime, int, str]:
        """
        Calculates the next optimal IST slot for Instagram Reels and Facebook.
        Returns:
            (target_dt_ist, unix_timestamp, human_summary)
            Example: (dt, 1794500000, "13:00 IST (07:30 UTC)")
        """
        active_slots = slots or self.ist_slots
        now_i = self.now_ist()
        target_ist = self.get_next_slot(now_i, active_slots, min_lead_minutes=min_lead_minutes)
        target_utc = self.ist_to_utc(target_ist)

        unix_ts = int(target_ist.timestamp())
        summary = f"{target_ist.strftime('%H:%M')} IST ({target_utc.strftime('%H:%M')} UTC on {target_utc.strftime('%b %d')})"
        return target_ist, unix_ts, summary

    def is_within_peak_window(self, timezone_type: str = "UTC", slots: Optional[List[str]] = None, tolerance_minutes: int = 30) -> bool:
        """
        Checks if the current wall-clock time is within +/- `tolerance_minutes` of any scheduled peak window.
        """
        if timezone_type.upper() == "UTC":
            now_dt = self.now_utc()
            active_slots = slots or self.youtube_slots_utc
        else:
            now_dt = self.now_ist()
            active_slots = slots or self.ist_slots

        for slot_str in active_slots:
            try:
                parts = slot_str.strip().split(":")
                hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
                slot_today = datetime(now_dt.year, now_dt.month, now_dt.day, hour, minute, 0, tzinfo=now_dt.tzinfo)
                diff = abs((now_dt - slot_today).total_seconds()) / 60.0
                if diff <= tolerance_minutes:
                    return True
            except Exception:
                continue
        return False

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns a comprehensive diagnostic dictionary of current dual-timezone state."""
        now_u = self.now_utc()
        now_i = self.now_ist()
        next_yt_dt, next_yt_iso, next_yt_summary = self.get_next_youtube_utc_slot()
        next_ig_dt, next_ig_ts, next_ig_summary = self.get_next_instagram_ist_slot()

        yt_countdown_mins = max(0, int((next_yt_dt - now_u).total_seconds() / 60))
        ig_countdown_mins = max(0, int((next_ig_dt - now_i).total_seconds() / 60))

        return {
            "current_utc": now_u.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "current_ist": now_i.strftime("%Y-%m-%d %H:%M:%S IST"),
            "youtube_schedule_tz": "UTC",
            "youtube_best_times_utc": self.youtube_slots_utc,
            "next_youtube_slot_utc": next_yt_summary,
            "next_youtube_iso": next_yt_iso,
            "youtube_countdown": f"{yt_countdown_mins // 60}h {yt_countdown_mins % 60}m",
            "instagram_fb_schedule_tz": "IST (Asia/Kolkata)",
            "instagram_fb_best_times_ist": self.ist_slots,
            "next_instagram_slot_ist": next_ig_summary,
            "instagram_countdown": f"{ig_countdown_mins // 60}h {ig_countdown_mins % 60}m",
        }

timing_manager = TimingManager()

