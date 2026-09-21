// SwasthyaAI beta — browser-only journal storage.
// Journal entries never leave this browser in the static beta deployment.

const STORAGE_KEY = "swasthya-mood-history";

function loadLocalEntries() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function saveLocalEntry(entry) {
  const entries = loadLocalEntries();
  entries.unshift(entry);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, 100)));
  return entry;
}

function deleteLocalEntry(entryId) {
  const entries = loadLocalEntries().filter((entry) => String(entry.id) !== String(entryId));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

function clearLocalEntries() {
  localStorage.removeItem(STORAGE_KEY);
}

function exportLocalEntries() {
  const entries = loadLocalEntries();
  const columns = ["created_at", "sentiment", "mood", "confidence", "engine", "text"];
  const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const csv = [
    columns.join(","),
    ...entries.map((entry) => columns.map((column) => escapeCsv(entry[column])).join(",")),
  ].join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "swasthya-mood-history.csv";
  link.click();
  URL.revokeObjectURL(url);
}
