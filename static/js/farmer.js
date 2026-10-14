/**
 * Farmer portal realtime alert handling.
 */

let isMuted = false;
let highestSeenId = 0;

document.addEventListener("DOMContentLoaded", () => {
  const metaEl = document.getElementById("farmer-meta");
  if (metaEl && metaEl.dataset.highestId) {
    highestSeenId = parseInt(metaEl.dataset.highestId, 10) || 0;
  }

  connectSSEStream();
  setInterval(pollLatestAlerts, 1500);

  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
});

function toggleAudioMute() {
  isMuted = !isMuted;
  const btn = document.getElementById("toggle-audio-btn");
  if (btn) {
    if (isMuted) {
      btn.textContent = "Audio: Off";
      btn.className = "btn btn-danger";
    } else {
      btn.textContent = "Audio: On";
      btn.className = "btn btn-secondary";
    }
  }
}

function dismissAlertModal() {
  const modal = document.getElementById("intrusion-alert-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

function triggerRealtimeFarmerAlert(alertData) {
  console.log("[ALERT]", alertData);

  if (!isMuted && typeof playIntrusionAlarm === "function") {
    playIntrusionAlarm(alertData.animal, alertData.confidence);
  }

  if ("Notification" in window && Notification.permission === "granted") {
    try {
      new Notification("Alert: Wild " + alertData.animal + " Detected", {
        body: "Confidence: " + (alertData.confidence * 100).toFixed(0) + "% | Estimated loss: ₹" + alertData.est_damage,
        icon: alertData.thumbnail_path || "/static/assets/icon.png"
      });
    } catch (e) {
      console.warn("Desktop notification error:", e);
    }
  }

  const modal = document.getElementById("intrusion-alert-modal");
  const imgEl = document.getElementById("modal-img-snapshot");
  const badgeEl = document.getElementById("modal-badge-animal");
  const confEl = document.getElementById("modal-txt-conf");
  const damageEl = document.getElementById("modal-txt-damage");
  const timeEl = document.getElementById("modal-txt-time");

  if (badgeEl) {
    badgeEl.textContent = alertData.animal;
    badgeEl.className = "badge " + alertData.animal.toLowerCase();
  }

  if (confEl) confEl.textContent = (alertData.confidence * 100).toFixed(1) + "%";
  if (damageEl) damageEl.textContent = "₹" + Number(alertData.est_damage).toLocaleString();
  if (timeEl) timeEl.textContent = (alertData.date || "") + " " + (alertData.time || alertData.timestamp || "Just now");

  if (imgEl) {
    if (alertData.thumbnail_path) {
      imgEl.src = alertData.thumbnail_path;
      imgEl.style.display = "block";
    } else {
      imgEl.style.display = "none";
    }
  }

  if (modal) modal.style.display = "flex";

  prependTableRow(alertData);

  const totalCountEl = document.getElementById("val-total-count");
  if (totalCountEl) {
    const cur = parseInt(totalCountEl.textContent.replace(/,/g, ""), 10) || 0;
    totalCountEl.textContent = cur + 1;
  }
}

function prependTableRow(d) {
  const tbody = document.getElementById("farmer-history-body");
  if (!tbody) return;

  if (document.getElementById("row-det-" + d.id)) return;

  const tr = document.createElement("tr");
  tr.id = "row-det-" + d.id;
  tr.style.background = "rgba(244, 63, 94, 0.12)";
  tr.style.transition = "background 2s ease";

  tr.innerHTML = "<td>" + (d.thumbnail_path ? "<img src=\"" + d.thumbnail_path + "\" class=\"table-thumb\" alt=\"" + d.animal + "\">" : '<div class="table-thumb no-img">No Image</div>') + "</td><td><span class=\"badge " + d.animal.toLowerCase() + "\">" + d.animal + "</span></td><td><span class=\"badge-confidence\">" + (d.confidence * 100).toFixed(1) + "%</span></td><td class=\"cell-damage\">₹" + Number(d.est_damage).toLocaleString() + "</td><td><span class=\"source-tag\">" + d.source + "</span></td><td class=\"cell-time\">" + (d.date || "") + " &bull; " + (d.time || d.timestamp || "Now") + "</td>";

  tbody.insertBefore(tr, tbody.firstChild);
  setTimeout(() => { tr.style.background = "transparent"; }, 4000);
}

function connectSSEStream() {
  const evtSource = new EventSource("/api/alerts/stream");

  evtSource.onmessage = function (event) {
    if (!event.data) return;
    try {
      const payload = JSON.parse(event.data);
      if (payload && payload.id && payload.id > highestSeenId) {
        highestSeenId = payload.id;
        triggerRealtimeFarmerAlert(payload);
      }
    } catch (e) {
      console.error("Error parsing SSE event:", e);
    }
  };

  evtSource.onerror = function () {
    const txt = document.getElementById("sync-status-txt");
    if (txt) {
      txt.textContent = "Reconnecting...";
      txt.parentElement.style.color = "var(--warning)";
    }
  };

  evtSource.onopen = function () {
    const txt = document.getElementById("sync-status-txt");
    if (txt) {
      txt.textContent = "Live Sync Active";
      txt.parentElement.style.color = "var(--accent)";
    }
  };
}

async function pollLatestAlerts() {
  try {
    const res = await fetch("/api/alerts/latest?since_id=" + highestSeenId);
    const list = await res.json();
    if (list && list.length > 0) {
      list.forEach((item) => {
        if (item.id > highestSeenId) {
          highestSeenId = item.id;
          triggerRealtimeFarmerAlert(item);
        }
      });
    }
  } catch (e) {}
}
