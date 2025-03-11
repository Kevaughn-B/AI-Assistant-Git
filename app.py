#http://127.0.0.1:5000/
import os
from qa_system.qa_model import QASystem
from recommendation_engine.recommender import Recommender
from media_processing.text_processor import TextProcessor
import sqlite3
import bcrypt
import logging
import requests
from werkzeug.utils import secure_filename
from flask import Flask, request, redirect, jsonify, url_for, render_template, send_file, session
from pdfminer.high_level import extract_text
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'secret_key'
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['SECRET_KEY'] = 'your_secret_key'

qa_system = QASystem()
recommender = Recommender()
text_processor = TextProcessor()

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

#def add_link_column():
    #conn = sqlite3.connect('users.db')
    #cursor = conn.cursor()
    #try:
    #    cursor.execute("ALTER TABLE recommendations ADD COLUMN link TEXT")
    #    conn.commit()
    #    print("✅ Added 'link' column to recommendations table.")
    #except sqlite3.OperationalError as e:
    #    print("Column may already exist or error occurred:", e)
    #conn.close()

#add_link_column()

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            username TEXT UNIQUE NOT NULL,        
            email TEXT UNIQUE NOT NULL,           
            password TEXT NOT NULL                
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            username TEXT NOT NULL,        
            query TEXT NOT NULL,           
            answer TEXT NOT NULL ,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP              
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            feature TEXT NOT NULL,
            feedback TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            filename TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            query TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
init_db()

logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@app.before_request
def log_request():
    logging.info(f"User accessed: {request.path} | Method: {request.method}")

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal Server Error: {error}")
    return "An internal error occurred.", 500

@app.errorhandler(404)
def not_found_error(error):
    logging.warning(f"Page not found: {request.path}")
    return "Page not found.", 404

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def search_google_books(query):
    api_url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": 5
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = []
        for item in data.get('items', []):
            volume_info = item.get('volumeInfo', {})
            title = volume_info.get('title', 'No Title')
            authors = ", ".join(volume_info.get('authors', []))
            info_link = volume_info.get('infoLink', '#')
            results.append({
                "title": f"{title} by {authors}" if authors else title,
                "link": info_link,
                "type": "Google Books"
            })
        return results
    else:
        return []

EXTRACTED_TEXT_FOLDER = os.path.expanduser("~/Downloads")

@app.route('/', methods=['GET'])
def home():
    username = session.get('username')
    return render_template('home.html', username=username)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    module = request.args.get('module', 'General Inquiry')
    
    if request.method == 'GET':
        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact Us</title>
            <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }}
            header {{
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }}
            header h1 {{
                margin: 0;
            }}
            main {{
                margin: 2rem;
            }}
            section {{
            padding: 100px;
            margin: 50px 0;
            border: 1px solid #ccc;
        }}
        .form-group {{
                    display: flex;
                    flex-direction: column;
                }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            a {{
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background-color 0.3s ease;
            }}
            a:hover {{
                background-color: #005BB5;
            }}
            footer {{
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }}
        </style>
        </head>
        <body>
            <header>
                <h1>Contact Us</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="/ask">Ask a Question</a>
                    <a href="/recommend">Get Recommendations</a>
                    <a href="/extract_text">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
            <main>
                <div class="container">
                    <form method="POST" action="/contact">
                        <label for="name">Name:</label><br>
                        <input type="text" id="name" name="name" placeholder="Your Name" required><br><br>
                        <label for="email">Email:</label><br>
                        <input type="email" id="email" name="email" placeholder="Your Email" required><br><br>
                        <label for="message">Message:</label><br>
                        <textarea id="message" name="message" placeholder="Your Message" rows="5" required></textarea><br><br>
                        <button type="submit">Submit</button>
                    </form>
                </div>
                <div class="container">
                    <h2>Feature Feedback</h2>
                    <form method="POST" action="/contact" class="form-group">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>
                        <label for="module">Feature:</label>
                        <input type="text" id="module" name="module" value="{module}" readonly> <!-- Auto-filled -->
                        <label for="feature_feedback">Feature Feedback:</label>
                        <textarea id="feature_feedback" name="feature_feedback" rows="4" required></textarea>
                        <button type="submit" name="feedback_type" value="feature">Submit Feature Feedback</button>
                    </form>
                </div>
            </main>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        feedback_type = request.form.get('feedback_type')

        if feedback_type == "contact":
            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)", (name, email, message))
            conn.commit()
            conn.close()

            return '''
            <h1>Thank You!</h1>
            <p>Your message has been received. We will get back to you soon.</p>
            <a href="/">Return to Home</a>
            '''

        elif feedback_type == "feature":
            name = request.form.get('name')
            module = request.form.get('module')
            feedback = request.form.get('feature_feedback')

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO feedback (name, feature, feedback) VALUES (?, ?, ?)", (name, module, feedback))
            conn.commit()
            conn.close()

            return '''
            <h1>Thank You!</h1>
            <p>Your feature feedback has been received.</p>
            <a href="/">Return to Home</a>
            '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - AI Academic Assistant</title>
            <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }
            header {
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }
            header h1 {
                margin: 0;
            }
            main {
                margin: 2rem;
            }
            section {
            padding: 100px;
            margin: 50px 0;
            border: 1px solid #ccc;
        }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            a {
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background-color 0.3s ease;
            }
            a:hover {
                background-color: #005BB5;
            }
            footer {
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
        </head>
        <body>
            <header>
                <h1>Login</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
            <main>
                <div class="container">
                    <form method="POST" action="/login">
                        <label for="username">Username:</label><br>
                        <input type="text" id="username" name="username" placeholder="Enter your username" required><br>
                        <label for="password">Password:</label><br>
                        <input type="password" id="password" name="password" placeholder="Enter your password" required><br><br>
                        <button type="submit">Login</button>
                        <p></p>
                        <a href = "/signup">New? Sign Up</a>
                    </form>
                </div>
            </main>
            <footer>
                &copy; 2024 AI Academic Assistant ~ Kevaughn Benjamin. All rights reserved.
            </footer>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        if result and verify_password(password, result[0]):
            session['username'] = username
            session['logged_in'] = True
            session.permanent = True

            cursor.execute("INSERT INTO user_sessions (username) VALUES (?)", (username,))
            conn.commit()
            conn.close()

            return redirect(url_for('dashboard'))
        else:
            return "<h1>Invalid credentials. Try again.</h1>"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - AI Academic Assistant</title>
            <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }
            header {
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }
            header h1 {
                margin: 0;
            }
            main {
                margin: 2rem;
            }
            section {
            padding: 100px;
            margin: 50px 0;
            border: 1px solid #ccc;
        }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            a {
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background-color 0.3s ease;
            }
            a:hover {
                background-color: #005BB5;
            }
            footer {
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
        </head>
        <body>
            <header>
                <h1>Sign Up</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
        </header>
            <main>
                <div class="container">
                    <form method="POST">
                    <label for="username">Username:</label><br>
                    <input type="text" id="username" name="username" required><br>
                    <label for="email">Email:</label><br>
                    <input type="email" id="email" name="email" required><br>
                    <label for="password">Password:</label><br>
                    <input type="password" id="password" name="password" required><br>
                    <button type="submit">Sign Up</button>
                </form>
                </div>
            </main>
            <footer>
                &copy; 2024 AI Academic Assistant ~ Kevaughn Benjamin. All rights reserved.
            </footer>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password(request.form['password'])

        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, password)
            )
            conn.commit()
            conn.close()
            return '<h1>Signup successful!</h1><a href="/login">Login</a>'
        except sqlite3.IntegrityError:
            return '<h1>Username or email already exists. Try again.</h1>'
    return

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Unified Search</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f4f4f9; }
                .container { max-width: 500px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px; }
                input[type="text"] { width: 80%; padding: 10px; margin: 10px 0; }
                button { padding: 10px 20px; background-color: #0078D7; color: white; border: none; border-radius: 5px; }
                button:hover { background-color: #005BB5; }
            </style>
        </head>
        <body>
            <h1>Search All User Data</h1>
            <div class="container">
                <form method="POST">
                    <input type="text" name="search_term" placeholder="Enter search term" required>
                    <button type="submit">Search</button>
                </form>
            </div>
        </body>
        </html>
        '''
    else:
        search_term = request.form.get('search_term')
        if not search_term:
            return "<h1>Error: No search term provided.</h1><a href='/search'>Try Again</a>"

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute("SELECT username, query, answer, submitted_at FROM user_queries WHERE query LIKE ? OR answer LIKE ?",
                    (f"%{search_term}%", f"%{search_term}%"))
        query_results = cursor.fetchall()

        cursor.execute("SELECT username, query, recommendation, timestamp FROM recommendations WHERE query LIKE ? OR recommendation LIKE ?",
                    (f"%{search_term}%", f"%{search_term}%"))
        rec_results = cursor.fetchall()

        cursor.execute("SELECT username, filename, uploaded_at FROM pdf_uploads WHERE filename LIKE ? OR extracted_text LIKE ?",
                    (f"%{search_term}%", f"%{search_term}%"))
        pdf_results = cursor.fetchall()

        conn.close()

        query_html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in query_results)
        rec_html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in rec_results)
        pdf_html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in pdf_results)

        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Search Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; text-align: center; }}
                table {{
                    width: 80%;
                    margin: 20px auto;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
                th {{ background-color: #0078D7; color: white; }}
                a {{
                    display: inline-block;
                    margin: 20px;
                    padding: 10px 20px;
                    background-color: #0078D7;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                a:hover {{ background-color: #005BB5; }}
            </style>
        </head>
        <body>
            <h1>Search Results for "{search_term}"</h1>
            
            <h2>Past Questions & Answers</h2>
            <table>
                <tr><th>Username</th><th>Query</th><th>Answer</th><th>Submitted At</th></tr>
                {query_html if query_html else "<tr><td colspan='4'>No results found.</td></tr>"}
            </table>
            
            <h2>Recommendations</h2>
            <table>
                <tr><th>Username</th><th>Query</th><th>Recommendation</th><th>Time</th></tr>
                {rec_html if rec_html else "<tr><td colspan='4'>No recommendations found.</td></tr>"}
            </table>
            
            <h2>Uploaded PDFs</h2>
            <table>
                <tr><th>Username</th><th>Filename</th><th>Uploaded At</th></tr>
                {pdf_html if pdf_html else "<tr><td colspan='3'>No PDFs found.</td></tr>"}
            </table>
            
            <br><a href="/search">New Search</a>
            <a href="/">Back to Home</a>
        </body>
        </html>
        '''

@app.route('/manage_entries')
def manage_entries():
    if 'username' not in session:
        return "<h1>Please log in first.</h1><a href='/login'>Login</a>"
    
    username = session['username']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, query, answer, submitted_at FROM user_queries WHERE username = ? ORDER BY submitted_at DESC", (username,))
    questions = cursor.fetchall()
    
    cursor.execute("SELECT id, query, recommendation, timestamp FROM recommendations WHERE username = ? ORDER BY timestamp DESC", (username,))
    recs = cursor.fetchall()
    
    conn.close()
    
    questions_html = "".join(
        f"<tr><td>{q[1]}</td><td>{q[2]}</td><td>{q[3]}</td><td><a href='/delete_query/{q[0]}'>Delete</a></td></tr>"
        for q in questions
    )
    
    recs_html = "".join(
        f"<tr><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td><a href='/delete_recommendation/{r[0]}'>Delete</a></td></tr>"
        for r in recs
    )
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Manage Your Entries</title>
        <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            text-align: center;
            padding: 20px;
        }}
        table {{
            width: 80%;
            margin: 20px auto;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background-color: #0078D7;
            color: white;
        }}
        a {{
            color: #0078D7;
            text-decoration: none;
        }}
        a:hover {{
            color: #005BB5;
        }}
        </style>
    </head>
    <body>
        <h1>Manage Your Entries</h1>
        
        <h2>Your Past Questions</h2>
        <table>
            <tr><th>Question</th><th>Answer</th><th>Asked At</th><th>Action</th></tr>
            {questions_html if questions_html else "<tr><td colspan='4'>No questions found.</td></tr>"}
        </table>
        <h2>Your Past Recommendations</h2>
        <table>
            <tr><th>Query</th><th>Recommendation</th><th>Time</th><th>Action</th></tr>
            {recs_html if recs_html else "<tr><td colspan='4'>No recommendations found.</td></tr>"}
        </table>
        <br><a href="/">Back to Home</a>
    </body>
    </html>
    '''

@app.route('/delete_query/<int:query_id>')
def delete_query(query_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_queries WHERE id = ? AND username = ?", (query_id, username))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_entries'))

@app.route('/delete_recommendation/<int:rec_id>')
def delete_recommendation(rec_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recommendations WHERE id = ? AND username = ?", (rec_id, username))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_entries'))

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Ask a Question</title>
            <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }
            header {
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }
            header h1 {
                margin: 0;
            }
            main {
                margin: 2rem;
            }
            section {
            padding: 100px;
            margin: 50px 0;
            border: 1px solid #ccc;
        }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            a {
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background-color 0.3s ease;
            }
            a:hover {
                background-color: #005BB5;
            }
            footer {
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
        
        </head>
        <body>
            <header>
                <h1>Ask a Question</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="/ask">Ask a Question</a>
                    <a href="/recommend">Get Recommendations</a>
                    <a href="/extract_text">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
            <main>
                <div class="container">
                    <form method="POST" action="/ask">
                        <label for="question">Question:</label><br>
                        <input type="text" id="question" name="question" placeholder="Enter your question" required><br><br>
                        <label for="context">Context (optional):</label><br>
                        <textarea id="context" name="context" placeholder="Enter context here..."></textarea><br><br>
                        <button type="submit">Get Answer</button>
                    </form>
                </div>
            </main>
        </body>
        <footer><a href="/contact?module=Ask a Question" class="feedback-button">Give Feedback</a></footer>
        </html>
        '''
    else:
        if 'username' not in session:
            return "<h1>Please log in to ask a question.</h1><a href='/login'>Login</a>"

        username = session['username']
        question = request.form['question']
        context = request.form.get('context', '')

        result = qa_system.answer_question(question, context)
        answer = result["answer"]

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_queries (username, query, answer) VALUES (?, ?, ?)",
            (username, question, answer)
        )
        conn.commit()
        conn.close()

        return f'''
        <h1>Answer:</h1>
        <p><strong>{answer}</strong></p>
        <p><small>Confidence: {round(result["confidence"] * 100, 2)}%</small></p>
        <h3>Context:</h3>
        <p>{result["context"].replace(answer, f'<span class="highlight">{answer}</span>')}</p>
        <a href="/ask">Ask Another Question</a>
        '''

@app.route('/answer', methods=['POST'])
def answer():
    try:
        if 'username' not in session:
            return jsonify({"error": "Please log in to ask questions"}), 401

        data = request.get_json()
        question = data.get('question', '').strip()
        context = data.get('context', '').strip()

        if not question:
            return jsonify({"error": "Missing question"}), 400

        result = qa_system.answer_question(question, context)
        answer = result["answer"]

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_queries (username, query, answer) VALUES (?, ?, ?)",
            (session['username'], question, answer)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "answer": answer,
            "confidence": result["confidence"],
            "context": result["context"]
        })

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {e}"}), 500

def search_duckduckgo(query):
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "pretty": 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    results = []
    for topic in data.get("RelatedTopics", []):
        if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
            results.append({
                "title": topic["Text"],
                "link": topic["FirstURL"],
                "type": "Web Search"
            })
        elif isinstance(topic, dict) and "Topics" in topic:
            for subtopic in topic["Topics"]:
                if "Text" in subtopic and "FirstURL" in subtopic:
                    results.append({
                        "title": subtopic["Text"],
                        "link": subtopic["FirstURL"],
                        "type": "Web Search"
                    })
    return results

def get_local_recommendations(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT query, recommendation, link FROM recommendations WHERE query LIKE ?", (f"%{query}%",))
    results = cursor.fetchall()
    conn.close()
    recs = []
    for q, title, link in results:
        recs.append({
            "title": title,
            "link": link,
            "type": "Local Recommendation"
        })
    return recs

@app.route('/recommend', methods=['GET', 'POST'])
def recommend_route():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extract Text from PDF</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
            }
            header {
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }
            header h1 {
                margin: 0;
            }
            main {
                margin: 2rem;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            a {
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            a:hover {
                background-color: #005BB5;
            }
            footer {
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
    </head>
    <body>
            <header>
                <h1>Academic Recommendations</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="/ask">Ask a Question</a>
                    <a href="/recommend">Get Recommendations</a>
                    <a href="/extract_text">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
            <div class="container">
                <form method="POST">
                    <label for="query">Enter a Query:</label><br>
                    <input type="text" id="query" name="query" placeholder="e.g., machine learning books" required><br><br>
                    <button type="submit">Get Recommendations</button>
                </form>
            </div>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        if 'username' not in session:
            return "<h1>Please log in to get recommendations.</h1><a href='/login'>Login</a>"
        
        username = session['username']
        query = request.form.get('query')
        if not query:
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body>
                <h1>Error</h1>
                <p>You must provide a query. <a href="/recommend">Try Again</a></p>
            </body>
            </html>
            '''
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_queries (username, query, answer) VALUES (?, ?, ?)", (username, query, "N/A"))
        conn.commit()

        local_results = get_local_recommendations(query)
        duckduckgo_results = search_duckduckgo(query)
        google_books_results = search_google_books(query)

        combined_results = local_results + duckduckgo_results + google_books_results

        if combined_results:
            recommendation_text = combined_results[0]["title"]
            cursor.execute("INSERT INTO recommendations (username, query, recommendation, link) VALUES (?, ?, ?, ?)", 
                (username, query, recommendation_text, combined_results[0]["link"]))
            conn.commit()
        conn.close()

        recommendations_html = ''.join(
            f'<li><b>{rec["type"]}:</b> <a href="{rec["link"]}" target="_blank">{rec["title"]}</a></li>' 
            for rec in combined_results
        )

        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recommendations</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    text-align: center;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                li {{
                    margin: 10px 0;
                }}
                a {{
                    color: #0078D7;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <h1>Recommendations for "{query}"</h1>
            <ul>
                {recommendations_html if recommendations_html else "<li>No recommendations found.</li>"}
            </ul>
            <a href="/recommend">Get More Recommendations</a>
        </body>
        </html>
        '''

@app.route('/extract_text', methods=['GET', 'POST'])
def extract_text_route():
    if 'username' not in session:
        return "<h1>Please log in first.</h1><a href='/login'>Login</a>"

    username = session['username']

    if request.method == 'POST':
        pdf_file = request.files['pdf']
        if pdf_file and pdf_file.filename.endswith('.pdf'):
            filename = secure_filename(pdf_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(filepath)

            extracted_text = extract_text(filepath)
            formatted_text = extracted_text.replace("\n\n", "<br><br>")

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO pdf_uploads (username, filename, extracted_text) VALUES (?, ?, ?)", 
                        (username, filename, extracted_text))
            conn.commit()
            conn.close()

            return redirect(url_for('view_extracted_text', filename=filename))
    
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extract Text from PDF</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
            }
            header {
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }
            header h1 {
                margin: 0;
            }
            main {
                margin: 2rem;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            a {
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            a:hover {
                background-color: #005BB5;
            }
            footer {
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>Extract Text from PDF</h1>
        </header>
        <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="/ask">Ask a Question</a>
                    <a href="/recommend">Get Recommendations</a>
                    <a href="/extract_text">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
        <main>
            <h1>Upload PDF</h1>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="pdf" accept=".pdf" required><br><br>
                <button type="submit">Upload & Extract</button>
            </form>
            <a href="/manage_pdfs">Manage Uploaded PDFs</a>
        </main>
    </body>
    <footer><a href="/contact?module=Feedback" class="feedback-button">Give Feedback</a></footer>
    </html>
    '''

@app.route('/manage_pdfs')
def manage_pdfs():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, filename, uploaded_at FROM pdf_uploads ORDER BY uploaded_at DESC")
    files = cursor.fetchall()
    conn.close()

    file_list = "".join([f"""
        <tr>
            <td>{file[1]}</td>
            <td>{file[2]}</td>
            <td><a href='/view_text/{file[1]}'>View</a></td>
            <td><a href='/delete_pdf/{file[0]}'>Delete</a></td>
        </tr>""" for file in files])

    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Manage Uploaded PDFs</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }}
            header {{
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }}
            header h1 {{
                margin: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            table {{
                width: 80%;
                margin: 20px auto;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #0078D7;
                color: white;
            }}
            a {{
                display: inline-block;
                margin: 20px 0;
                padding: 10px 20px;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }}
            a:hover {{
                background-color: #005BB5;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Manage Uploaded PDFs</h1>
        </header>
        <div class="container">
            <table>
                <tr>
                    <th>Filename</th>
                    <th>Uploaded At</th>
                    <th>Actions</th>
                </tr>
                {file_list}
            </table>
        </div>
        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    '''

    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at FROM pdf_uploads ORDER BY uploaded_at DESC")
    files = cursor.fetchall()
    conn.close()

    file_list = "".join([f"""
        <tr>
            <td>{file[1]}</td>
            <td>{file[2]}</td>
            <td><a href='/view_text/{file[1]}'>View</a></td>
            <td><a href='/delete_pdf/{file[0]}'>Delete</a></td>
        </tr>""" for file in files])

    return f'''
    <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact Us</title>
            <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                text-align: center;
                scroll-behavior: smooth;
            }}
            header {{
                background-color: #0078D7;
                color: white;
                padding: 1rem;
            }}
            header h1 {{
                margin: 0;
            }}
            main {{
                margin: 2rem;
            }}
            section {{
            padding: 100px;
            margin: 50px 0;
            border: 1px solid #ccc;
        }}
        .form-group {{
                    display: flex;
                    flex-direction: column;
                }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            a {{
                display: inline-block;
                margin: 1rem 0;
                padding: 0.75rem 1.5rem;
                background-color: #0078D7;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background-color 0.3s ease;
            }}
            a:hover {{
                background-color: #005BB5;
            }}
            footer {{
                margin-top: 2rem;
                font-size: 0.9rem;
                color: #666;
            }}
            .textcentering {{
                text-align: center;
            }}
        </style>
        </head>
    <body>
    <header>
                <h1>Manage Uploaded PDFs</h1>
            </header>
            <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="/ask">Ask a Question</a>
                    <a href="/recommend">Get Recommendations</a>
                    <a href="/extract_text">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
        </header>
        <div>
    <table border="1" >
        <tr>
            <th>Filename</th>
            <th>Uploaded At</th>
            <th>Actions</th>
        </tr>
        {file_list}
    </table>
    </div>
    <br>
    <a href="/">Back to Home</a>
    </body>
    </html>
    '''

@app.route('/view_text/<filename>')
def view_extracted_text(filename):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT extracted_text FROM pdf_uploads WHERE filename=?", (filename,))
    result = cursor.fetchone()
    conn.close()

    if result:
        extracted_text = result[0].replace("\n\n", "<br><br>")
        return f'''
        <h1>Extracted Text - {filename}</h1>
        <div style="white-space: pre-line; border: 1px solid #ccc; padding: 10px;">{extracted_text}</div>
        <br>
        <a href="/">Back to Home</a>
        <a href="/download/{filename}">Download Extracted Text</a>
        '''
    return "<h1>No text found</h1>"

@app.route('/download/<filename>')
def download_extracted_text(filename):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT extracted_text FROM pdf_uploads WHERE filename=?", (filename,))
    result = cursor.fetchone()
    conn.close()

    if result:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}.txt")
        with open(filepath, "w") as f:
            f.write(result[0])

        return send_file(filepath, as_attachment=True)

    return "<h1>File not found</h1>"

@app.route('/delete_pdf/<int:file_id>')
def delete_pdf(file_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT filename FROM pdf_uploads WHERE id=?", (file_id,))
    file = cursor.fetchone()
    
    if file:
        filename = file[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        cursor.execute("DELETE FROM pdf_uploads WHERE id=?", (file_id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('manage_pdfs'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return "<h1>Please log in first.</h1><a href='/login'>Login</a>"

    username = session['username']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if username == 'admin':
        cursor.execute("SELECT name, email, message, submitted_at FROM contact_messages ORDER BY submitted_at DESC")
        messages = cursor.fetchall()

        cursor.execute("SELECT name, feature, feedback, submitted_at FROM feedback ORDER BY submitted_at DESC")
        feedback = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        total_logins = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pdf_uploads")
        total_pdfs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_queries")
        total_queries = cursor.fetchone()[0]

        cursor.execute("""
            SELECT users.username, 
                COUNT(DISTINCT user_queries.id) AS total_queries, 
                COUNT(DISTINCT recommendations.id) AS total_recommendations,
                COUNT(DISTINCT pdf_uploads.id) AS total_pdfs
            FROM users
            LEFT JOIN user_queries ON users.username = user_queries.username
            LEFT JOIN recommendations ON users.username = recommendations.username
            LEFT JOIN pdf_uploads ON users.username = pdf_uploads.username  -- FIXED THIS LINE
            GROUP BY users.username
            ORDER BY total_queries DESC, total_recommendations DESC, total_pdfs DESC
            LIMIT 5
        """)
        active_users = cursor.fetchall()
        conn.close()

        message_list = "".join(f"<tr><td>{m[0]}</td><td>{m[1]}</td><td>{m[2]}</td><td>{m[3]}</td></tr>" for m in messages)
        feedback_list = "".join(f"<tr><td>{f[0]}</td><td>{f[1]}</td><td>{f[2]}</td><td>{f[3]}</td></tr>" for f in feedback)
        active_user_list = "".join(f"<tr><td>{u[0]}</td><td>{u[1]} queries</td><td>{u[2]} recommendations</td><td>{u[3]} PDFs</td></tr>" for u in active_users)

        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Dashboard</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f9;
                    color: #333;
                    text-align: center;
                }}
                h1 {{ margin: 20px 0; }}
                table {{
                    width: 80%;
                    margin: 20px auto;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 10px;
                    text-align: left;
                }}
                th {{ background-color: #0078D7; color: white; }}
                a {{
                    display: inline-block;
                    margin: 20px 0;
                    padding: 10px 20px;
                    background-color: #0078D7;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                a:hover {{ background-color: #005BB5; }}
            </style>
        </head>
        <body>
            <h1>Admin Dashboard</h1>
            <section>
                <h2>System Metrics</h2>
                <p>Total User Logins: {total_logins}</p>
                <p>Total PDFs Uploaded: {total_pdfs}</p>
                <p>Total Recommendations: {total_recommendations}</p>
                <p>Total Queries: {total_queries}</p>
            </section>
            <section>
                <h3>Most Active Users</h3>
                <table>
                    <tr><th>Username</th><th>Queries</th><th>Recommendations</th><th>PDF Uploads</th></tr>
                    {active_user_list}
                </table>
            </section>
            <section>
                <h3>Contact Messages</h3>
                <table><tr><th>Name</th><th>Email</th><th>Message</th><th>Submitted At</th></tr>{message_list}</table>
            </section>
            <section>
                <h3>Feedback</h3>
                <table><tr><th>Name</th><th>Feature</th><th>Message</th><th>Submitted At</th></tr>{feedback_list}</table>
            </section>
        </body>
        <a href="/">Go to Home</a>
        </html>
        '''

    else:
        cursor.execute("SELECT query, answer, submitted_at FROM user_queries WHERE username = ? ORDER BY submitted_at DESC", (username,))
        user_queries = cursor.fetchall()

        cursor.execute("SELECT filename, uploaded_at FROM pdf_uploads WHERE username = ? ORDER BY uploaded_at DESC", (username,))
        user_pdfs = cursor.fetchall()

        cursor.execute("SELECT query, recommendation, timestamp FROM recommendations WHERE username = ? ORDER BY timestamp DESC", (username,))
        user_recommendations = cursor.fetchall()

        conn.close()

        user_query_list = "".join(f"<tr><td>{q[0]}</td><td>{q[1]}</td><td>{q[2]}</td></tr>" for q in user_queries)
        user_pdf_list = "".join(f"<tr><td>{p[0]}</td><td>{p[1]}</td></tr>" for p in user_pdfs)
        user_recommendation_list = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in user_recommendations)

        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>User Dashboard</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    text-align: center;
                }}
                h1 {{ margin: 20px 0; }}
                table {{
                    width: 80%;
                    margin: 20px auto;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 10px;
                    text-align: left;
                }}
                th {{ background-color: #0078D7; color: white; }}
            </style>
        </head>
        <body>
            <h1>User Dashboard</h1>
            <h2>Welcome, {username}!</h2>
            <section>
                <h3>Your Past Questions</h3>
                <table><tr><th>Question</th><th>Answer</th><th>Asked At</th></tr>{user_query_list}</table>
            </section>
            <section>
                <h3>Your Uploaded PDFs</h3>
                <table><tr><th>Filename</th><th>Uploaded At</th></tr>{user_pdf_list}</table>
            </section>
            <section>
                <h3>Your Past Recommendations</h3>
                <table><tr><th>Query</th><th>Recommendation</th><th>Time</th></tr>{user_recommendation_list}</table>
            </section>
        </body>
        <br><a href="/">Back to Home</a>
        </html>
        '''

if __name__ == '__main__':
    app.run(port=5000, debug=True)
