# services/sms_log.py  (Wrapper เรียก DB แทน CSV)
from .sms_log_store import (
    log_sms_sent as _log_sent,
    log_sms_inbox as _log_inbox,
    log_sms_failed as _log_failed,
    list_logs as _list_logs,
    count_inbox as _count_inbox,
    delete_by_ids as _delete_by_ids,
    delete_all as _delete_all,
    vacuum_db as _vacuum_db
)
from .utility_functions import dedupe_event

def delete_selected(direction: str, ids):
    return _delete_by_ids(direction, ids)

def delete_all(direction: str | None = None, only_failed: bool = False):
    return _delete_all(direction, only_failed)

def vacuum_db():
    _vacuum_db()
    
# API ที่เคยมีอยู่
def log_sms_sent(phone, message, status="ส่งสำเร็จ", dt=None):
    _log_sent(phone, message, status, dt); return True

def log_sms_inbox(phone, message, status="รับเข้า", dt=None):
    _log_inbox(phone, message, status, dt); return True

def log_sms_failed(phone, message, error_msg, dt=None):
    # กันซ้ำ 5 วินาทีต่อ (เบอร์ + เนื้อความ) เดียวกัน
    key = f"send_fail:{phone}:{hash(message)}"
    if not dedupe_event(key, window_seconds=5):
        return False  # บอก caller ว่าข้ามการบันทึก (ซ้ำ)
    _log_failed(phone, message, error_msg, dt)
    return True

# ฟังก์ชันอ่าน/นับที่ UI เคยใช้ (ถ้ามี)
def list_logs(direction=None, phone=None, keyword=None, since=None, until=None,
              limit=500, offset=0, order="DESC"):
    return _list_logs(direction, phone, keyword, since, until, limit, offset, order)

def count_inbox():
    return _count_inbox()

# ถ้าโค้ดเดิมมี helper ชื่อ append_sms_log/get_log_file_path ฯลฯ
# ให้คงไว้ แต่เปลี่ยนให้ชี้ไป DB หรือไม่ทำงาน (ลบการพึ่งพา CSV)
def append_sms_log(*args, **kwargs):
    # ไม่ใช้แล้ว (เดิมไว้เขียน CSV) — คงไว้เพื่อไม่ให้ caller เก่าพัง
    return True

def get_log_file_path(*args, **kwargs):
    # ไม่ใช้แล้ว แต่คงฟังก์ชันไว้
    return None
