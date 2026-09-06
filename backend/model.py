"""
SwasthyaAI — sentiment / mood analysis engine.

Primary path: a Hugging Face Transformers sentiment model (DistilBERT,
fine-tuned on SST-2). It is loaded lazily so importing this module never fails.

Fallback path: if `transformers`/`torch` aren't installed, or the model weights
can't be downloaded (offline), we use a lightweight lexicon scorer. The app
keeps working either way — the response includes `engine` so the UI can show
which one produced the result.
"""

from __future__ import annotations

import re
from typing import Dict, Any

# ── Lexicon fallback ────────────────────────────────────────────────────────
POSITIVE_WORDS = {
    "happy", "joy", "joyful", "great", "good", "awesome", "amazing", "love",
    "loved", "grateful", "thankful", "calm", "peaceful", "relaxed", "excited",
    "hopeful", "proud", "content", "cheerful", "delighted", "fantastic",
    "wonderful", "better", "best", "smile", "laugh", "fun", "enjoy", "enjoyed",
    "refreshed", "energetic", "confident", "blessed", "glad", "nice",
}
NEGATIVE_WORDS = {
    "sad", "angry", "anxious", "anxiety", "stressed", "stress", "depressed",
    "depression", "worried", "worry", "fear", "afraid", "scared", "frustrated",
    "frustrating", "annoyed", "annoying", "lonely", "alone", "tired", "exhausted",
    "overwhelmed", "hurt", "pain", "upset", "unhappy", "miserable", "cry",
    "crying", "hate", "hopeless", "helpless", "nervous", "panicked", "panic",
    "bad", "terrible", "awful", "horrible", "worst", "sick", "fed up", "lost",
}

# Simple negations flip the polarity of the word that follows.
NEGATIONS = {"not", "no", "never", "dont", "doesn't", "didnt", "cant",
             "cannot", "won't", "isnt", "aren't", "wasnt", "werent"}


def _lexicon_score(text: str) -> Dict[str, Any]:
    words = re.findall(r"[a-z']+", text.lower())
    pos = neg = 0
    for i, w in enumerate(words):
        # check for a negation in the previous token
        prev = words[i - 1] if i > 0 else ""
        weight = -1 if prev in NEGATIONS else 1
        if w in POSITIVE_WORDS:
            if weight == -1:
                neg += 1
            else:
                pos += 1
        elif w in NEGATIVE_WORDS:
            if weight == -1:
                pos += 1
            else:
                neg += 1

    total = pos + neg
    if total == 0:
        return {"label": "NEUTRAL", "score": 0.5}
    # confidence = share of the dominant polarity
    if pos >= neg:
        return {"label": "POSITIVE", "score": pos / total}
    return {"label": "NEGATIVE", "score": neg / total}


# ── Wellness mapping ────────────────────────────────────────────────────────
SUGGESTIONS = {
    "positive": [
        "Keep the momentum — write down 3 things you're grateful for today. 🌞",
        "Share your good mood: reach out to someone you care about. 💛",
        "Channel this energy into a small goal you've been postponing. ✨",
    ],
    "neutral": [
        "Take a mindful 2-minute break — focus only on your breath. 🌬️",
        "A short walk outside can lift an even mood into a good one. 🌿",
        "Try journaling one line about what you're feeling right now. 📓",
    ],
    "negative": [
        "Be gentle with yourself — try a 5-minute guided breathing exercise. 🧘",
        "Step away from the screen and drink a glass of water. 💧",
        "Talk to someone you trust; you don't have to carry this alone. 🤝",
        "If these feelings persist, consider reaching out to a professional. 💚",
    ],
}

EMOJI = {"positive": "😊", "neutral": "😐", "negative": "😔"}


class MoodAnalyzer:
    def __init__(self) -> None:
        self._pipeline = None
        self._tried = False
        self.engine = "lexicon"

    def _load_model(self) -> bool:
        """Lazily try to load the HF pipeline. Returns True on success."""
        if self._tried:
            return self._pipeline is not None
        self._tried = True
        try:
            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
            )
            self.engine = "huggingface"
            return True
        except Exception as exc:  # offline / not installed / weights missing
            print(f"[model] Hugging Face unavailable, using lexicon: {exc}")
            self._pipeline = None
            self.engine = "lexicon"
            return False

    def analyze(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"error": "empty text"}

        if self._load_model():
            try:
                out = self._pipeline(text[:512])[0]  # type: ignore
                raw_label = out["label"]
                conf = float(out["score"])
                label = "POSITIVE" if raw_label == "POSITIVE" else "NEGATIVE"
                score = conf
            except Exception as exc:
                print(f"[model] inference failed, falling back: {exc}")
                result = _lexicon_score(text)
                label, score = result["label"], result["score"]
                self.engine = "lexicon"
        else:
            result = _lexicon_score(text)
            label, score = result["label"], result["score"]

        # Map model confidence onto a 0–100 mood band. We don't use the raw
        # confidence directly (it's usually ~0.99) — we blend it so strong
        # signals land clearly but not at the absolute extremes.
        def _band(center: float, spread: float) -> int:
            return round(center + spread * (score - 0.6) / 0.4)

        if label == "POSITIVE":
            sentiment = "positive"
            mood = _band(78, 17)                   # ~70–95
        elif label == "NEGATIVE":
            sentiment = "negative"
            mood = _band(22, -17)                  # ~10–30
        else:
            sentiment = "neutral"
            mood = 50

        mood = max(5, min(98, mood))
        return {
            "sentiment": sentiment,
            "label": label,
            "confidence": round(score, 3),
            "mood": mood,
            "emoji": EMOJI[sentiment],
            "suggestions": SUGGESTIONS[sentiment],
            "engine": self.engine,
        }


analyzer = MoodAnalyzer()
