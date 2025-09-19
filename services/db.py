# services/db.py  (SQLite, auto-create .db ข้างๆ ตัวโปรแกรม)
import sys
from pathlib import Path
import sqlite3

def _app_dir():
    # โหมด .exe (PyInstaller) → โฟลเดอร์เดียวกับไฟล์ .exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # โหมดรันจากซอร์ส → โฟลเดอร์รากโปรเจกต์ (พาเรนต์ของ /services)
    return Path(__file__).resolve().parents[1]

DB_PATH = _app_dir() / "sim_logs.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # ให้ได้ dict-like rows
    return conn

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        # กล่องส่งออก
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                message TEXT,
                status TEXT,
                is_failed INTEGER DEFAULT 0,
                error_code TEXT,
                dt TEXT
            )
        """)
        # กล่องรับเข้า
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_inbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                message TEXT,
                status TEXT,
                dt TEXT
            )
        """)
        # มุมมองรวม
        c.execute("""
            CREATE VIEW IF NOT EXISTS sms_logs AS
            SELECT id, dt, 'sent'  AS direction, phone, message, status, is_failed FROM sms_sent
            UNION ALL
            SELECT id, dt, 'inbox' AS direction, phone, message, status, 0 AS is_failed FROM sms_inbox
        """)
        conn.commit()

# สร้างฐานข้อมูล/ตารางทันทีเมื่อ import
init_db()
