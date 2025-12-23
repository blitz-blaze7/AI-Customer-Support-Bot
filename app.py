import os
import json
import sqlite3
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

#Logging 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("support-bot")

#Paths 
HERE = os.path.dirname(__file__)               # folder containing app.py
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ENV_PATH = os.path.join(ROOT, ".env")          # .env at repo root
FAQ_PATH = os.path.join(HERE, "faqs.json")
DB_PATH = os.path.join(HERE, "chat_history.db")

# Load env
load_dotenv(dotenv_path=ENV_PATH)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.critical("GROQ_API_KEY not found in .env at project root.")
    raise ValueError("GROQ_API_KEY not found in .env")

# Groq client 
client = Groq(api_key=GROQ_API_KEY)

# Model(s) to try
MODEL_FALLBACKS = ["llama-3.1-8b-instant"]

#  Flask 
app = Flask(__name__)
CORS(app)

# DB helpers
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversations WHERE session_id=? ORDER BY id", (session_id,))
    rows = c.fetchall()
    conn.close()
    history = []
    for role, content in rows:
        history.append({"role": "assistant" if role == "assistant" else "user", "content": content})
    return history

# FAQ loader + matcher 
def load_faqs():
    try:
        with open(FAQ_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load faqs.json: %s", e)
        return []

    faqs = []
    if isinstance(data, list):
        for item in data:
            faqs.append({
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "tags": item.get("tags", []) or []
            })
    elif isinstance(data, dict):
        for k, v in data.items():
            faqs.append({
                "question": k.replace("_", " "),
                "answer": v,
                "tags": []
            })
    return faqs

FAQ_LIST = load_faqs()

def tokenize(text):
    return [w for w in ''.join(c if c.isalnum() else ' ' for c in (text or "").lower()).split() if len(w) > 1]

def find_relevant_faq(query, threshold=0.3):
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return None, 0.0
    best_score = 0.0
    best_faq = None
    for faq in FAQ_LIST:
        combined = (faq.get("question", "") + " " + faq.get("answer", "") + " " + " ".join(faq.get("tags", [])))
        tokens = set(tokenize(combined))
        if not tokens:
            continue
        score = len(q_tokens & tokens) / max(1, len(tokens))
        if score > best_score:
            best_score = score
            best_faq = faq
    if best_faq and best_score >= threshold:
        return best_faq.get("answer"), round(best_score, 3)
    return None, 0.0

#  Rule-based escalation 
ESCALATION_KEYWORDS = [
    "hack", "hacking", "illegal", "fraud", "steal", "breach",
    "attack", "exploit", "bomb", "terror", "kill"
]

def should_escalate(query: str) -> bool:
    if not query:
        return False
    q = query.lower()
    return any(k in q for k in ESCALATION_KEYWORDS)

# Routes 
@app.route("/", methods=["GET"])
def serve_ui():
   
    return send_from_directory(HERE, "test.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        session_id = data.get("session_id", "default")
        query = data.get("query")

        if not query:
            return jsonify({"error": "No query provided"}), 400

        # 1) rule-based escalation (deterministic)
        if should_escalate(query):
            message = "I cannot help with that. Connecting you to a human agent..."
            save_message(session_id, "user", query)
            save_message(session_id, "assistant", message)
            return jsonify({
                "response": message,
                "source": "rule-based",
                "action": "escalated",
                "session_id": session_id
            })

        # 2) try FAQ first (fast & deterministic)
        faq_answer, score = find_relevant_faq(query)
        if faq_answer:
            save_message(session_id, "user", query)
            save_message(session_id, "assistant", faq_answer)
            return jsonify({
                "response": faq_answer,
                "source": "faq",
                "match_score": score,
                "action": "responded",
                "session_id": session_id
            })

        # 3) fallback to LLM
        history = get_history(session_id)
        system_prompt = (
            "You are a helpful and concise customer support assistant. "
            "If the user's request is illegal, harmful, or requires human intervention, reply EXACTLY with the token: ESCALATE_TO_AGENT"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": query}
        ]

        last_error = None
        for model in MODEL_FALLBACKS:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0
                )
                # defensive parsing
                bot_reply = ""
                try:
                    bot_reply = resp.choices[0].message.content.strip()
                except Exception:
                    # fallback generic
                    try:
                        bot_reply = resp.choices[0].text.strip()
                    except Exception:
                        bot_reply = str(resp)[:1000]

                if "ESCALATE_TO_AGENT" in bot_reply:
                    final_reply = "I cannot help with that. Connecting you to a human agent..."
                    action = "escalated"
                else:
                    final_reply = bot_reply
                    action = "responded"

                save_message(session_id, "user", query)
                save_message(session_id, "assistant", final_reply)

                return jsonify({
                    "response": final_reply,
                    "source": f"llm:{model}",
                    "action": action,
                    "session_id": session_id
                })
            except Exception as e:
                logger.warning("Model %s failed: %s", model, e)
                last_error = str(e)
                continue

        # if no model succeeded
        return jsonify({"error": "AI backend failed", "detail": last_error}), 500

    except Exception as e:
        logger.exception("Unhandled error in /chat")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

@app.route("/history", methods=["GET"])
def history():
    session_id = request.args.get("session_id", "default")
    return jsonify(get_history(session_id))

@app.route("/clear_history", methods=["POST"])
def clear_history():
    data = request.json or {}
    session_id = data.get("session_id", "default")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"cleared": True, "session_id": session_id})

# Run
if __name__ == "__main__":
    app.run(debug=True, port=5000)
