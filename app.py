"""
Animal Intrusion Detection & Smart Farm Protection
Flask Backend Application with Multi-Device Real-Time Sync.

Architecture:
- Laptop 1 (Detection Station): Runs YOLOv8 inference on images, video files, or webcam.
- Laptop 2 (Farmer Portal): Connects via LAN (http://<local-ip>:5000/farmer), receives
  real-time Server-Sent Events (SSE), pops up an intrusion alert modal, and plays the alarm.
- Zero False Positives on Humans: Integrated COCO person rejection filter.
"""

import os
import cv2
import time
import base64
import socket
import queue
import json
import threading
from datetime import datetime
from collections import Counter
from functools import wraps
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, Response, send_from_directory, session
)

from db import init_db, insert_detection, get_detections, get_stats, clear_history, seed_demo_history
from detection import get_detector, get_detection_metrics
from analytics import estimate_crop_damage, get_damage_model_metrics, analyze_animal_activity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "audio"), exist_ok=True)

# Initialize database schema
init_db()

app = Flask(__name__)
app.secret_key = "smartfarm-secret-key-phase1-production-local"
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64MB cap
APP_PORT = int(os.environ.get("APP_PORT", "5002"))

# Demo Farmer Credentials
FARMER_USERNAME = "farmer"
FARMER_PASSWORD = "farmer123"

# Thread-safe webcam state
_webcam_lock = threading.Lock()
_webcam_state = {"active": False, "last_detection": None}

# Real-Time SSE Alert Broadcast Queue for Laptop 2
_alert_listeners = []
_listeners_lock = threading.Lock()


def get_local_ip() -> str:
    """Finds this machine's actual LAN IP address so Laptop 2 can connect over Wi-Fi."""
    advertised_host = os.environ.get("APP_ADVERTISE_HOST")
    if advertised_host:
        return advertised_host

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def broadcast_intrusion_alert(alert_payload: dict):
    """Pushes a new intrusion event in real-time to all connected Farmer accounts (Laptop 2)."""
    with _listeners_lock:
        for q in list(_alert_listeners):
            try:
                q.put_nowait(alert_payload)
            except Exception:
                pass


def encode_img_to_base64(img_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", img_bgr)
    if not ok:
        return ""
    b64 = base64.b64encode(buf).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def save_detection_snapshot(img_bgr, prefix="snap") -> str:
    """Saves an image snapshot to uploads directory and returns web URL."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp_str}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    cv2.imwrite(filepath, img_bgr)
    return f"/uploads/{filename}"


def farmer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("farmer_logged_in"):
            return redirect(url_for("farmer_login"))
        return f(*args, **kwargs)
    return decorated_function


# --------------------------------------------------------------------------
# Web Routes: Detection Station (Laptop 1)
# --------------------------------------------------------------------------
@app.route("/")
def index():
    stats = get_stats()
    recent = get_detections(limit=6)
    local_ip = get_local_ip()
    return render_template("index.html", stats=stats, recent_detections=recent, local_ip=local_ip)


@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/webcam")
def webcam_page():
    return render_template("webcam.html")


@app.route("/history")
def history_page():
    animal_filter = request.args.get("animal", "all")
    source_filter = request.args.get("source", "all")
    detections = get_detections(limit=100, animal_filter=animal_filter, source_filter=source_filter)
    return render_template(
        "history.html",
        detections=detections,
        current_animal=animal_filter,
        current_source=source_filter
    )


@app.route("/history/seed", methods=["POST"])
def seed_history_route():
    seed_demo_history()
    return redirect(url_for("history_page"))


@app.route("/history/clear", methods=["POST"])
def clear_history_route():
    clear_history()
    return redirect(url_for("history_page"))


@app.route("/dashboard")
def dashboard_page():
    all_detections = get_detections(limit=250)
    activity = analyze_animal_activity(all_detections)
    stats = get_stats()
    reg_metrics = get_damage_model_metrics()
    return render_template(
        "dashboard.html",
        activity=activity,
        stats=stats,
        reg_metrics=reg_metrics
    )


@app.route("/metrics")
def metrics_page():
    det_metrics = get_detection_metrics()
    reg_metrics = get_damage_model_metrics()
    return render_template(
        "metrics.html",
        det_metrics=det_metrics,
        reg_metrics=reg_metrics
    )


# --------------------------------------------------------------------------
# Farmer Account & Multi-Device Routes (Laptop 2)
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def farmer_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == FARMER_USERNAME and password == FARMER_PASSWORD:
            session["farmer_logged_in"] = True
            return redirect(url_for("farmer_dashboard"))
        error = "Invalid username or password. Use demo credentials: farmer / farmer123"
    return render_template("login.html", error=error)


@app.route("/logout")
def farmer_logout():
    session.clear()
    return redirect(url_for("farmer_login"))


@app.route("/farmer")
@farmer_login_required
def farmer_dashboard():
    stats = get_stats()
    detections = get_detections(limit=30)
    highest_id = detections[0]["id"] if detections else 0
    local_ip = get_local_ip()
    return render_template(
        "farmer.html",
        stats=stats,
        detections=detections,
        highest_id=highest_id,
        local_ip=local_ip,
        server_port=APP_PORT
    )


# --------------------------------------------------------------------------
# Real-Time SSE Alert Streaming (Zero-latency notification to Laptop 2)
# --------------------------------------------------------------------------
@app.route("/api/alerts/stream")
def api_alerts_stream():
    """Server-Sent Events endpoint pushing intrusion events instantly to Laptop 2."""
    def event_generator():
        client_q = queue.Queue(maxsize=30)
        with _listeners_lock:
            _alert_listeners.append(client_q)
        try:
            yield ": ping\n\n"
            while True:
                try:
                    alert_data = client_q.get(timeout=20)
                    yield f"data: {json.dumps(alert_data)}\n\n"
                except queue.Empty:
                    # Heartbeat
                    yield ": heartbeat\n\n"
        finally:
            with _listeners_lock:
                if client_q in _alert_listeners:
                    _alert_listeners.remove(client_q)

    return Response(event_generator(), mimetype="text/event-stream")


@app.route("/api/alerts/latest")
def api_alerts_latest():
    """Polling fallback for Farmer Dashboard."""
    since_id = int(request.args.get("since_id", 0))
    from db import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM detections WHERE id > ? ORDER BY id ASC LIMIT 15", (since_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# --------------------------------------------------------------------------
# API Routes: Detection & Processing on Laptop 1
# --------------------------------------------------------------------------
@app.route("/api/detect_image", methods=["POST"])
def api_detect_image():
    """Processes uploaded image, draws boxes, logs to DB, and broadcasts alert to Laptop 2."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    import numpy as np
    file_bytes = file.read()
    nparr = np.frombuffer(file_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify({"error": "Failed to decode image"}), 400

    detector = get_detector()
    annotated_img, detections, has_human = detector.detect(img_bgr)

    snapshot_url = None
    if detections:
        snapshot_url = save_detection_snapshot(annotated_img, prefix="img")

    processed_detections = []
    for d in detections:
        damage = estimate_crop_damage(d["animal"], count=1, duration_mins=15)
        row_id = insert_detection(
            animal=d["animal"],
            confidence=d["confidence"],
            est_damage=damage,
            source="image",
            thumbnail_path=snapshot_url,
            box_coords=d["box"]
        )

        # Broadcast real-time intrusion alert to Laptop 2!
        alert_payload = {
            "id": row_id,
            "animal": d["animal"],
            "confidence": d["confidence"],
            "est_damage": damage,
            "source": "image",
            "thumbnail_path": snapshot_url,
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        broadcast_intrusion_alert(alert_payload)

        processed_detections.append({
            "animal": d["animal"],
            "confidence": d["confidence"],
            "est_damage": damage,
            "box": d["box"]
        })

    return jsonify({
        "annotated_image": encode_img_to_base64(annotated_img),
        "detections": processed_detections,
        "has_human": has_human,
        "snapshot_url": snapshot_url
    })


@app.route("/api/detect_sample_image", methods=["POST"])
def api_detect_sample_image():
    """Runs detection on a sample image and broadcasts to Laptop 2."""
    filename = request.args.get("file", "elephant.jpg")
    safe_name = os.path.basename(filename)
    filepath = os.path.join(SAMPLE_DIR, safe_name)

    if not os.path.exists(filepath):
        return jsonify({"error": f"Sample file not found: {safe_name}"}), 404

    img_bgr = cv2.imread(filepath)
    if img_bgr is None:
        return jsonify({"error": "Failed to load sample image"}), 500

    detector = get_detector()
    annotated_img, detections, has_human = detector.detect(img_bgr)

    snapshot_url = f"/sample_data/{safe_name}"
    processed_detections = []
    for d in detections:
        damage = estimate_crop_damage(d["animal"], count=1, duration_mins=15)
        row_id = insert_detection(
            animal=d["animal"],
            confidence=d["confidence"],
            est_damage=damage,
            source="sample_image",
            thumbnail_path=snapshot_url,
            box_coords=d["box"]
        )

        # Broadcast alert to Laptop 2!
        alert_payload = {
            "id": row_id,
            "animal": d["animal"],
            "confidence": d["confidence"],
            "est_damage": damage,
            "source": "sample_image",
            "thumbnail_path": snapshot_url,
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        broadcast_intrusion_alert(alert_payload)

        processed_detections.append({
            "animal": d["animal"],
            "confidence": d["confidence"],
            "est_damage": damage,
            "box": d["box"]
        })

    return jsonify({
        "annotated_image": encode_img_to_base64(annotated_img),
        "detections": processed_detections,
        "has_human": has_human,
        "snapshot_url": snapshot_url
    })


@app.route("/api/detect_video", methods=["POST"])
def api_detect_video():
    """Processes uploaded video frame-by-frame and broadcasts detected intrusions to Laptop 2."""
    if "video" not in request.files:
        return jsonify({"error": "No video provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_DIR, filename)
    file.save(input_path)

    return _process_video_file(input_path, out_prefix=f"annotated_{filename}")


@app.route("/api/detect_demo_video", methods=["POST"])
def api_detect_demo_video():
    """One-click demo video runner broadcasting detections to Laptop 2."""
    demo_path = os.path.join(SAMPLE_DIR, "demo_intrusion.mp4")
    if not os.path.exists(demo_path):
        return jsonify({"error": "demo_intrusion.mp4 not found in sample_data"}), 404

    return _process_video_file(demo_path, out_prefix="demo_intrusion_annotated.mp4")


def _process_video_file(input_path: str, out_prefix: str):
    """Core video processing routine with native H.264 MP4 output and broadcast."""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return jsonify({"error": "Failed to open video file"}), 400

    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if not out_prefix.lower().endswith(".mp4"):
        out_prefix += ".mp4"
    out_filename = f"{int(time.time())}_{out_prefix}"
    output_path = os.path.join(UPLOAD_DIR, out_filename)

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    sample_every = max(1, total_frames // 120) if total_frames > 0 else 4

    detector = get_detector()
    all_detections = []
    frame_idx = 0
    logged_animals = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every == 0:
            annotated_frame, detections, _ = detector.detect(frame)
            writer.write(annotated_frame)

            for d in detections:
                all_detections.append(d)
                key = (d["animal"], frame_idx // (sample_every * 10))
                if key not in logged_animals:
                    logged_animals.add(key)
                    snap_url = save_detection_snapshot(annotated_frame, prefix="vid")
                    damage = estimate_crop_damage(d["animal"], count=1, duration_mins=20)
                    row_id = insert_detection(
                        animal=d["animal"],
                        confidence=d["confidence"],
                        est_damage=damage,
                        source="video",
                        thumbnail_path=snap_url,
                        box_coords=d["box"]
                    )
                    # Broadcast alert to Laptop 2
                    broadcast_intrusion_alert({
                        "id": row_id,
                        "animal": d["animal"],
                        "confidence": d["confidence"],
                        "est_damage": damage,
                        "source": "video",
                        "thumbnail_path": snap_url,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    })
        else:
            writer.write(frame)

        frame_idx += 1

    cap.release()
    writer.release()

    counts = Counter(d["animal"] for d in all_detections)
    return jsonify({
        "output_video": f"/uploads/{out_filename}",
        "total_detections": len(all_detections),
        "counts": dict(counts)
    })


# --------------------------------------------------------------------------
# Live Webcam Streaming
# --------------------------------------------------------------------------
@app.route("/api/webcam/<action>", methods=["POST"])
def webcam_control(action):
    global _webcam_state
    with _webcam_lock:
        if action == "start":
            test_cap = cv2.VideoCapture(0)
            if not test_cap.isOpened():
                test_cap.release()
                return jsonify({"available": False, "active": False})
            test_cap.release()
            _webcam_state["active"] = True
            return jsonify({"available": True, "active": True})
        else:
            _webcam_state["active"] = False
            return jsonify({"available": True, "active": False})


@app.route("/webcam_feed")
def webcam_feed():
    return Response(
        gen_webcam_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def gen_webcam_frames():
    global _webcam_state
    cap = cv2.VideoCapture(0)
    detector = get_detector()
    last_log_time = 0

    try:
        while True:
            with _webcam_lock:
                if not _webcam_state["active"]:
                    break

            ret, frame = cap.read()
            if not ret:
                break

            annotated_frame, detections, _ = detector.detect(frame)

            now = time.time()
            if detections and (now - last_log_time > 3.0):
                last_log_time = now
                primary = detections[0]
                snap_url = save_detection_snapshot(annotated_frame, prefix="cam")
                damage = estimate_crop_damage(primary["animal"], count=1, duration_mins=10)
                row_id = insert_detection(
                    animal=primary["animal"],
                    confidence=primary["confidence"],
                    est_damage=damage,
                    source="webcam",
                    thumbnail_path=snap_url,
                    box_coords=primary["box"]
                )
                alert_payload = {
                    "id": row_id,
                    "animal": primary["animal"],
                    "confidence": primary["confidence"],
                    "est_damage": damage,
                    "source": "webcam",
                    "thumbnail_path": snap_url,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
                with _webcam_lock:
                    _webcam_state["last_detection"] = alert_payload

                broadcast_intrusion_alert(alert_payload)

            ok, buffer = cv2.imencode(".jpg", annotated_frame)
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(0.04)
    finally:
        cap.release()


@app.route("/api/webcam_last_event")
def api_webcam_last_event():
    with _webcam_lock:
        return jsonify({"detection": _webcam_state.get("last_detection")})


@app.route("/api/estimate_damage")
def api_estimate_damage():
    animal = request.args.get("animal", "Elephant")
    count = int(request.args.get("count", 1))
    duration = int(request.args.get("duration", 20))
    loss = estimate_crop_damage(animal, count=count, duration_mins=duration)
    return jsonify({
        "animal": animal,
        "count": count,
        "duration_minutes": duration,
        "estimated_damage_inr": loss
    })


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/sample_data/<path:filename>")
def sample_file(filename):
    return send_from_directory(SAMPLE_DIR, filename)


# --------------------------------------------------------------------------
# Main Entrypoint: Bind to 0.0.0.0 for LAN Multi-Device Access
# --------------------------------------------------------------------------
if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 72)
    print(" SmartFarm AI — Animal Intrusion Detection & Crop Protection")
    print(" Multi-Device Real-Time Sync Station (Phase 1)")
    print(f" Detection Station (Laptop 1): http://127.0.0.1:{APP_PORT}/upload")
    print(f" Farmer Portal (Laptop 2):     http://{local_ip}:{APP_PORT}/login")
    print(" Login Credentials:            farmer / farmer123")
    print("=" * 72)
    app.run(host="0.0.0.0", port=APP_PORT, debug=False, threaded=True)