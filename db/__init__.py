
"""Database initialization and access package."""

from .database import (
    get_db,
    init_db,
    insert_detection,
    get_detections,
    get_stats,
    get_alerts_since,
    delete_detection,
    clear_history,
    seed_demo_history,
)
