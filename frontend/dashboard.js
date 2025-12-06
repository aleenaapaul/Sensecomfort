// dashboard.js — robustized & corrected
// + Hide/Show Sensor Readings Toggle
// - Polls GET /latest every AUTO_MS
// - Renders probability, status, inferred days_left
// - Shows recent readings
// - Defensive DOM access; logs errors

let readingsVisible = true;

const LATEST_URL = '/latest';
const AUTO_MS = 6000;
const FORECAST_DAYS = 5; // future use
let lastData = null;

// Wait for DOM to be ready before wiring UI
document.addEventListener('DOMContentLoaded', () => {
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', fetchLatest);

  // ******** NEW: Toggle button wiring ********
  const toggleBtn = document.getElementById("toggleReadingsBtn");
  const readingsContainer = document.getElementById("sensorReadingsContainer");

  if (toggleBtn && readingsContainer) {
    toggleBtn.addEventListener("click", () => {
      readingsVisible = !readingsVisible;

      if (readingsVisible) {
        readingsContainer.style.display = "block";
        toggleBtn.innerText = "Hide";
      } else {
        readingsContainer.style.display = "none";
        toggleBtn.innerText = "Show";
      }
    });
  }
  // *******************************************

  // initial fetch + polling
  fetchLatest();
  setInterval(fetchLatest, AUTO_MS);
});

// Fetch latest prediction from backend
async function fetchLatest() {
  try {
    const resp = await fetch(LATEST_URL, { method: 'GET', cache: 'no-store' });
    if (resp.status === 204) {
      showWaiting();
      return;
    }
    if (!resp.ok) {
      const txt = await resp.text().catch(() => '');
      console.error('fetchLatest error status', resp.status, txt);
      showError(`Server ${resp.status}`);
      return;
    }
    const data = await resp.json();
    lastData = data;
    updateUI(data);
  } catch (err) {
    console.error('fetchLatest exception', err);
    showError('Server unreachable');
  }
}

// Show UI waiting state
function showWaiting() {
  const pt = document.getElementById('probText');
  const st = document.getElementById('statusText');
  const dt = document.getElementById('daysText');
  const container = document.getElementById('readingsList');
  if (pt) pt.innerText = '--%';
  if (st) st.innerText = 'Waiting for sensor...';
  if (dt) dt.innerText = '-- days';
  if (container) {
    container.innerHTML = `
      <div class="reading-item">
        <div class="reading-time">No readings yet</div>
      </div>`;
  }
}

// Show error message in status card
function showError(msg) {
  const st = document.getElementById('statusText');
  if (st) st.innerText = msg;
}

// Primary UI update — robust and with inferred days_left
function updateUI(data) {
  if (!data || typeof data !== 'object') {
    console.error('updateUI: invalid data', data);
    showWaiting();
    return;
  }

  // DOM references
  const probEl = document.getElementById('probText');
  const statusEl = document.getElementById('statusText');
  const daysEl = document.getElementById('daysText');
  const circleEl = document.getElementById('probCircle');
  const listEl = document.getElementById('readingsList');
  const readingsContainer = document.getElementById("sensorReadingsContainer");

  // Probability
  const rawProb = (data.probability != null && !isNaN(Number(data.probability)))
    ? Number(data.probability)
    : null;

  const percent = rawProb === null ? null : Math.round(rawProb * 100);
  if (probEl) probEl.innerText = percent === null ? '--%' : percent + '%';

  // Status
  if (statusEl) statusEl.innerText = data.status ?? '—';

  // Days-left: server > fallback inference
  let daysDisplay = '-- days';
  if (data.days_left !== null && data.days_left !== undefined) {
    daysDisplay = `${data.days_left} days`;
  } else if (rawProb !== null) {
    if (rawProb >= 0.95) daysDisplay = '0 days';
    else if (rawProb >= 0.75) daysDisplay = '1 day';
    else if (rawProb >= 0.60) daysDisplay = '2 days';
    else if (rawProb >= 0.40) daysDisplay = '3 days';
  }
  if (daysEl) daysEl.innerText = daysDisplay;

  // Circular progress
  if (circleEl) {
    const deg = percent === null ? 0 : Math.min(100, Math.max(0, percent)) * 3.6;
    circleEl.style.background =
      `conic-gradient(var(--accent) ${deg}deg, rgba(0,0,0,0.06) ${deg}deg)`;
  }

  // ******************** SENSOR READINGS LIST ********************
  if (listEl) {
    listEl.innerHTML = '';
    const history = Array.isArray(data.history) ? data.history.slice().reverse() : [];

    if (history.length === 0) {
      listEl.innerHTML = `
        <div class="reading-item">
          <div class="reading-time">No readings yet</div>
        </div>`;
    } else {
      const show = history.slice(0, 12);
      for (const h of show) {
        const item = document.createElement('div');
        item.className = 'reading-item';

        let t = '--';
        try { t = new Date(h.timestamp).toLocaleString(); }
        catch { t = String(h.timestamp || '--'); }

        const val = (h.resistance !== undefined && h.resistance !== null)
          ? String(h.resistance)
          : '--';

        item.innerHTML = `
          <div class="reading-time">${t}</div>
          <div class="reading-value">${val}</div>`;
        listEl.appendChild(item);
      }
    }
  }

  // Keep the hide/show state intact during auto-refresh
  if (readingsContainer) {
    readingsContainer.style.display = readingsVisible ? "block" : "none";
  }
  // ****************************************************************
}

// Optional manual trigger
window.refreshDashboard = fetchLatest;
