# services/db.py
import os, json, sys
from pathlib import Path
import pymysql

def _find_dbjson():
    cands = []
    # รันจาก source
    cands.append(Path(__file__).resolve().parents[1] / "windows" / "config" / "db.json")
    # รันเป็น .exe (PyInstaller one-file/one-folder)
    exe_dir = Path(getattr(sys, "frozen", False) and Path(sys.executable).resolve().parent or Path.cwd())
    cands.append(exe_dir / "windows" / "config" / "db.json")
    # ProgramData (เผื่อใช้กับ Installer)
    cands.append(Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Simbox" / "config" / "db.json")
    # โฟลเดอร์ทำงานปัจจุบัน
    cands.append(Path.cwd() / "windows" / "config" / "db.json")
    for p in cands:
        if p.exists(): return p
    return None

_cfg = {}
p = _find_dbjson()
if p:
    try: _cfg = json.loads(p.read_text(encoding="utf-8"))
    except Exception: _cfg = {}

DB_HOST = os.getenv("DB_HOST", _cfg.get("host", "127.0.0.1"))
DB_PORT = int(os.getenv("DB_PORT", _cfg.get("port", 3306)))
DB_USER = os.getenv("DB_USER", _cfg.get("user", "root"))
DB_PASS = os.getenv("DB_PASS", _cfg.get("password", "sim12345"))
DB_NAME = os.getenv("DB_NAME", _cfg.get("database", "sim_logs"))

def get_conn():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME, charset="utf8mb4",
        autocommit=True, cursorclass=pymysql.cursors.DictCursor)
