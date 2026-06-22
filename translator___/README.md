# Language Translator

A free, web-based language translation app using the free Google Translate web endpoint (via `deep-translator`). **No API key. No billing. No account needed.**

**Stack:** Python · Flask · Vanilla JS · HTML/CSS

---

## Quick Start (Local)

### 1. Unzip and enter the project folder

```bash
cd translator
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows (PowerShell/cmd)
source venv/Scripts/activate    # Windows (Git Bash)
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

Open http://localhost:5000 in your browser. That's it — no API key setup required.

---

## Run with Docker (optional)

```bash
docker-compose up
```

or manually:

```bash
docker build -t translator .
docker run -p 5000:5000 translator
```

---

## Deploy

No API key/secrets needed for any of these — just deploy the code.

### Render (free tier)
1. Push to GitHub
2. Create a new **Web Service** on https://render.com
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`

### Railway
1. Push to GitHub
2. New project → Deploy from GitHub repo
3. Railway auto-detects the `Procfile`

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

### Fly.io
```bash
fly launch
fly deploy
```

---

## Project Structure

```
translator/
├── app.py                  # Flask backend + API routes
├── requirements.txt        # Python dependencies
├── Procfile                # For Heroku / Render
├── Dockerfile               # Container image
├── docker-compose.yml       # Local Docker dev
├── templates/
│   └── index.html          # Main HTML page (Jinja2)
└── static/
    ├── css/
    │   └── style.css       # All styles (light + dark mode)
    └── js/
        └── app.js          # Frontend logic
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the UI |
| POST | `/translate` | Translates text |
| GET | `/languages` | Returns supported languages |
| GET | `/health` | Health check |

### POST /translate

**Request body:**
```json
{
  "text": "Hello, how are you?",
  "source_language": "English",
  "target_language": "French"
}
```

**Response:**
```json
{
  "translation": "Bonjour, comment allez-vous ?",
  "source_language": "English",
  "target_language": "French"
}
```

---

## How translation works

This app uses [`deep-translator`](https://github.com/nidhaloff/deep-translator)'s `GoogleTranslator`, which calls Google Translate's free public web endpoint — the same one translate.google.com uses in the browser. There's no official API contract or SLA, so:

- It's **free and requires no signup**, but
- Google can rate-limit or change the endpoint without notice
- Very high-volume or production use isn't guaranteed reliable — for that, consider Google Cloud Translation API (paid, official) or self-hosted [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate)
- Your server needs internet access to reach Google's endpoint at request time

## Features

- 100+ languages
- Auto-detect source language
- Copy translated text
- Text-to-speech (browser built-in)
- Swap languages
- Dark mode (automatic)
- Keyboard shortcut: Ctrl+Enter to translate
- Character limit: 5000
