# services/sms_log_store.py
# ------------------------------------------------------------
# บริการบันทึก/อ่าน LOG ของ SMS
# - เขียนลง SQLite ตามเดิม (ถ้าต้องการ)
# - และ "มิร์เรอร์" ลง CSV ข้าง .exe
# - หน้า History สามารถสลับมาอ่านจาก CSV ได้
# - CSV ไม่มีคอลัมน์ is_failed แล้ว → เวลาคืนค่าจาก CSV จะคำนวณ is_failed จาก status ให้
# ------------------------------------------------------------
from __future__ import annotations
from typing import Optional, List, Dict, Any, Union, Iterable
from datetime import datetime, timedelta
from pathlib import Path
import sys

# SQLite connection ใช้ตามเดิม (ไม่มี get_db_file_path แล้ว)
from .db import get_conn

# ---------- โหมด/พาธ CSV ----------
USE_CSV_ONLY  = False   # True = เขียนเฉพาะ CSV (ไม่แตะ SQLite)
READ_FROM_CSV = True    # True = list_logs อ่านจาก CSV
MIRROR_TO_CSV = True    # True = เวลาเขียน จะ append CSV ด้วย

ISO_FMT = "%Y-%m-%d %H:%M:%S"

def _app_dir() -> Path:
    """คืนโฟลเดอร์โปรแกรม (รองรับทั้งตอนรันจากโค้ดและไฟล์ .exe ของ PyInstaller)"""
    if getattr(sys, "_MEIPASS", None):
        # รันจาก .exe → โฟลเดอร์เดียวกับโปรแกรม
        return Path(sys.executable).resolve().parent
    # รันจากซอร์ส → โฟลเดอร์โปรเจกต์ (services/.. → root)
    return Path(__file__).resolve().parents[1]

_CSV_PATH = _app_dir() / "sim_logs.csv"

def get_csv_file_path() -> str:
    return str(_CSV_PATH)
# -----------------------------------

def _now() -> datetime:
    return datetime.now().replace(microsecond=0)

def _fmt_dt(dt: Optional[Union[datetime, str]]) -> str:
    if isinstance(dt, str):
        return dt
    return (dt or _now()).strftime(ISO_FMT)

def _mirror_csv(direction: str, phone: str, message: str, status: str, when: str) -> None:
    from .csv_store import append_row
    append_row(_CSV_PATH, direction=direction, phone=phone, message=message, status=status, dt=when)

# ============================================================
# Low-level INSERT helpers
# ============================================================
def _insert_sent(
    phone: str,
    message: str,
    status: str,
    dt: Optional[Union[datetime, str]] = None,
    is_failed: bool = False,
    error_code: Optional[str] = None,
) -> None:
    """บันทึกลง 'sms_sent' และ (ตามสวิตช์) เขียน CSV"""
    when = _fmt_dt(dt)

    # CSV only
    if USE_CSV_ONLY:
        _mirror_csv("sent", phone or "Unknown", message or "", status or ("ล้มเหลว" if is_failed else "ส่งสำเร็จ"), when)
        return

    # SQLite ปกติ
    sql = """
        INSERT INTO sms_sent (phone, message, status, is_failed, error_code, dt)
        VALUES (?,?,?,?,?,?)
    """
    args = [
        phone or "Unknown",
        message or "",
        status or ("ล้มเหลว" if is_failed else "ส่งสำเร็จ"),
        1 if is_failed else 0,
        error_code,
        when,
    ]
    with get_conn() as conn:
        conn.execute(sql, args)
        conn.commit()

    # mirror CSV
    if MIRROR_TO_CSV:
        _mirror_csv("sent", args[0], args[1], args[2], when)

def _insert_inbox(
    phone: str,
    message: str,
    status: str,
    dt: Optional[Union[datetime, str]] = None,
) -> None:
    """บันทึกลง 'sms_inbox' และ (ตามสวิตช์) เขียน CSV"""
    when = _fmt_dt(dt)

    # CSV only
    if USE_CSV_ONLY:
        _mirror_csv("inbox", phone or "Unknown", message or "", status or "รับเข้า", when)
        return

    # SQLite ปกติ
    sql = """
        INSERT INTO sms_inbox (phone, message, status, dt)
        VALUES (?,?,?,?)
    """
    args = [phone or "Unknown", message or "", status or "รับเข้า", when]
    with get_conn() as conn:
        conn.execute(sql, args)
        conn.commit()

    # mirror CSV
    if MIRROR_TO_CSV:
        _mirror_csv("inbox", args[0], args[1], args[2], when)

# ============================================================
# Public write APIs
# ============================================================
def log_sms_sent(phone, message, status="ส่งสำเร็จ", dt=None):
    _insert_sent(phone, message, status, dt, is_failed=False)

def log_sms_inbox(phone, message, status="รับเข้า", dt=None):
    _insert_inbox(phone, message, status, dt)

def log_sms_failed(phone, message, error_msg, dt=None, error_code=None, dedupe_seconds=10):
    """กันซ้ำเคสล้มเหลวระยะสั้น แล้วบันทึกเป็น 'ล้มเหลว: ...'"""
    when = _fmt_dt(dt)

    # CSV only: กันซ้ำจาก CSV (ดูไม่กี่รายการล่าสุด)
    if USE_CSV_ONLY:
        from .csv_store import list_logs_csv
        recent = list_logs_csv(_CSV_PATH, direction="sent", order="DESC", limit=50)
        for r in recent:
            if (r.get("phone") == (phone or "") and
                r.get("message") == (message or "") and
                "ล้มเหลว" in (r.get("status") or "")):
                try:
                    last_dt = datetime.strptime(r.get("dt") or "", ISO_FMT)
                    if (_now() - last_dt).total_seconds() <= dedupe_seconds:
                        return False
                except Exception:
                    pass
        _mirror_csv("sent", phone or "Unknown", message or "", f"ล้มเหลว: {error_msg}", when)
        return True

    # SQLite: กันซ้ำในตาราง
    threshold_dt = datetime.strptime(when, ISO_FMT) - timedelta(seconds=dedupe_seconds)
    threshold = threshold_dt.strftime(ISO_FMT)
    sql_check = """
        SELECT id FROM sms_sent
         WHERE is_failed=1 AND phone=? AND message=? AND dt>=?
         ORDER BY id DESC LIMIT 1
    """
    with get_conn() as conn:
        found = conn.execute(sql_check, [phone, message, threshold]).fetchone()
        if found:
            return False

    _insert_sent(phone, message, f"ล้มเหลว: {error_msg}", when, is_failed=True, error_code=error_code)
    return True

# ============================================================
# Read APIs
# ============================================================
def list_logs(
    direction: Optional[str] = None,   # 'sent' | 'inbox' | None
    phone: Optional[str] = None,
    keyword: Optional[str] = None,
    since: Optional[Union[datetime, str]] = None,
    until: Optional[Union[datetime, str]] = None,
    limit: int = 500,
    offset: int = 0,
    order: str = "DESC",
) -> List[Dict[str, Any]]:

    # อ่านจาก CSV เมื่อเปิดสวิตช์
    if READ_FROM_CSV:
        from .csv_store import list_logs_csv, looks_failed
        rows = list_logs_csv(_CSV_PATH, direction=direction, phone=phone,
                             keyword=keyword, since=since, until=until,
                             limit=limit, offset=offset, order=order)
        # เติมคีย์ is_failed (คำนวณจาก status) เพื่อความเข้ากันได้กับ UI เดิม
        out: List[Dict[str, Any]] = []
        for r in rows:
            rr = dict(r)
            rr["is_failed"] = 1 if looks_failed(rr.get("status") or "") else 0
            out.append(rr)
        return out

    # อ่านจาก SQLite ปกติ
    conds: List[str] = []
    args: List[Any] = []
    if direction:
        conds.append("direction = ?"); args.append(direction)
    if phone:
        conds.append("phone LIKE ?");  args.append(f"%{phone}%")
    if keyword:
        conds.append("(message LIKE ? OR phone LIKE ?)"); args.extend([f"%{keyword}%", f"%{keyword}%"])
    if since:
        conds.append("dt >= ?");       args.append(_fmt_dt(since))
    if until:
        conds.append("dt <= ?");       args.append(_fmt_dt(until))

    where_sql = ("WHERE " + " AND ".join(conds)) if conds else ""
    order_sql = "DESC" if str(order).upper() == "DESC" else "ASC"

    sql_view = f"""
        SELECT id, dt, direction, phone, message, status, is_failed
          FROM sms_logs
          {where_sql}
         ORDER BY dt {order_sql}
         LIMIT ? OFFSET ?
    """
    args_with_page = args + [int(limit), int(offset)]

    with get_conn() as conn:
        try:
            rows = conn.execute(sql_view, args_with_page).fetchall()
        except Exception:
            # กรณีไม่มี view sms_logs ให้ union จาก 2 ตาราง
            sql_union = f"""
                SELECT id, dt, direction, phone, message, status, is_failed
                  FROM (
                        SELECT id, dt, 'sent'  AS direction, phone, message, status, is_failed FROM sms_sent
                        UNION ALL
                        SELECT id, dt, 'inbox' AS direction, phone, message, status, 0 AS is_failed FROM sms_inbox
                       ) AS all_logs
                  {where_sql}
                 ORDER BY dt {order_sql}
                 LIMIT ? OFFSET ?
            """
            rows = conn.execute(sql_union, args_with_page).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows or []:
        if hasattr(r, "keys"):
            out.append({k: r[k] for k in r.keys()})
        else:
            cols = ("id", "dt", "direction", "phone", "message", "status", "is_failed")
            out.append(dict(zip(cols, r)))
    return out

def count_inbox() -> int:
    if READ_FROM_CSV:
        from .csv_store import list_logs_csv
        return len(list_logs_csv(_CSV_PATH, direction="inbox", limit=10**9))
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM sms_inbox").fetchone()
        return int(row["c"] if hasattr(row, "keys") else row[0])

# ============================================================
# Delete APIs
# ============================================================
def delete_by_ids(direction, ids: Iterable[int]):
    if READ_FROM_CSV:
        from .csv_store import delete_by_ids_csv
        return delete_by_ids_csv(_CSV_PATH, ids)

    ids = [int(x) for x in ids if str(x).isdigit()]
    if not ids:
        return 0
    table = "sms_inbox" if direction == "inbox" else "sms_sent"
    placeholders = ",".join("?" for _ in ids)
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", ids)
        conn.commit()
    return len(ids)

def delete_all(direction=None, only_failed: bool = False):
    if READ_FROM_CSV:
        from .csv_store import delete_all_csv
        return delete_all_csv(_CSV_PATH, direction=direction, only_failed=only_failed)

    with get_conn() as conn:
        if direction == "inbox":
            conn.execute("DELETE FROM sms_inbox")
        elif direction == "sent":
            if only_failed:
                conn.execute("DELETE FROM sms_sent WHERE is_failed=1")
            else:
                conn.execute("DELETE FROM sms_sent")
        else:
            conn.execute("DELETE FROM sms_inbox")
            if only_failed:
                conn.execute("DELETE FROM sms_sent WHERE is_failed=1")
            else:
                conn.execute("DELETE FROM sms_sent")
        conn.commit()

def vacuum_db() -> None:
    """สำหรับ SQLite เท่านั้น (ไม่กระทบ CSV)"""
    with get_conn() as conn:
        conn.execute("VACUUM")
