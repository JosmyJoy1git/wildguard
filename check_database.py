
import sqlite3

connection = sqlite3.connect("db/detections.db")
cursor = connection.cursor()

tables = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Database tables:", tables)

for (table_name,) in tables:
    count = cursor.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()[0]
    print(f"{table_name}: {count} records")

connection.close()
