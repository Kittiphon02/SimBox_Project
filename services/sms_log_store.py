# services/sms_log_store.py
# ------------------------------------------------------------
# จัดการบันทึก/อ่าน LOG ของ SMS สำหรับ SQLite (ฐานข้อมูลฝังในโฟลเดอร์เดียวกับโปรแกรม)
# ใช้ร่วมกับ services/db.py (get_conn() -> sqlite3.Connection ที่ตั้ง row_factory เป็น sqlite3.Row)
# ------------------------------------------------------------
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Iterable
from .db import get_conn

ISO_FMT = "%Y-%m-%d %H:%M:%S"


def _now() -> datetime:
    """คืนเวลาปัจจุบันแบบตัด microsecond ทิ้ง เพื่อความสวยงาม/คงที่ในการเปรียบเทียบ"""
    return datetime.now().replace(microsecond=0)


def _fmt_dt(dt: Optional[Union[datetime, str]]) -> str:
    """แปลง datetime/str ให้เป็นสตริง ISO 'YYYY-MM-DD HH:MM:SS' สำหรับเก็บและเปรียบเทียบแบบ lexicographic"""
    if isinstance(dt, str):
        # สมมติว่าผู้เรียกส่งมาเป็นฟอร์แมตถูกต้องแล้ว
        return dt
    return (dt or _now()).strftime(ISO_FMT)


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
        _fmt_dt(dt),
    ]
    with get_conn() as conn:
        conn.execute(sql, args)
        conn.commit()


def _insert_inbox(
    phone: str,
    message: str,
    status: str,
    dt: Optional[Union[datetime, str]] = None,
) -> None:
    sql = """
        INSERT INTO sms_inbox (phone, message, status, dt)
        VALUES (?,?,?,?)
    """
    args = [phone or "Unknown", message or "", status or "รับเข้า", _fmt_dt(dt)]
    with get_conn() as conn:
        conn.execute(sql, args)
        conn.commit()


# ============================================================
# Public write APIs (คงชื่อเดิมเพื่อไม่ให้ UI/ส่วนอื่นพัง)
# ============================================================
def log_sms_sent(phone, message, status="ส่งสำเร็จ", dt=None):
    """บันทึก SMS ที่ส่งออก (สำเร็จ)"""
    _insert_sent(phone, message, status, dt, is_failed=False)


def log_sms_inbox(phone, message, status="รับเข้า", dt=None):
    """บันทึก SMS ขาเข้า (รับสำเร็จ)"""
    _insert_inbox(phone, message, status, dt)


def log_sms_failed(phone, message, error_msg, dt=None, error_code=None, dedupe_seconds=10):
    """
    บันทึกเคสส่งล้มเหลว โดย 'กันซ้ำ' ถ้าเพิ่งมีเรคอร์ด failed ของ (เบอร์+ข้อความ) เดียวกัน
    ในช่วง dedupe_seconds วินาทีล่าสุด
    """
    when = _fmt_dt(dt)
    threshold_dt = datetime.strptime(when, ISO_FMT) - timedelta(seconds=dedupe_seconds)
    threshold = threshold_dt.strftime(ISO_FMT)

    sql_check = """
        SELECT id
          FROM sms_sent
         WHERE is_failed=1
           AND phone=?
           AND message=?
           AND dt >= ?
         ORDER BY id DESC
         LIMIT 1
    """
    with get_conn() as conn:
        found = conn.execute(sql_check, [phone, message, threshold]).fetchone()
        if found:
            return False  # ซ้ำภายในหน้าต่างเวลา → ไม่บันทึกซ้ำ

    _insert_sent(phone, message, f"ล้มเหลว: {error_msg}", when, is_failed=True, error_code=error_code)
    return True


# ============================================================
# Read APIs
# ============================================================
def list_logs(
    direction: Optional[str] = None,   # 'sent' | 'inbox' | None = ทั้งหมด
    phone: Optional[str] = None,
    keyword: Optional[str] = None,
    since: Optional[Union[datetime, str]] = None,
    until: Optional[Union[datetime, str]] = None,
    limit: int = 500,
    offset: int = 0,
    order: str = "DESC",               # 'ASC' | 'DESC'
) -> List[Dict[str, Any]]:

    conds: List[str] = []
    args: List[Any] = []

    if direction:
        conds.append("direction = ?")
        args.append(direction)

    if phone:
        conds.append("phone LIKE ?")
        args.append(f"%{phone}%")

    if keyword:
        conds.append("(message LIKE ? OR phone LIKE ?)")
        args.extend([f"%{keyword}%", f"%{keyword}%"])

    if since:
        conds.append("dt >= ?")
        args.append(_fmt_dt(since))

    if until:
        conds.append("dt <= ?")
        args.append(_fmt_dt(until))

    where_sql = ("WHERE " + " AND ".join(conds)) if conds else ""
    order_sql = "DESC" if str(order).upper() == "DESC" else "ASC"

    # ปกติอ่านจาก view sms_logs (ถูกสร้างตอน init ใน services/db.py)
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
            # เผื่อเครื่องที่ view ยังไม่ถูกสร้าง: รวม 2 ตารางด้วย subquery แทน
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

    # แปลงเป็น list[dict]
    out: List[Dict[str, Any]] = []
    for r in rows or []:
        if hasattr(r, "keys"):
            out.append({k: r[k] for k in r.keys()})
        else:
            cols = ("id", "dt", "direction", "phone", "message", "status", "is_failed")
            out.append(dict(zip(cols, r)))
    return out


def count_inbox() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM sms_inbox").fetchone()
        if not row:
            return 0
        if hasattr(row, "keys"):
            return int(row["c"])
        return int(row[0])

def delete_by_ids(direction: str, ids: Iterable[int]) -> int:
    """
    ลบตาม id ที่ระบุ
    direction: 'inbox' หรือ 'sent'
    return: จำนวนที่ตั้งใจลบ (ประมาณการ)
    """
    ids = [int(x) for x in ids if str(x).isdigit()]
    if not ids:
        return 0
    table = "sms_inbox" if direction == "inbox" else "sms_sent"
    placeholders = ",".join("?" for _ in ids)
    sql = f"DELETE FROM {table} WHERE id IN ({placeholders})"
    with get_conn() as conn:
        conn.execute(sql, ids)
        conn.commit()
    return len(ids)

def delete_all(direction: str | None = None, only_failed: bool = False) -> int:
    """
    ลบทั้งหมด
    direction=None  → ทั้ง inbox และ sent
    direction='inbox' → เฉพาะ inbox
    direction='sent'  → เฉพาะ sent (ถ้า only_failed=True จะลบเฉพาะแถวที่ fail)
    """
    with get_conn() as conn:
        if direction == "inbox":
            cur = conn.execute("DELETE FROM sms_inbox")
            conn.commit()
            return cur.rowcount if cur.rowcount is not None else 0

        if direction == "sent":
            if only_failed:
                cur = conn.execute("DELETE FROM sms_sent WHERE is_failed=1")
            else:
                cur = conn.execute("DELETE FROM sms_sent")
            conn.commit()
            return cur.rowcount if cur.rowcount is not None else 0

        # ลบทั้งสองตาราง
        conn.execute("DELETE FROM sms_inbox")
        if only_failed:
            conn.execute("DELETE FROM sms_sent WHERE is_failed=1")
        else:
            conn.execute("DELETE FROM sms_sent")
        conn.commit()
        return 0

def vacuum_db() -> None:
    """จัดระเบียบไฟล์ DB หลังลบข้อมูลจำนวนมาก (optional)"""
    with get_conn() as conn:
        conn.execute("VACUUM")