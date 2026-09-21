// SwasthyaAI beta — deterministic browser-only mood analyzer.
// This module keeps journal text in the browser and requires no API key.

const LOCAL_POSITIVE_WORDS = new Set([
  "happy", "joy", "joyful", "great", "good", "awesome", "amazing", "love",
  "loved", "grateful", "thankful", "calm", "peaceful", "relaxed", "excited",
  "hopeful", "proud", "content", "cheerful", "delighted", "fantastic",
  "wonderful", "better", "best", "smile", "laugh", "fun", "enjoy", "enjoyed",
  "refreshed", "energetic", "confident", "blessed", "glad", "nice",
]);

const LOCAL_NEGATIVE_WORDS = new Set([
  "sad", "angry", "anxious", "anxiety", "stressed", "stress", "depressed",
  "depression", "worried", "worry", "fear", "afraid", "scared", "frustrated",
  "frustrating", "annoyed", "annoying", "lonely", "alone", "tired", "exhausted",
  "overwhelmed", "hurt", "pain", "upset", "unhappy", "miserable", "cry",
  "crying", "hate", "hopeless", "helpless", "nervous", "panicked", "panic",
  "bad", "terrible", "awful", "horrible", "worst", "sick", "lost",
]);

const LOCAL_NEGATIONS = new Set([
  "not", "no", "never", "dont", "doesn't", "didnt", "cant", "cannot",
  "won't", "isnt", "aren't", "wasnt", "werent",
]);

const LOCAL_SUGGESTIONS = {
  positive: [
    "Keep the momentum — write down 3 things you're grateful for today. 🌞",
    "Share your good mood: reach out to someone you care about. 💛",
    "Channel this energy into a small goal you've been postponing. ✨",
  ],
  neutral: [
    "Take a mindful 2-minute break — focus only on your breath. 🌬️",
    "A short walk outside can lift an even mood into a good one. 🌿",
    "Try journaling one line about what you're feeling right now. 📓",
  ],
  negative: [
    "Be gentle with yourself — try a 5-minute guided breathing exercise. 🧘",
    "Step away from the screen and drink a glass of water. 💧",
    "Talk to someone you trust; you don't have to carry this alone. 🤝",
    "If these feelings persist, consider reaching out to a professional. 💚",
  ],
};

function analyzeLocally(text) {
  const words = (text.toLowerCase().match(/[a-z']+/g) || []);
  const phrases = words.slice(0, -1).map((word, index) => `${word} ${words[index + 1]}`);
  let positive = 0;
  let negative = 0;
  const consumed = new Set();

  phrases.forEach((phrase, index) => {
    if (!LOCAL_POSITIVE_WORDS.has(phrase) && !LOCAL_NEGATIVE_WORDS.has(phrase)) return;
    consumed.add(index);
    consumed.add(index + 1);
    const negated = index > 0 && LOCAL_NEGATIONS.has(words[index - 1]);
    if (LOCAL_POSITIVE_WORDS.has(phrase)) negated ? negative++ : positive++;
    if (LOCAL_NEGATIVE_WORDS.has(phrase)) negated ? positive++ : negative++;
  });

  words.forEach((word, index) => {
    if (consumed.has(index)) return;
    const negated = index > 0 && LOCAL_NEGATIONS.has(words[index - 1]);
    if (LOCAL_POSITIVE_WORDS.has(word)) negated ? negative++ : positive++;
    if (LOCAL_NEGATIVE_WORDS.has(word)) negated ? positive++ : negative++;
  });

  const total = positive + negative;
  const confidence = total ? Math.max(positive, negative) / total : 0.5;
  let sentiment = "neutral";
  if (positive > negative) sentiment = "positive";
  if (negative > positive) sentiment = "negative";

  let mood = 50;
  if (sentiment === "positive") mood = Math.round(78 + 17 * (confidence - 0.6) / 0.4);
  if (sentiment === "negative") mood = Math.round(22 - 17 * (confidence - 0.6) / 0.4);

  return {
    id: Date.now(),
    text,
    sentiment,
    mood: Math.max(5, Math.min(98, mood)),
    confidence: Number(confidence.toFixed(3)),
    engine: "local-browser",
    emoji: { positive: "😊", neutral: "😐", negative: "😔" }[sentiment],
    suggestions: LOCAL_SUGGESTIONS[sentiment],
    created_at: new Date().toISOString(),
  };
}
