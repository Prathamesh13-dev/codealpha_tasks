# 🤖 FAQ Chatbot — Fullstack (Flask + HTML/CSS/JS)

A fullstack FAQ chatbot with NLP matching — runs entirely free, no API keys needed.

## Project Structure

```
faq-chatbot/
├── backend/
│   ├── app.py          ← Flask server (API routes)
│   └── nlp_engine.py   ← NLP preprocessing + TF-IDF matching
├── frontend/
│   ├── templates/
│   │   └── index.html  ← Main chat UI
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── requirements.txt
└── README.md
```

## Setup (VS Code)

### 1. Open project in VS Code
```bash
code faq-chatbot
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the server
```bash
python backend/app.py
```

### 5. Open the chatbot
Visit → **http://127.0.0.1:5000**

---

## VS Code Tip — Run with one click

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run FAQ Chatbot",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/app.py",
      "console": "integratedTerminal"
    }
  ]
}
```
Then press **F5** to start the server.

---

## Adding Your Own FAQs

Open `backend/nlp_engine.py` and add entries to `FAQ_DATA`:
```python
{
    "question": "What is your return policy?",
    "answer": "Items can be returned within 30 days with a receipt.",
    "category": "Support",
},
```

## How It Works

| Step | Tech |
|------|------|
| Preprocessing | NLTK tokenize → stopword removal → lemmatization |
| Vectorization | TF-IDF (scikit-learn) |
| Matching | Cosine similarity |
| Backend | Flask REST API |
| Frontend | Vanilla HTML + CSS + JS |
