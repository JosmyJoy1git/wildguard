-- Database Schema for Animal Intrusion Detection & Smart Farm Protection
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal TEXT NOT NULL,
    confidence REAL NOT NULL,
    est_damage REAL NOT NULL DEFAULT 0.0,
    source TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    thumbnail_path TEXT,
    box_coords TEXT
);

CREATE INDEX IF NOT EXISTS idx_detections_animal ON detections(animal);
CREATE INDEX IF NOT EXISTS idx_detections_date ON detections(date);
CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp);
