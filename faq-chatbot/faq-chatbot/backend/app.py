"""
FAQ Chatbot Backend — Flask API
================================
Run: python backend/app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from nlp_engine import FAQEngine, FAQ_DATA

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "../frontend/static"),
    template_folder=os.path.join(os.path.dirname(__file__), "../frontend/templates"),
)
CORS(app)

# Boot the NLP engine once
print("🔧  Loading NLP engine…")
engine = FAQEngine(FAQ_DATA)
print(f"✅  {len(FAQ_DATA)} FAQs ready\n")


# ── Serve frontend ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    from flask import render_template
    return render_template("index.html")


# ── Chat API ──────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    query = (data.get("message") or "").strip()

    if not query:
        return jsonify({"error": "Empty message"}), 400

    result = engine.get_answer(query)

    # Initialize defaults
    answer = "No answer found."
    score = 0.0
    matched = "Unknown"

    # Case 1: The engine returned a simple string text answer
    if isinstance(result, str):
        answer = result
    
    # Case 2: The engine returned a list or tuple of values
    elif isinstance(result, (tuple, list)):
        if len(result) >= 1:
            answer = result[0]
        if len(result) >= 2:
            score = result[1]
        if len(result) >= 3:
            matched = result[2]

    # Return the clean structured response to your frontend
    return jsonify({
        "answer": answer,
        "score": round(float(score), 4) if score else 0.0,
        "matched_question": matched
    })



# ── FAQ list API ──────────────────────────────────────────────────────────────
@app.route("/api/faqs", methods=["GET"])
def list_faqs():
    return jsonify([
        {"id": i, "question": item["question"]}
        for i, item in enumerate(FAQ_DATA)
    ])


if __name__ == "__main__":
    print("🚀  FAQ Chatbot running → http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
