# services/sms_log_store.py
from datetime import datetime, timedelta
from .db import get_conn

# --- เลือก collation ที่ “ปลอดภัย” สำหรับบังคับฝั่งคอลัมน์ตอนค้นหา ---
SAFE_COLLATIONS = {
    "utf8mb4_0900_ai_ci",      # ✅ MySQL 8
    "utf8mb4_unicode_ci",      # ✅ MariaDB/รุ่นเก่า
    "utf8mb4_unicode_520_ci",
    "utf8mb4_general_ci",
}

def _pick_session_collation():
    """ดึง collation ของ session; ถ้าไม่ได้ให้ fallback เป็น utf8mb4_unicode_ci"""
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT @@collation_connection AS c")
            row = cur.fetchone()
            c = None
            if isinstance(row, dict):
                c = (row.get("c") or row.get("COLLATION_CONNECTION") or "").strip()
            elif isinstance(row, (list, tuple)) and row:
                c = str(row[0]).strip()
            if c in SAFE_COLLATIONS:
                return c
    except Exception:
        pass
    return "utf8mb4_unicode_ci"

# ---------------------------------------------------------------------------

def _insert_sent(phone, message, status, dt=None, is_failed=False, error_code=None):
    when = (dt or datetime.now()).replace(microsecond=0)
    sql = """
        INSERT INTO sms_sent (phone, message, status, is_failed, error_code, dt)
        VALUES (%s,%s,%s,%s,%s,%s)
    """
    args = (phone, message, status, int(is_failed), error_code, when)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
        conn.commit()

def _insert_inbox(phone, message, status, dt=None):
    when = (dt or datetime.now()).replace(microsecond=0)
    sql = """
        INSERT INTO sms_inbox (phone, message, status, dt)
        VALUES (%s,%s,%s,%s)
    """
    args = (phone, message, status, when)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
        conn.commit()

def log_sms_sent(phone, message, status="ส่งสำเร็จ", dt=None):
    _insert_sent(phone, message, status, dt, is_failed=False)

def log_sms_inbox(phone, message, status="รับเข้า", dt=None):
    _insert_inbox(phone, message, status, dt)

def log_sms_failed(phone, message, error_msg, dt=None, error_code=None, dedupe_seconds=10):
    """
    บันทึกเคสส่งล้มเหลว โดย 'กันซ้ำ' ถ้ามีเรคอร์ด failed ของเบอร์+ข้อความเดียวกัน
    ภายใน dedupe_seconds วินาทีล่าสุด
    """
    when = (dt or datetime.now()).replace(microsecond=0)
    threshold = when - timedelta(seconds=dedupe_seconds)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM sms_sent
                 WHERE is_failed=1
                   AND phone=%s
                   AND message=%s
                   AND dt >= %s
                 ORDER BY id DESC
                 LIMIT 1
                """,
                (phone, message, threshold),
            )
            row = cur.fetchone()
            if row:
                # เพิ่งบันทึกไปแล้วในหน้าต่างเวลากันซ้ำ → ไม่ต้อง insert ซ้ำ
                return False

    _insert_sent(phone, message, f"ล้มเหลว: {error_msg}", when, is_failed=True, error_code=error_code)
    return True

# ---------------------------------------------------------------------------

def list_logs(direction=None, phone=None, keyword=None,
              since=None, until=None, limit=500, offset=0, order="DESC"):
    # เลือก collation ของ session (ต้องมี SAFE_COLLATIONS + _pick_session_collation() อยู่ในไฟล์นี้)
    coll = _pick_session_collation()

    # สร้างเงื่อนไขแบบไดนามิก
    conds = []
    params = {}

    if direction:
        conds.append("direction = %(direction)s")
        params["direction"] = direction

    # ✅ ใช้ LIKE และบังคับ COLLATE ที่ฝั่ง 'คอลัมน์'
    if phone:
        conds.append(f"phone COLLATE {coll} LIKE %(phone)s")
        params["phone"] = f"%{phone}%"

    if keyword:
        conds.append(
            f"""(
                   message COLLATE {coll} LIKE %(kw)s
                OR phone   COLLATE {coll} LIKE %(kw)s
               )"""
        )
        params["kw"] = f"%{keyword}%"

    if since:
        conds.append("dt >= %(since)s")
        params["since"] = since
    if until:
        conds.append("dt <= %(until)s")
        params["until"] = until

    where_sql = ("WHERE " + " AND ".join(conds)) if conds else ""
    order_sql = "DESC" if str(order).upper() == "DESC" else "ASC"

    # ✅ คงคอลัมน์เดิมให้ครบ (id, dt, direction, phone, message, status, is_failed)
    sql = f"""
        SELECT id, dt, direction, phone, message, status, is_failed
          FROM sms_logs
          {where_sql}
         ORDER BY dt {order_sql}
         LIMIT %(limit)s OFFSET %(offset)s
    """

    params["limit"] = int(limit)
    params["offset"] = int(offset)

    conn = get_conn()
    # ใช้ dict cursor ถ้ามี (เช่น mysql-connector) เพื่อให้ได้ dict ทันที
    try:
        cur = conn.cursor(dictionary=True)
    except TypeError:
        cur = conn.cursor()
    with cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    # ถ้าไม่ใช่ dict rows ให้แปลงเอง (กันไว้กรณีใช้ไลบรารีอื่น)
    if rows and not isinstance(rows[0], dict):
        cols = ("id", "dt", "direction", "phone", "message", "status", "is_failed")
        rows = [dict(zip(cols, r)) for r in rows]

    return rows

def count_inbox():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sms_inbox")
            row = cur.fetchone()
            return row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
