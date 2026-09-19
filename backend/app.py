"""
SwasthyaAI — Flask backend.

Serves the frontend and exposes a small JSON API:
  POST /api/analyze   { text: "..." }  -> sentiment analysis + saves entry
  GET  /api/history                      -> recent entries (for the dashboard)

Run:  python backend/app.py   (from the project root)
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, render_template, request

from model import analyzer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "swasthya.db")

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)


@app.after_request
def add_security_headers(response):
    """Keep private journal API responses out of browser/proxy caches."""
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ── Database ────────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    """Yield a SQLite connection and always release the file handle."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT NOT NULL,
                sentiment  TEXT NOT NULL,
                mood       INTEGER NOT NULL,
                confidence REAL,
                engine     TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Return a small readiness response without analyzing or storing text."""
    return jsonify({
        "status": "ok",
        "service": "SwasthyaAI",
        "analyzer_engine": analyzer.engine,
        "database": "sqlite",
    })


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Please write something about how you're feeling."}), 400
    if len(text) > 2000:
        return jsonify({"error": "Entry is too long (2000 characters max)."}), 400

    result = analyzer.analyze(text)
    if "error" in result:
        return jsonify(result), 400

    created = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO entries (text, sentiment, mood, confidence, engine, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (text, result["sentiment"], result["mood"],
             result["confidence"], result["engine"], created),
        )
        result["id"] = cur.lastrowid
        result["created_at"] = created

    return jsonify(result)


@app.route("/api/history/export")
def export_history():
    """Export local mood history as a portable CSV file."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT created_at, sentiment, mood, confidence, engine, text "
            "FROM entries ORDER BY id ASC"
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "sentiment", "mood", "confidence", "engine", "text"])
    writer.writerows(
        (row["created_at"], row["sentiment"], row["mood"], row["confidence"], row["engine"], row["text"])
        for row in rows
    )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=swasthya-mood-history.csv"},
    )


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """Delete all locally stored journal entries when the user requests it."""
    with get_db() as conn:
        deleted = conn.execute("DELETE FROM entries").rowcount
    return jsonify({"deleted": deleted})


@app.route("/api/history/<int:entry_id>", methods=["DELETE"])
def delete_history_entry(entry_id: int):
    """Delete one local journal entry without disturbing the rest of history."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Journal entry not found."}), 404
    return jsonify({"deleted": entry_id})


@app.route("/api/history")
def history():
    # Bound history reads so an invalid or huge query cannot crash the route
    # or request an unnecessary amount of private journal data.
    raw_limit = request.args.get("limit", "30")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be a whole number between 1 and 100."}), 400
    if not 1 <= limit <= 100:
        return jsonify({"error": "limit must be a whole number between 1 and 100."}), 400

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, text, sentiment, mood, confidence, engine, created_at "
            "FROM entries ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    print("🪷  SwasthyaAI running at http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
