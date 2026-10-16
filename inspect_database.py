import sqlite3

connection = sqlite3.connect("db/detections.db")
cursor = connection.cursor()

columns = cursor.execute(
    "PRAGMA table_info(detections)"
).fetchall()

print("DETECTIONS TABLE COLUMNS:")
for column in columns:
    print(column[1], "-", column[2])

print("\nFIRST 3 DETECTION RECORDS:")
records = cursor.execute(
    "SELECT * FROM detections LIMIT 3"
).fetchall()

for record in records:
    print(record)

print("\nTOTAL RECORDS:")
print(cursor.execute(
    "SELECT COUNT(*) FROM detections"
).fetchone()[0])

connection.close()



