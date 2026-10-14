"""
Animal Activity Analysis Module
Computes behavioral patterns:
1. Most active animal overall
2. Hourly activity distribution (time-of-day histogram: 00:00 to 23:00)
3. Weekly / daily trend
Includes graceful fallbacks when insufficient data is logged.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any


def analyze_animal_activity(detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes historical intrusion records and computes activity metrics.
    """
    total = len(detections)
    if total == 0:
        return {
            "has_data": False,
            "total_detections": 0,
            "most_active_animal": "None recorded",
            "most_active_hour_label": "N/A",
            "most_active_hour": None,
            "animal_distribution": {},
            "hourly_distribution": [0] * 24,
            "daily_trend": [],
            "risk_level": "Low",
            "message": "No animal intrusions logged yet. Upload an image or video to begin analysis."
        }

    # 1. Animal Distribution & Most Active Animal
    animal_counts = Counter(d["animal"].capitalize() for d in detections if d.get("animal"))
    most_active_animal = animal_counts.most_common(1)[0][0] if animal_counts else "None"

    # 2. Hourly Distribution (0 to 23)
    hourly_counts = [0] * 24
    for d in detections:
        ts = d.get("timestamp") or d.get("time")
        if ts:
            try:
                # Handle ISO format '2026-10-12T22:43:00' or '22:43:00' or standard timestamp
                if "T" in str(ts):
                    hour = datetime.fromisoformat(str(ts)).hour
                elif ":" in str(ts):
                    hour = int(str(ts).split(":")[0].split(" ")[-1])
                else:
                    hour = 12
                if 0 <= hour < 24:
                    hourly_counts[hour] += 1
            except Exception:
                continue

    peak_hour = int(max(range(24), key=lambda h: hourly_counts[h])) if sum(hourly_counts) > 0 else 12
    peak_hour_str = f"{peak_hour:02d}:00 - {(peak_hour + 1) % 24:02d}:00"

    # 3. Daily / Weekly Trend
    # Count occurrences per date 'YYYY-MM-DD'
    date_counter = Counter()
    for d in detections:
        date_val = d.get("date")
        if not date_val and d.get("timestamp"):
            date_val = str(d["timestamp"])[:10]
        if date_val:
            date_counter[str(date_val)] += 1

    # Sort dates chronologically
    sorted_dates = sorted(date_counter.keys())
    daily_trend = [{"date": dt, "count": date_counter[dt]} for dt in sorted_dates[-7:]]

    # Compute dynamic threat risk level based on frequency
    recent_count = len(detections[:15])
    if recent_count >= 10:
        risk_level = "High"
    elif recent_count >= 4:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    has_sufficient_data = total >= 3

    return {
        "has_data": True,
        "has_sufficient_data": has_sufficient_data,
        "total_detections": total,
        "most_active_animal": most_active_animal,
        "most_active_hour": peak_hour,
        "most_active_hour_label": peak_hour_str,
        "animal_distribution": dict(animal_counts),
        "hourly_distribution": hourly_counts,
        "daily_trend": daily_trend,
        "risk_level": risk_level,
        "message": "Sufficient history loaded." if has_sufficient_data else "Initial data logged; more samples will refine trends."
    }
