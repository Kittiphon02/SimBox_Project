# services/db.py
import os, json
from pathlib import Path
import pymysql

# ---- โหลด config จาก windows/config/db.json ถ้ามี (ENV จะ override ได้) ----
_cfg = {}
cfg_path = Path(__file__).resolve().parents[1] / "windows" / "config" / "db.json"
if cfg_path.exists():
    try:
        _cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        _cfg = {}

DB_HOST = os.getenv("DB_HOST", _cfg.get("host", "127.0.0.1"))
DB_PORT = int(os.getenv("DB_PORT", _cfg.get("port", 3306)))
DB_USER = os.getenv("DB_USER", _cfg.get("user", "root"))
DB_PASS = os.getenv("DB_PASS", _cfg.get("password", "sim12345"))
DB_NAME = os.getenv("DB_NAME", _cfg.get("database", "sim_logs"))

def get_conn():
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset="utf8mb4", autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    # บังคับ collation ของ session (รองรับ MySQL 8 / MariaDB)
    with conn.cursor() as cur:
        try:
            cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cur.execute("SET collation_connection = 'utf8mb4_0900_ai_ci'")
        except Exception:
            cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute("SET collation_connection = 'utf8mb4_unicode_ci'")
    return conn
