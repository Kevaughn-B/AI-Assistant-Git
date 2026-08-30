"""Secure Flask application for the AI Academic Assistant."""
from __future__ import annotations

import os
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

import bcrypt
import requests
from dotenv import load_dotenv
from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from media_processing.text_processor import TextProcessor
from qa_system.qa_model import QASystem
from recommendation_engine.recommender import Recommender

load_dotenv()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32),
        DATABASE=str(Path(app.root_path) / "users.db"),
        UPLOAD_FOLDER=str(Path(app.root_path) / "uploads"),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME"),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    def init_db():
        connection = db()
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS user_queries (id INTEGER PRIMARY KEY, username TEXT NOT NULL, query TEXT NOT NULL, answer TEXT NOT NULL, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, name TEXT NOT NULL, feature TEXT NOT NULL, feedback TEXT NOT NULL, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS contact_messages (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS pdf_uploads (id INTEGER PRIMARY KEY, username TEXT NOT NULL, filename TEXT NOT NULL, extracted_text TEXT NOT NULL, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY, username TEXT NOT NULL, query TEXT NOT NULL, recommendation TEXT NOT NULL, link TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS user_sessions (id INTEGER PRIMARY KEY, username TEXT NOT NULL, login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """)
        if "stored_filename" not in {r["name"] for r in connection.execute("PRAGMA table_info(pdf_uploads)")}:
            connection.execute("ALTER TABLE pdf_uploads ADD COLUMN stored_filename TEXT")
        connection.commit()

    with app.app_context():
        init_db()

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
                abort(400, "Invalid or missing CSRF token.")

    @app.errorhandler(413)
    def too_large(_error):
        flash("Uploads must be 10 MB or smaller.", "error")
        return redirect(url_for("extract_text"))

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "username" not in session:
                flash("Please log in first.", "error")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if len(username) < 3 or "@" not in email or len(password) < 8:
                flash("Use a 3+ character username, valid email, and 8+ character password.", "error")
            else:
                try:
                    digest = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    db().execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, digest))
                    db().commit()
                    flash("Account created. Please log in.", "success")
                    return redirect(url_for("login"))
                except sqlite3.IntegrityError:
                    flash("That username or email is already in use.", "error")
        return render_template("auth.html", mode="signup")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = db().execute("SELECT username, password FROM users WHERE username = ?", (request.form.get("username", "").strip(),)).fetchone()
            if user and bcrypt.checkpw(request.form.get("password", "").encode(), user["password"].encode()):
                session.clear()
                session["username"] = user["username"]
                csrf_token()
                db().execute("INSERT INTO user_sessions (username) VALUES (?)", (user["username"],))
                db().commit()
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("home"))

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if request.form.get("form_type") == "contact":
                email, message = request.form.get("email", "").strip(), request.form.get("message", "").strip()
                if name and "@" in email and message:
                    db().execute("INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)", (name, email, message))
                else:
                    flash("Please complete every contact field.", "error")
                    return redirect(url_for("contact"))
            elif request.form.get("form_type") == "feedback":
                feedback = request.form.get("feedback", "").strip()
                if name and feedback:
                    db().execute("INSERT INTO feedback (name, feature, feedback) VALUES (?, ?, ?)", (name, request.form.get("feature", "General"), feedback))
                else:
                    flash("Please provide your name and feedback.", "error")
                    return redirect(url_for("contact"))
            else:
                abort(400)
            db().commit()
            flash("Thanks — your message has been received.", "success")
            return redirect(url_for("contact"))
        return render_template("contact.html")

    @app.route("/ask", methods=["GET", "POST"])
    @login_required
    def ask():
        if request.method == "POST":
            question, context = request.form.get("question", "").strip(), request.form.get("context", "").strip()
            if not question or not context:
                flash("Both a question and supporting context are required.", "error")
            else:
                result = QASystem.instance().answer_question(question, context)
                if result.get("error"):
                    flash(result["error"], "error")
                else:
                    db().execute("INSERT INTO user_queries (username, query, answer) VALUES (?, ?, ?)", (session["username"], question, result["answer"]))
                    db().commit()
                    return render_template("answer.html", question=question, result=result)
        return render_template("ask.html")

    def books(query):
        try:
            response = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": query, "maxResults": 5}, timeout=8)
            response.raise_for_status()
        except requests.RequestException:
            return []
        return [{"title": item.get("volumeInfo", {}).get("title", "Untitled"), "link": item.get("volumeInfo", {}).get("infoLink", "#"), "type": "Google Books"} for item in response.json().get("items", [])]

    @app.route("/recommend", methods=["GET", "POST"])
    @login_required
    def recommend():
        if request.method == "POST":
            query = request.form.get("query", "").strip()
            if not query:
                flash("Enter a topic to get recommendations.", "error")
            else:
                local = [dict(row) for row in db().execute("SELECT recommendation AS title, link, 'Previous recommendation' AS type FROM recommendations WHERE username = ? AND query LIKE ? LIMIT 5", (session["username"], f"%{query}%"))]
                results = Recommender().get_recommendations(query, local, books(query))
                if results:
                    top = results[0]
                    db().execute("INSERT INTO recommendations (username, query, recommendation, link) VALUES (?, ?, ?, ?)", (session["username"], query, top["title"], top.get("link")))
                    db().commit()
                return render_template("recommendations.html", query=query, results=results)
        return render_template("recommend.html")

    @app.route("/extract_text", methods=["GET", "POST"])
    @login_required
    def extract_text():
        if request.method == "POST":
            uploaded = request.files.get("pdf")
            if not uploaded or not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
                flash("Please select a PDF file.", "error")
            elif uploaded.stream.read(5) != b"%PDF-":
                flash("The uploaded file is not a valid PDF.", "error")
            else:
                uploaded.stream.seek(0)
                filename = secure_filename(uploaded.filename)
                stored = f"{secrets.token_hex(16)}_{filename}"
                path = Path(app.config["UPLOAD_FOLDER"]) / stored
                uploaded.save(path)
                text = TextProcessor().extract_text_from_pdf(str(path))
                if text.startswith("Error processing PDF"):
                    path.unlink(missing_ok=True)
                    flash(text, "error")
                else:
                    db().execute("INSERT INTO pdf_uploads (username, filename, stored_filename, extracted_text) VALUES (?, ?, ?, ?)", (session["username"], filename, stored, text))
                    db().commit()
                    flash("PDF text extracted successfully.", "success")
                    return redirect(url_for("manage_pdfs"))
        return render_template("upload.html")

    @app.get("/manage_pdfs")
    @login_required
    def manage_pdfs():
        files = db().execute("SELECT id, filename, uploaded_at FROM pdf_uploads WHERE username = ? ORDER BY uploaded_at DESC", (session["username"],)).fetchall()
        return render_template("pdfs.html", files=files)

    def owned_pdf(file_id):
        file = db().execute("SELECT * FROM pdf_uploads WHERE id = ? AND username = ?", (file_id, session["username"])).fetchone()
        if file is None:
            abort(404)
        return file

    @app.get("/pdfs/<int:file_id>")
    @login_required
    def view_pdf(file_id):
        return render_template("pdf_text.html", file=owned_pdf(file_id))

    @app.get("/pdfs/<int:file_id>/download")
    @login_required
    def download_pdf(file_id):
        file = owned_pdf(file_id)
        output = Path(app.config["UPLOAD_FOLDER"]) / f"{file['stored_filename'] or file['filename']}.txt"
        output.write_text(file["extracted_text"], encoding="utf-8")
        return send_file(output, as_attachment=True, download_name=f"{Path(file['filename']).stem}.txt")

    @app.post("/pdfs/<int:file_id>/delete")
    @login_required
    def delete_pdf(file_id):
        file = owned_pdf(file_id)
        (Path(app.config["UPLOAD_FOLDER"]) / (file["stored_filename"] or file["filename"])).unlink(missing_ok=True)
        db().execute("DELETE FROM pdf_uploads WHERE id = ?", (file_id,))
        db().commit()
        flash("PDF deleted.", "success")
        return redirect(url_for("manage_pdfs"))

    @app.get("/search")
    @login_required
    def search():
        term = request.args.get("q", "").strip()
        results = db().execute("SELECT query, answer, submitted_at FROM user_queries WHERE username = ? AND (query LIKE ? OR answer LIKE ?) ORDER BY submitted_at DESC", (session["username"], f"%{term}%", f"%{term}%")).fetchall() if term else []
        return render_template("search.html", term=term, results=results)

    @app.get("/dashboard")
    @login_required
    def dashboard():
        connection = db()
        if app.config["ADMIN_USERNAME"] and session["username"] == app.config["ADMIN_USERNAME"]:
            metrics = {"users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], "queries": connection.execute("SELECT COUNT(*) FROM user_queries").fetchone()[0], "pdfs": connection.execute("SELECT COUNT(*) FROM pdf_uploads").fetchone()[0]}
            return render_template("dashboard.html", admin=True, metrics=metrics)
        return render_template("dashboard.html", admin=False,
            queries=connection.execute("SELECT query, answer, submitted_at FROM user_queries WHERE username = ? ORDER BY submitted_at DESC LIMIT 10", (session["username"],)).fetchall(),
            pdfs=connection.execute("SELECT id, filename, uploaded_at FROM pdf_uploads WHERE username = ? ORDER BY uploaded_at DESC LIMIT 10", (session["username"],)).fetchall(),
            recommendations=connection.execute("SELECT query, recommendation, link, timestamp FROM recommendations WHERE username = ? ORDER BY timestamp DESC LIMIT 10", (session["username"],)).fetchall())
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
