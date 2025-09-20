# services/csv_store.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Dict, Any, Optional
import csv

# ไม่มีคอลัมน์ is_failed อีกต่อไป
FIELDS = ["id", "dt", "direction", "phone", "message", "status"]
ISO = "%Y-%m-%d %H:%M:%S"

# คำบ่งชี้ว่าเป็นรายการส่งล้มเหลว (ใช้ตอนลบเฉพาะ Fail)
FAIL_KEYWORDS = [
    "ล้มเหลว", "ส่งไม่สำเร็จ", "ผิดพลาด", "ขัดข้อง",
    "fail", "failed", "error", "timeout", "time out",
    "no route", "no service", "no sim", "no signal", "no network",
    "denied", "reject",
]
def looks_failed(status: str) -> bool:
    s = (status or "").lower()
    return any(k in s for k in FAIL_KEYWORDS)

def ensure_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()

def _next_id(path: Path) -> int:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            last = None
            for last in reader:
                pass
            return int(last["id"]) + 1 if last and last.get("id") else 1
    except Exception:
        return 1

def append_row(path: Path, *, direction: str, phone: str, message: str,
               status: str, dt: Optional[str | datetime] = None) -> None:
    ensure_csv(path)
    if isinstance(dt, datetime):
        dt = dt.strftime(ISO)
    if not dt:
        dt = datetime.now().strftime(ISO)
    row = {
        "id": _next_id(path),
        "dt": dt,
        "direction": direction,  # 'sent' | 'inbox'
        "phone": phone or "",
        "message": message or "",
        "status": status or "",
    }
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow(row)

def list_logs_csv(path: Path, *, direction: Optional[str] = None,
                  phone: Optional[str] = None, keyword: Optional[str] = None,
                  since: Optional[str | datetime] = None, until: Optional[str | datetime] = None,
                  limit: int = 500, offset: int = 0, order: str = "DESC") -> List[Dict[str, Any]]:
    ensure_csv(path)
    if isinstance(since, datetime): since = since.strftime(ISO)
    if isinstance(until, datetime): until = until.strftime(ISO)

    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if direction and r.get("direction") != direction:
                continue
            if phone and phone not in (r.get("phone") or ""):
                continue
            if keyword:
                blob = (r.get("message") or "") + "|" + (r.get("phone") or "") + "|" + (r.get("status") or "")
                if keyword not in blob:
                    continue
            dt = r.get("dt") or ""
            if since and dt < since:
                continue
            if until and dt > until:
                continue
            rows.append(r)

    rows.sort(key=lambda x: x.get("dt") or "", reverse=(str(order).upper() == "DESC"))
    if offset: rows = rows[offset:]
    if limit is not None: rows = rows[:limit]
    return rows

def delete_by_ids_csv(path: Path, ids: Iterable[int]) -> int:
    ensure_csv(path)
    ids = {int(x) for x in ids}
    kept: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if int(r.get("id") or 0) not in ids:
                kept.append(r)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept)
    return len(ids)

def delete_all_csv(path: Path, *, direction: Optional[str] = None, only_failed: bool = False) -> int:
    """ลบทั้งไฟล์/ทั้งทิศทาง หรือเฉพาะรายการที่ 'เป็น Fail' (ดูจาก status)"""
    ensure_csv(path)
    if direction is None and not only_failed:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()
        return 0

    kept: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if direction and r.get("direction") != direction:
                kept.append(r); continue
            if only_failed:
                if not looks_failed(r.get("status") or ""):
                    kept.append(r)
            # else: ลบทิ้งทั้ง direction นี้
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept)
    return 0
