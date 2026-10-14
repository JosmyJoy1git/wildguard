"""
SQLite Database Access Layer
Stores all animal intrusion detections with timestamps, confidence scores,
crop damage estimates, and thumbnails.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "detections.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")


def get_db(db_path: str = None) -> sqlite3.Connection:
    target_path = db_path or DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None):
    conn = get_db(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()


def insert_detection(
    animal: str,
    confidence: float,
    est_damage: float,
    source: str,
    thumbnail_path: str = None,
    box_coords: list = None,
    custom_timestamp: datetime = None
) -> int:
    """Inserts a new intrusion detection record and returns the row id."""
    now = custom_timestamp or datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    timestamp_str = now.isoformat(timespec="seconds")
    box_json = json.dumps(box_coords) if box_coords else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections 
        (animal, confidence, est_damage, source, date, time, timestamp, thumbnail_path, box_coords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        animal.capitalize(),
        round(float(confidence), 3),
        round(float(est_damage), 2),
        source,
        date_str,
        time_str,
        timestamp_str,
        thumbnail_path,
        box_json
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_detections(
    limit: int = 100,
    animal_filter: str = None,
    source_filter: str = None
) -> list:
    """Retrieves detection records newest first, with optional animal and source filtering."""
    conn = get_db()
    query = "SELECT * FROM detections"
    params = []
    clauses = []

    if animal_filter and animal_filter.lower() != "all":
        clauses.append("LOWER(animal) = LOWER(?)")
        params.append(animal_filter)

    if source_filter and source_filter.lower() != "all":
        clauses.append("LOWER(source) = LOWER(?)")
        params.append(source_filter)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Calculates overall stats for dashboard cards."""
    conn = get_db()
    total_rows = conn.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(est_damage), 0) AS total_damage FROM detections").fetchone()
    total_count = total_rows["cnt"]
    total_damage = round(float(total_rows["total_damage"]), 2)

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_rows = conn.execute("SELECT COUNT(*) AS cnt FROM detections WHERE date = ?", (today_str,)).fetchone()
    today_count = today_rows["cnt"]

    # Animal counts
    animal_rows = conn.execute("SELECT animal, COUNT(*) as cnt FROM detections GROUP BY animal ORDER BY cnt DESC").fetchall()
    animal_counts = {r["animal"]: r["cnt"] for r in animal_rows}
    top_animal = animal_rows[0]["animal"] if animal_rows else "None"

    conn.close()
    return {
        "total_detections": total_count,
        "total_damage_inr": total_damage,
        "today_detections": today_count,
        "animal_counts": animal_counts,
        "top_animal": top_animal
    }


def clear_history():
    """Clears all records in the detections table."""
    conn = get_db()
    conn.execute("DELETE FROM detections")
    conn.commit()
    conn.close()


def seed_demo_history():
    """Seeds realistic intrusion records across the past 7 days for rich initial demo."""
    clear_history()
    now = datetime.now()
    animals_pool = [
        ("Elephant", 0.94, 4200.0, "image", "/sample_data/elephant.jpg"),
        ("Monkey", 0.91, 750.0, "video", "/sample_data/monkey.jpg"),
        ("Tiger", 0.88, 2100.0, "image", "/sample_data/tiger.jpg"),
        ("Elephant", 0.96, 5100.0, "video", "/sample_data/elephant.jpg"),
        ("Monkey", 0.89, 620.0, "image", "/sample_data/monkey.jpg"),
        ("Monkey", 0.93, 850.0, "video", "/sample_data/monkey.jpg"),
        ("Elephant", 0.95, 3800.0, "image", "/sample_data/elephant.jpg"),
        ("Tiger", 0.86, 1950.0, "video", "/sample_data/tiger.jpg"),
        ("Monkey", 0.92, 540.0, "webcam", "/sample_data/monkey.jpg"),
        ("Elephant", 0.92, 4600.0, "video", "/sample_data/elephant.jpg"),
    ]

    for i, (animal, conf, damage, src, thumb) in enumerate(animals_pool):
        days_ago = (10 - i) // 2
        hours_offset = (i * 3 + 2) % 24
        past_time = now - timedelta(days=days_ago)
        past_time = past_time.replace(hour=hours_offset, minute=random.randint(5, 55))
        insert_detection(
            animal=animal,
            confidence=conf,
            est_damage=damage,
            source=src,
            thumbnail_path=thumb,
            custom_timestamp=past_time
        )
