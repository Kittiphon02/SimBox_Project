# services/db.py
import os
from mysql.connector import pooling

DBCFG = {
    "host": os.getenv("DB_HOST", "localhost"),  # <- เปลี่ยนจาก 127.0.0.1 เป็น localhost
    "user": os.getenv("DB_USER", "app"),
    "password": os.getenv("DB_PASS", "apppass"),
    "database": os.getenv("DB_NAME", "sim_logs"),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
}

_pool = pooling.MySQLConnectionPool(pool_name="sim_pool", pool_size=5, **DBCFG)

def get_conn():
    return _pool.get_connection()
