# AI Academic Assistant

A Flask application for context-grounded Q&A, academic resource recommendations, and private PDF text extraction.

## Features

- Account-based access with password hashing and CSRF protection
- Question answering from user-supplied context (RoBERTa SQuAD2)
- Google Books and optional SerpAPI recommendations
- PDF text extraction, download, and per-user document management
- Private dashboards and Q&A search history

## Run locally

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

Visit `http://127.0.0.1:5000`. Set a strong `SECRET_KEY` before sharing the app. `SERPAPI_KEY` is optional; without it, recommendations still use Google Books and prior results.

## Deploy

The repository includes a `Procfile` for Render, Railway, or Heroku-style platforms. Configure these environment variables in the host:

- `SECRET_KEY` — a long random value
- `SERPAPI_KEY` — optional
- `ADMIN_USERNAME` — optional username for metrics-only admin access
- `FLASK_DEBUG=0`

Use `gunicorn app:app` as the start command. The current SQLite and local `uploads/` storage are suitable for a demo only. For a durable production deployment, use managed PostgreSQL and object storage (such as S3) before serving real users.

## Privacy

Runtime databases and uploaded PDFs are intentionally ignored by Git. Do not commit user documents, resumes, secrets, or `.env` files.
