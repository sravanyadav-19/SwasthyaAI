"""
SwasthyaAI — Flask backend.

Serves the frontend and exposes a small JSON API:
  POST /api/analyze   { text: "..." }  -> sentiment analysis + saves entry
  GET  /api/history                      -> recent entries (for the dashboard)

Run:  python backend/app.py   (from the project root)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

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


# ── Database ────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


@app.route("/api/history")
def history():
    limit = min(int(request.args.get("limit", 30)), 100)
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
