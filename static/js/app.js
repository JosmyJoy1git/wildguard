/**
 * Core frontend notifications for the intrusion detection UI.
 */

let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }

  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }

  return audioCtx;
}

document.addEventListener("click", () => {
  getAudioContext();
}, { once: false });

function playIntrusionAlarm(animalName = "Wild Animal", confidence = 0.9) {
  console.log("[ALARM] " + animalName + " detected (" + (confidence * 100).toFixed(0) + "%)");
  synthesizeNotificationTone();
  showToast("Alert: " + animalName + " detected near the field boundary", "alert-intrusion");
}

function synthesizeNotificationTone() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const notes = [
      { freq: 680, duration: 0.12 },
      { freq: 860, duration: 0.12 }
    ];

    notes.forEach((note, index) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const start = ctx.currentTime + (index * 0.16);

      osc.type = "triangle";
      osc.frequency.setValueAtTime(note.freq, start);

      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.05, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + note.duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(start);
      osc.stop(start + note.duration + 0.02);
    });
  } catch (error) {
    console.error("Notification sound failed:", error);
  }
}

function showToast(message, type = "normal") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast " + type;
  toast.innerHTML = "<div style=\"width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent);\"></div><div style=\"flex: 1;\"><div style=\"font-weight: 600; font-size: 0.88rem;\">" + message + "</div><div style=\"font-size: 0.75rem; color: #cbd5e1; margin-top: 2px;\">Local notification</div></div><button onclick=\"this.parentElement.remove()\" style=\"background:none;border:none;color:#94a3b8;cursor:pointer;font-size:1rem;\">&times;</button>";

  container.appendChild(toast);
  setTimeout(() => toast.remove(), 6000);
}
