// SwasthyaAI — frontend logic

const $ = (id) => document.getElementById(id);
let chart = null;

const SENT_COLOR = { positive: "#2f9e6e", neutral: "#f2c14e", negative: "#e8836b" };
const MAX_JOURNAL_LENGTH = 2000;

function updateCharacterCount() {
  const journal = $("journal");
  const counter = $("charCount");
  if (!journal || !counter) return;
  counter.textContent = `${journal.value.length} / ${MAX_JOURNAL_LENGTH}`;
  counter.classList.toggle("text-danger", journal.value.length >= MAX_JOURNAL_LENGTH);
}

async function analyze() {
  const text = $("journal").value.trim();
  if (!text) { setStatus("Please write a few words about how you're feeling first.", "error"); return; }
  $("analyzeBtn").disabled = true;
  $("btnText").textContent = "Analyzing…";
  $("btnSpinner").classList.remove("d-none");
  try {
    const data = analyzeLocally(text);
    saveLocalEntry(data);
    renderResult(data);
    setStatus("Your reflection was analyzed locally in this browser.", "success");
    await loadHistory();
  } catch (err) { setStatus(err.message || "Unable to analyze this entry.", "error"); }
  finally {
    $("analyzeBtn").disabled = false;
    $("btnText").textContent = "Analyze my mood";
    $("btnSpinner").classList.add("d-none");
  }
}

function renderResult(d) {
  $("result").classList.remove("d-none");
  $("resultEmoji").textContent = d.emoji;
  $("resultSentiment").textContent = d.sentiment;
  $("resultSentiment").style.color = SENT_COLOR[d.sentiment] || "#1f7a53";
  $("moodValue").textContent = d.mood;
  const confidence = Number(d.confidence);
  $("confidenceValue").textContent = Number.isFinite(confidence)
    ? `analysis confidence ${Math.round(confidence * 100)}%`
    : "analysis confidence unavailable";

  requestAnimationFrame(() => { $("moodBar").style.width = d.mood + "%"; });

  const badge = $("engineBadge");
  badge.textContent = d.engine === "huggingface"
    ? "🧠 AI model (DistilBERT)"
    : "🧠 local sentiment engine";
  badge.classList.remove("d-none");

  // Suggestions come from an API response. Build text nodes instead of
  // injecting response content as HTML into the page.
  const suggestions = $("suggestions");
  suggestions.replaceChildren();
  (Array.isArray(d.suggestions) ? d.suggestions : []).forEach((suggestion) => {
    const item = document.createElement("li");
    item.textContent = suggestion;
    suggestions.appendChild(item);
  });
}

function exportHistory() {
  try {
    exportLocalEntries();
    setStatus("Mood history exported from this browser.", "success");
  } catch (e) {
    setStatus("Unable to export mood history.", "error");
  }
}

async function clearHistory() {
  if (!window.confirm("Delete all locally stored mood entries? This cannot be undone.")) return;
  clearLocalEntries();
  renderDashboard([]);
  setStatus("All local journal entries deleted.", "success");
}

async function deleteHistoryEntry(entryId) {
  if (!window.confirm("Delete this journal entry?")) return;
  deleteLocalEntry(entryId);
  setStatus("Journal entry deleted from this browser.", "success");
  await loadHistory();
}

async function loadHistory() {
  try { renderDashboard(loadLocalEntries()); }
  catch (e) { setStatus("Unable to load local mood history.", "error"); }
}

function renderDashboard(rows) {
  const ul = $("history");
  if (!rows.length) {
    ul.innerHTML = '<li class="empty">No entries yet — your reflections will appear here.</li>';
  } else {
    ul.innerHTML = rows.slice().reverse().map((r) => {
      const color = SENT_COLOR[r.sentiment] || "#999";
      const snippet = (r.text || "").slice(0, 60);
      return `<li>
        <span class="hist-dot" style="background:${color}"></span>
        <span class="hist-text">${escapeHtml(snippet)}</span>
        <span class="hist-mood">${r.mood}</span>
        <button class="delete-history-btn" type="button" data-entry-id="${r.id}" aria-label="Delete journal entry">×</button>
      </li>`;
    }).join("");
  }

  ul.querySelectorAll(".delete-history-btn").forEach((button) => {
    button.addEventListener("click", () => deleteHistoryEntry(button.dataset.entryId));
  });

  // stats
  $("statCount").textContent = rows.length;
  $("statStreak").textContent = rows.length ? rows[rows.length - 1].mood : "—";
  const avg = rows.length
    ? Math.round(rows.reduce((s, r) => s + r.mood, 0) / rows.length)
    : "—";
  $("statAvg").textContent = avg;

  drawChart(rows);
}

function drawChart(rows) {
  const wrap = document.querySelector(".chart-wrap");
  if (typeof Chart === "undefined" || !wrap) return;

  const labels = rows.map((r) => {
    const d = new Date(r.created_at);
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  });
  const data = rows.map((r) => r.mood);

  if (chart) chart.destroy();
  chart = new Chart($("moodChart"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        data,
        borderColor: "#2f9e6e",
        backgroundColor: "rgba(47,158,110,0.12)",
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: "#2f9e6e",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 100, ticks: { stepSize: 25 }, grid: { color: "rgba(0,0,0,0.05)" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function setStatus(message, tone = "success") {
  const status = $("appStatus");
  if (!status) return;
  status.textContent = message;
  status.className = `app-status ${tone}`;
}

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("analyzeBtn").addEventListener("click", analyze);
$("refreshBtn").addEventListener("click", loadHistory);
$("exportHistoryBtn").addEventListener("click", exportHistory);
$("clearHistoryBtn").addEventListener("click", clearHistory);
$("journal").addEventListener("input", updateCharacterCount);
updateCharacterCount();
loadHistory();
