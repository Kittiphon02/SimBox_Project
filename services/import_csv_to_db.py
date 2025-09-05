# import_csv_to_db.py
import csv
import os
from datetime import datetime
from typing import Optional
from services.db import get_conn

# ---------- Utilities ----------
def parse_dt_inbox(s: str) -> Optional[datetime]:
    # ตัวอย่างค่า: "03/07/2025,14:22:00+07"
    if not s:
        return None
    s = s.strip().strip('"')
    try:
        # แยกวันที่กับเวลา(+เขตเวลา)
        if ',' in s:
            d, t = s.split(',', 1)
        else:
            # fallback
            parts = s.split()
            d, t = parts[0], parts[1]
        t = t.replace('+07', '')  # ละเขตเวลา (local: Asia/Bangkok)
        return datetime.strptime(f"{d} {t}", "%d/%m/%Y %H:%M:%S")
    except Exception:
        try:
            # fallback format อื่น ๆ
            return datetime.fromisoformat(s.replace('+07',''))
        except Exception:
            return None

def parse_dt_sent(s: str) -> Optional[datetime]:
    # ตัวอย่างค่า: 2025-07-14 10:40:02
    if not s:
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

def norm(s: Optional[str]) -> str:
    return (s or "").strip()

def to_thai_status(status: str) -> str:
    # แปลง "Sent" -> "ส่งสำเร็จ" (ไม่บังคับ จะคงค่าเดิมก็ได้)
    if status.strip().lower() == "sent":
        return "ส่งสำเร็จ"
    return status

# ---------- Importers ----------
def insert_inbox_row(phone: str, message: str, status: str, dt_val: Optional[datetime]) -> bool:
    if dt_val is None:
        dt_val = datetime.now()
    with get_conn() as conn:
        with conn.cursor() as cur:
            # กันซ้ำ: ถ้ามี phone+message+dt ตรงกันแล้ว ให้ข้าม
            cur.execute(
                "SELECT 1 FROM sms_inbox WHERE phone=%s AND message=%s AND dt=%s LIMIT 1",
                (phone, message, dt_val)
            )
            if cur.fetchone():
                return False
            cur.execute(
                "INSERT INTO sms_inbox (phone, message, status, dt) VALUES (%s,%s,%s,%s)",
                (phone, message, status, dt_val)
            )
        conn.commit()
    return True

def insert_sent_row(phone: str, message: str, status: str, dt_val: Optional[datetime]) -> bool:
    if dt_val is None:
        dt_val = datetime.now()
    is_failed = 1 if status.startswith("ล้มเหลว") or status.lower().startswith("failed") else 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            # กันซ้ำ: ถ้ามี phone+message+dt+is_failed ตรงกันแล้ว ให้ข้าม
            cur.execute(
                """SELECT 1 FROM sms_sent
                   WHERE phone=%s AND message=%s AND dt=%s AND is_failed=%s
                   LIMIT 1""",
                (phone, message, dt_val, is_failed)
            )
            if cur.fetchone():
                return False
            cur.execute(
                """INSERT INTO sms_sent (phone, message, status, is_failed, error_code, dt)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (phone, message, status, is_failed, None, dt_val)
            )
        conn.commit()
    return True

def import_inbox_csv(path: str) -> dict:
    added = skipped = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            # --- เดิม: dt_val = parse_dt_inbox(...)
            dt_raw = norm(row.get("Received_Time"))
            dt_val = parse_dt_inbox(dt_raw) or datetime.now()
            dt_val = dt_val.replace(microsecond=0)   # << ตัดเศษวินาที

            phone  = norm(row.get("Sender"))         # หรือ clean_sender(...) ถ้าคุณใช้
            msg    = norm(row.get("Message"))
            status = norm(row.get("Status")) or "รับเข้า"

            if insert_inbox_row(phone, msg, status, dt_val):
                added += 1
            else:
                skipped += 1
    return {"added": added, "skipped": skipped}


def import_sent_csv(path: str) -> dict:
    added = skipped = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            dt_raw = norm(row.get("Datetime"))
            dt_val = parse_dt_sent(dt_raw) or datetime.now()
            dt_val = dt_val.replace(microsecond=0)   # << ตัดเศษวินาที

            phone  = norm(row.get("Phone"))
            msg    = norm(row.get("Message"))
            status = to_thai_status(norm(row.get("Status")) or "ส่งสำเร็จ")

            if insert_sent_row(phone, msg, status, dt_val):
                added += 1
            else:
                skipped += 1
    return {"added": added, "skipped": skipped}


# ---------- Main ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Import legacy CSV logs into MySQL")
    ap.add_argument("--inbox", help="Path to sms_inbox_log.csv", default="sms_inbox_log.csv")
    ap.add_argument("--sent",  help="Path to sms_sent_log.csv",  default="sms_sent_log.csv")
    args = ap.parse_args()

    if args.sent and os.path.exists(args.sent):
        r = import_sent_csv(args.sent)
        print(f"[SENT]   added={r['added']} skipped={r['skipped']}")
    else:
        print("[SENT]   file not found, skip")

    if args.inbox and os.path.exists(args.inbox):
        r = import_inbox_csv(args.inbox)
        print(f"[INBOX]  added={r['added']} skipped={r['skipped']}")
    else:
        print("[INBOX]  file not found, skip")

    print("DONE.")
