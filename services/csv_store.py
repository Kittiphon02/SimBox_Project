# services/csv_store.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Dict, Any, Optional
import csv, os, re

# ฟอร์แมตใหม่: แยก date / time
CSV_FIELDS = ["id", "date", "time", "direction", "phone", "message", "status"]
ISO = "%Y-%m-%d %H:%M:%S"

def _normalize_phone_program(p: str) -> str:
    """ให้เบอร์เป็นรูปแบบโปรแกรม: 0xxxxxxxxx (10 หลัก), ไม่มีขีด/เว้นวรรค"""
    digits = re.sub(r"\D+", "", str(p or ""))
    if digits.startswith("66"):
        digits = "0" + digits[2:]
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits[:10] if len(digits) >= 10 else digits

def _format_date_program(date_str: str) -> str:
    """แปลง date ใด ๆ ให้เป็น DD/MM/YYYY"""
    s = (date_str or "").strip()
    if not s:
        return ""
    for pat in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            d = datetime.strptime(s, pat)
            return d.strftime("%d/%m/%Y")
        except Exception:
            pass
    return s

def _join_to_iso(date_str: str, time_str: str) -> str:
    """
    รวม date(โปรแกรม) + time ให้เป็น ISO 'YYYY-MM-DD HH:MM:SS'
    รองรับ time: HH:MM:SS / HH:MM / h:mm:ss AM/PM / h:mm AM/PM
    """
    dprog = _format_date_program(date_str)
    t = (time_str or "").strip()
    time_pats = ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p")
    for tp in time_pats:
        try:
            dd = datetime.strptime(dprog, "%d/%m/%Y")
            tt = datetime.strptime(t or "00:00:00", tp).time()
            return datetime.combine(dd.date(), tt).strftime(ISO)
        except Exception:
            continue
    try:
        dd = datetime.strptime(dprog, "%d/%m/%Y")
        return datetime(dd.year, dd.month, dd.day, 0, 0, 0).strftime(ISO)
    except Exception:
        return f"{date_str} {time_str}".strip()
    
# ----------------------- Utilities -----------------------
def looks_failed(status: str) -> bool:
    """บ่งชี้ว่าเป็นรายการส่งล้มเหลว (ใช้ตอนลบเฉพาะ Fail/แสดงสีแดง)"""
    FAIL_KEYWORDS = [
        "ล้มเหลว", "ส่งไม่สำเร็จ", "ผิดพลาด", "ขัดข้อง",
        "fail", "failed", "error", "timeout", "time out",
        "no route", "no service", "no sim", "no signal", "no network",
        "denied", "reject",
    ]
    s = (status or "").lower()
    return any(k in s for k in FAIL_KEYWORDS)

def _split_dt(s: str):
    """แยกสตริงวันเวลา → (date, time) รองรับ 'YYYY-MM-DD HH:MM:SS' และแบบ GSM 'DD/MM/YY,HH:MM:SS+zz'"""
    s = (str(s or "").strip().replace("T", " "))
    if "," in s:  # GSM
        dpart, tpart = s.split(",", 1)
        time_str = tpart.split("+", 1)[0].strip()
        dd, mm, yy = dpart.split("/")
        yyyy = 2000 + int(yy) if len(yy) == 2 else int(yy)
        dt = datetime(int(yyyy), int(mm), int(dd), *map(int, time_str.split(":")))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
    if " " in s:
        d, t = s.split(" ", 1)
        return d.strip(), t.strip()
    return s, ""

def _ensure_new_header(path: Path) -> None:
    """
    ให้ไฟล์ CSV ใช้หัวใหม่เสมอ (id,date,time,direction,phone,message,status)
    ถ้าพบหัวเก่า (มี 'dt') จะ migrate ทันที
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()
        return

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        fields = rdr.fieldnames or []
        if "dt" not in fields:
            return  # ใช้คอลัมน์ใหม่อยู่แล้ว
        rows = list(rdr)

    # แปลงทุกแถวจาก dt → date,time
    for r in rows:
        d, t = _split_dt(r.get("dt", ""))
        r["date"], r["time"] = _format_date_program(d), t
        r.pop("dt", None)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})

def _next_id(path: Path) -> int:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            last = None
            for last in reader:  # เดินไปหาแถวสุดท้าย
                pass
            return int(last["id"]) + 1 if last and last.get("id") else 1
    except Exception:
        return 1

# ----------------------- Write APIs -----------------------
def append_row(path: Path, *, direction: str, phone: str, message: str,
               status: str, date: Optional[str] = None, time: Optional[str] = None,
               dt: Optional[str | datetime] = None) -> None:
    
    _ensure_new_header(path)

    if (not date and not time) and dt:
        if isinstance(dt, datetime):
            date = dt.strftime("%d/%m/%Y")
            time = dt.strftime("%H:%M:%S")
        else:
            s = str(dt).replace("T", " ")
            try:
                dobj = datetime.strptime(s[:19], ISO)
                date = dobj.strftime("%d/%m/%Y")
                time = dobj.strftime("%H:%M:%S")
            except Exception:
                if " " in s:
                    dpart, tpart = s.split(" ", 1)
                    date = _format_date_program(dpart)
                    time = tpart.strip()

    # normalize อีกครั้ง (กรณีส่ง date/time มาเอง)
    date = _format_date_program(date or datetime.now().strftime("%Y-%m-%d"))
    try:
        time = datetime.strptime((time or "00:00:00"), "%H:%M:%S").strftime("%H:%M:%S")
    except Exception:
        time = "00:00:00"

    row = {
        "id": _next_id(path),
        "date": date,
        "time": time,
        "direction": direction,                # 'sent' | 'inbox'
        "phone": _normalize_phone_program(phone),
        "message": message or "",
        "status": status or "",
    }
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore").writerow(row)

# ----------------------- Read APIs -----------------------
def list_logs_csv(path: Path, *, direction: Optional[str] = None,
                  phone: Optional[str] = None, keyword: Optional[str] = None,
                  since: Optional[str | datetime] = None, until: Optional[str | datetime] = None,
                  limit: int = 500, offset: int = 0, order: str = "DESC") -> List[Dict[str, Any]]:
    _ensure_new_header(path)

    if isinstance(since, datetime): since = since.strftime(ISO)
    if isinstance(until, datetime): until = until.strftime(ISO)

    # ทำ query phone ให้เป็นรูปแบบโปรแกรม (ค้นหาแบบ contains ได้)
    q_phone_norm = _normalize_phone_program(phone) if phone else None

    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # normalize ตามรูปแบบโปรแกรมก่อน
            r_date  = _format_date_program(r.get("date", ""))
            r_time  = (r.get("time", "") or "").strip()
            r_phone = _normalize_phone_program(r.get("phone", ""))

            dt_str = _join_to_iso(r_date, r_time)

            if direction and r.get("direction") != direction:
                continue
            if q_phone_norm and q_phone_norm not in r_phone:
                continue
            if keyword:
                blob = (r.get("message") or "") + "|" + r_phone + "|" + (r.get("status") or "")
                if (keyword or "").strip() not in blob:
                    continue
            if since and dt_str < since:
                continue
            if until and dt_str > until:
                continue

            rr = dict(r)
            rr["date"]  = r_date          # DD/MM/YYYY
            rr["time"]  = r_time or "00:00:00"
            rr["phone"] = r_phone         # 0xxxxxxxxx
            rr["dt"]    = dt_str          # ISO (เผื่อโค้ด UI ใช้)
            rows.append(rr)

    rows.sort(key=lambda x: x.get("dt") or "", reverse=(str(order).upper() == "DESC"))
    if offset: rows = rows[offset:]
    if limit is not None: rows = rows[:limit]
    return rows

# ----------------------- Delete APIs -----------------------
def delete_by_ids_csv(path: Path, ids: Iterable[int]) -> int:
    _ensure_new_header(path)
    ids = {int(x) for x in ids}
    kept: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if int(r.get("id") or 0) not in ids:
                kept.append(r)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(kept)
    return len(ids)

def delete_all_csv(path: Path, *, direction: Optional[str] = None, only_failed: bool = False) -> int:
    """
    ลบทั้งไฟล์/ทั้งทิศทาง หรือเฉพาะรายการที่ 'เป็น Fail' (ดูจาก status)
    คืนค่าจำนวนที่พยายามลบ (ประมาณ)
    """
    _ensure_new_header(path)

    # ลบทั้งหมด (แบบเคลียร์ไฟล์)
    if direction is None and not only_failed:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()
        return 0

    kept: List[Dict[str, Any]] = []
    removed = 0
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if direction and r.get("direction") != direction:
                kept.append(r); continue
            if only_failed:
                if not looks_failed(r.get("status") or ""):
                    kept.append(r)
                else:
                    removed += 1
            else:
                removed += 1  # ลบทิ้งทั้ง direction นี้

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(kept)
    return removed
