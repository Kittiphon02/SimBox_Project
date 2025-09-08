# services/db.py
import os
import pymysql

# ===== 1) ค่าคอนฟิก DB (อ่านจาก ENV ถ้าไม่มีใช้ค่า default) =====
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "sim12345")
DB_NAME = os.getenv("DB_NAME", "sim_logs")

# ===== 2) ฟังก์ชันคืน connection =====
def get_conn():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,  # คืน row เป็น dict
    )
    # บังคับ collation ของ session ให้แมทช์กับที่เราใช้ใน query
    with conn.cursor() as cur:
        try:
            # MySQL 8
            cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cur.execute("SET collation_connection = 'utf8mb4_0900_ai_ci'")
        except Exception:
            # MariaDB / รุ่นเก่าที่ไม่มี 0900
            cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute("SET collation_connection = 'utf8mb4_unicode_ci'")
    return conn
