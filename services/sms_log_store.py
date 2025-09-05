# services/sms_log_store.py
from datetime import datetime, timedelta
from .db import get_conn

def _insert_sent(phone, message, status, dt=None, is_failed=False, error_code=None):
    when = (dt or datetime.now()).replace(microsecond=0)
    sql = """INSERT INTO sms_sent (phone, message, status, is_failed, error_code, dt)
             VALUES (%s,%s,%s,%s,%s,%s)"""
    args = (phone, message, status, int(is_failed), error_code, dt or datetime.now())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
        conn.commit()

def _insert_inbox(phone, message, status, dt=None):
    when = (dt or datetime.now()).replace(microsecond=0)
    sql = """INSERT INTO sms_inbox (phone, message, status, dt)
             VALUES (%s,%s,%s,%s)"""
    args = (phone, message, status, dt or datetime.now())
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
    ในช่วง dedupe_seconds วินาทีล่าสุดแล้ว
    """
    when = dt or datetime.now()
    threshold = when - timedelta(seconds=dedupe_seconds)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # เช็กว่ามีเรคอร์ด fail ที่เพิ่งเกิดไปแล้วหรือยัง (กันเด้งซ้ำ)
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
                # พบว่าเพิ่งบันทึกไปแล้วภายในหน้าต่างเวลา -> ไม่ต้อง insert ซ้ำ
                return False

    _insert_sent(phone, message, f"ล้มเหลว: {error_msg}", when, is_failed=True, error_code=error_code)
    return True

def list_logs(direction=None, phone=None, keyword=None,
              since=None, until=None, limit=500, offset=0, order="DESC"):
    cond, args = [], []
    if direction: cond.append("direction=%s"); args.append(direction)
    if phone:     cond.append("phone=%s");     args.append(phone)
    if keyword:   cond.append("message LIKE %s"); args.append(f"%{keyword}%")
    if since:     cond.append("dt >= %s");     args.append(since)
    if until:     cond.append("dt < %s");      args.append(until)
    where = ("WHERE " + " AND ".join(cond)) if cond else ""
    sql = f"""SELECT id, dt, direction, phone, message, status, is_failed
              FROM sms_logs {where}
              ORDER BY dt {order} LIMIT %s OFFSET %s"""
    args += [limit, offset]
    with get_conn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, args)
            return cur.fetchall()

def count_inbox():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sms_inbox")
            return cur.fetchone()[0]
