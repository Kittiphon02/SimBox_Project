# services/csv_store.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Dict, Any, Optional
import csv
import os

# ฟอร์แมตใหม่: แยก date / time
CSV_FIELDS = ["id", "date", "time", "direction", "phone", "message", "status"]
ISO = "%Y-%m-%d %H:%M:%S"

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
        r["date"], r["time"] = d, t
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
    """
    เพิ่มแถวใหม่ (รองรับการส่ง dt มา—จะถูกแตกเป็น date/time ให้เอง)
    """
    _ensure_new_header(path)

    if (not date and not time) and dt:
        if isinstance(dt, datetime):
            dt = dt.strftime(ISO)
        date, time = _split_dt(dt)

    if not date or not time:
        now = datetime.now()
        date = date or now.strftime("%Y-%m-%d")
        time = time or now.strftime("%H:%M:%S")

    row = {
        "id": _next_id(path),
        "date": date,
        "time": time,
        "direction": direction,  # 'sent' | 'inbox'
        "phone": phone or "",
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

    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # ประกอบ dt กลับเพื่อใช้กรอง/เรียง
            dt_str = f"{r.get('date','')} {r.get('time','')}".strip()

            if direction and r.get("direction") != direction:
                continue
            if phone and phone not in (r.get("phone") or ""):
                continue
            if keyword:
                blob = (r.get("message") or "") + "|" + (r.get("phone") or "") + "|" + (r.get("status") or "")
                if keyword not in blob:
                    continue
            if since and dt_str < since:
                continue
            if until and dt_str > until:
                continue

            rr = dict(r)
            rr["dt"] = dt_str  # แนบให้เผื่อโค้ดฝั่ง UI ใช้
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
