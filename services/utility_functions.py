# --- De-dup helper: กันเด้ง/บันทึกซ้ำในช่วงเวลาสั้น ๆ ---
from datetime import datetime, timedelta

__LAST_EVENTS = {}

def dedupe_event(key: str, window_seconds: int = 5) -> bool:
    """
    True  = ครั้งแรกในช่วงเวลา -> ให้ทำงานต่อ (แสดง dialog/บันทึก)
    False = เคยเกิด event นี้ภายใน window แล้ว -> ข้าม
    """
    now = datetime.now()
    last = __LAST_EVENTS.get(key)
    if last and (now - last) < timedelta(seconds=window_seconds):
        return False
    __LAST_EVENTS[key] = now
    return True
