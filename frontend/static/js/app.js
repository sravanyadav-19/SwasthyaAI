// SwasthyaAI — frontend logic

const $ = (id) => document.getElementById(id);
let chart = null;

const SENT_COLOR = { positive: "#2f9e6e", neutral: "#f2c14e", negative: "#e8836b" };

async function analyze() {
  const text = $("journal").value.trim();
  if (!text) {
    alert("Please write a few words about how you're feeling first.");
    return;
  }

  $("analyzeBtn").disabled = true;
  $("btnText").textContent = "Analyzing…";
  $("btnSpinner").classList.remove("d-none");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    renderResult(data);
    loadHistory();
  } catch (err) {
    alert(err.message);
  } finally {
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

  requestAnimationFrame(() => { $("moodBar").style.width = d.mood + "%"; });

  const badge = $("engineBadge");
  badge.textContent = d.engine === "huggingface"
    ? "🧠 AI model (DistilBERT)"
    : "🧠 local sentiment engine";
  badge.classList.remove("d-none");

  $("suggestions").innerHTML = d.suggestions
    .map((s) => `<li>${s}</li>`)
    .join("");
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history?limit=30");
    const rows = await res.json();
    renderDashboard(rows.reverse()); // chronological for the chart
  } catch (e) {
    console.warn("history load failed", e);
  }
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
      </li>`;
    }).join("");
  }

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

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("analyzeBtn").addEventListener("click", analyze);
$("refreshBtn").addEventListener("click", loadHistory);
loadHistory();
