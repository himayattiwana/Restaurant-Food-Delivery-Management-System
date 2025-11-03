from db import get_conn

try:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok;")
            print(cur.fetchone())
    print("MySQL connection OK ✅")
except Exception as e:
    print("MySQL connection FAILED ❌:", e)
