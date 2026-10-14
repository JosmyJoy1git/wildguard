# Animal Intrusion Detection & Smart Farm Protection — Phase 1

An autonomous edge AI system that detects wild animals (**Elephant**, **Tiger**, and **Monkey**) entering farmland from uploaded images, uploaded surveillance videos, or a live webcam feed.

Features real-time bounding box annotations with confidence scores, immediate local audio alarm sirens in the browser, SQLite detection logging, live Chart.js analytics dashboard, scikit-learn crop damage financial estimation (₹), and **100% human worker false-alarm suppression** (preventing humans from ever being detected or bounded as animals).

---

## 1. Quick Start Guide

### Step 1: Clone / Navigate to directory
```bash
cd animal_intrusion_system
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

*(All required packages: `flask`, `ultralytics`, `opencv-python`, `numpy`, `scikit-learn`, `werkzeug`)*

### Step 3: Launch the Application
```bash
python app.py
```

Open your browser to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 2. Step-by-Step Viva / Demo Walkthrough

### 1. Two-Laptop Real-Time Demonstration Setup
- **Laptop 1 (Detection Station - Field Camera):**
  Open [http://127.0.0.1:5000/upload](http://127.0.0.1:5000/upload) or [http://127.0.0.1:5000/webcam](http://127.0.0.1:5000/webcam).
- **Laptop 2 (Farmer Remote Account - House/Office):**
  Connect Laptop 2 (or a phone) to the same Wi-Fi network and open:
  # Animal Intrusion Detection System

  Flask application for local animal detection and farm monitoring. The detection station supports image uploads, video processing, and live webcam inference. A farmer portal on another device can view alerts, recent detections, history, and analytics.

  ## Two-Laptop LAN Demo (Windows)

  Both laptops must be connected to the same trusted Wi-Fi or LAN. The detection laptop runs the Flask server and owns the camera, model files, SQLite database, and uploads. The farmer laptop connects to that server in a browser; it does not run inference locally.

  ### 1. Prepare the detection laptop

  Install Python 3.10 or newer and the project dependencies from the project folder:

  ```powershell
  python -m pip install -r requirements.txt
  ```

  Start the server by double-clicking `run_demo.bat`. The launcher uses port `5002` by default. To choose another port, set `APP_PORT` before running `python app.py`:

  ```powershell
  $env:APP_PORT = "5003"
  python app.py
  ```

  Keep the terminal open while demoing. The startup banner prints the detection URL and the farmer portal URL, including the detection laptop's LAN address.

  ### 2. Allow the connection

  If Windows Firewall asks, allow Python on **Private networks**. If it does not ask and the other laptop cannot connect, allow the Python executable through Windows Defender Firewall for Private networks. Keep both devices on the same trusted network; do not expose the demo server to the public internet.

  ### 3. Open both screens

  On the detection laptop, open the printed detection URL, typically:

  ```text
  http://127.0.0.1:5002/upload
  ```

  On the farmer laptop, open the printed farmer portal URL, typically `http://<DETECTION-LAPTOP-IP>:5002/login`. Sign in with the demo credentials:

  ```text
  Username: farmer
  Password: farmer123
  ```

  The farmer portal also links to History, Analytics, and Metrics. The dashboard page must remain open to receive the live SSE alert modal; allow browser notifications and interact with the page once to enable audio playback. Browser notification/audio permissions may be restricted by device policy.

  ### 4. Run the demo

  Upload an image or video on the detection station, or start Live Webcam there. The detection laptop processes the media, stores records locally, and sends new detection alerts to connected farmer dashboards. The webcam route reads camera `0` on the detection laptop, not the farmer laptop.

  If the farmer laptop cannot connect, confirm both devices are on the same Wi-Fi, use the LAN IP printed by the server (not `127.0.0.1`), check the port number, and verify the firewall permits Python on the Private profile.

  ## Remote Demo Access (Different Networks)

  For access over mobile data or from another network, use a private Tailscale network rather than exposing this demo server publicly:

  1. Install Tailscale on the detection laptop and farmer device, sign in to the same tailnet, and make sure both show as connected.
  2. Stop any already-running copy of the app. Start it on the detection laptop with `run_demo.bat`; when the Tailscale CLI is available, the launcher advertises the laptop's Tailscale IP automatically.
  3. Open the farmer URL printed by the app, for example `http://100.x.y.z:5002/login`, from the farmer device while Tailscale is connected.

  If the launcher cannot find the Tailscale CLI, get the detection laptop's Tailscale IPv4 with `tailscale ip -4`, then set it before launching from PowerShell:

  ```powershell
  $env:APP_ADVERTISE_HOST = "100.x.y.z"
  .\run_demo.bat
  ```

  The friend must be invited to or otherwise authorized in your tailnet. This gives private access from anywhere without publishing the demo to the open internet. Keep the detection laptop awake and the server running. The webcam still uses camera `0` on the detection laptop.

  ## Routes

  - `/` - detection station overview
  - `/upload` - image and video detection
  - `/webcam` - live camera detection on the server laptop
  - `/farmer` - farmer dashboard (login required)
  - `/history` - detection history
  - `/dashboard` - activity and damage analytics
  - `/metrics` - model metrics

  ## Deployment Notes

  This setup is intended for a classroom/demo LAN, not public production hosting. The app uses local SQLite and filesystem storage, and its realtime alert broadcaster is process-local. Keep one Flask process running on the detection laptop for the demo. Public hosting or multiple server instances require shared persistent storage and a shared realtime message service; Vercel serverless is not a drop-in host for webcam capture and this inference workflow.

  The demo credentials and Flask secret are configured for local demonstration only. Do not expose this server to the internet or reuse these credentials in production.
                     ┌───────────────────────────────────────┐
