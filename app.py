#http://127.0.0.1:5000/
import os
from flask import Flask, request, jsonify, send_file
from qa_system.qa_model import QASystem
from recommendation_engine.recommender import Recommender
from media_processing.text_processor import TextProcessor
import sqlite3
import bcrypt
import logging
from flask import session

app = Flask(__name__)

app.secret_key = 'secret_key'

qa_system = QASystem()
recommender = Recommender()
text_processor = TextProcessor()

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Auto-incrementing unique ID
            username TEXT UNIQUE NOT NULL,        -- Unique username (required)
            email TEXT UNIQUE NOT NULL,           -- Unique email (required)
            password TEXT NOT NULL                -- Hashed password (required)
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

EXTRACTED_TEXT_FOLDER = os.path.expanduser("~/Downloads")

@app.route('/', methods=['GET'])
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Academic Assistant</title>
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
        <header>
            <h1>Welcome to the AI Academic Assistant</h1>
        </header>
    <body>
        <header style="display: flex; justify-content: space-between; align-items: center; background-color: #0078D7; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: left;">
                    <a href="/">Home</a>
                    <a href="#section1">Ask a Question</a>
                    <a href="#section2">Get Recommendations</a>
                    <a href="#section3">Extract Text from PDF</a>
                    <h4> | </h4>
                    <a href="/contact">Contact Us</a>
                </div>
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
        </header>
        <main>
            <section style="padding: 2rem; background-color: white;">
                <h2 style="text-align: center; margin-bottom: 1.5rem;">What Our Users Say</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; max-width: 1000px; margin: 0 auto;">
                    <div style="background: #f4f4f9; padding: 1rem; border-radius: 8px;">
                        <p>"This tool has revolutionized the way I study. The question-answering feature is amazing!"</p>
                        <p><strong>- Student A</strong></p>
                    </div>
                    <div style="background: #f4f4f9; padding: 1rem; border-radius: 8px;">
                        <p>"Extracting text from PDFs has never been easier. Highly recommended for researchers!"</p>
                        <p><strong>- Researcher B</strong></p>
                    </div>
                    <div style="background: #f4f4f9; padding: 1rem; border-radius: 8px;">
                        <p>"The recommendations I get are spot-on and super helpful for my assignments."</p>
                        <p><strong>- Student C</strong></p>
                    </div>
                </div>
            </section>
            <section style="padding: 2rem; background-color: #0078D7; color: white; text-align: center;">
                <h1>Welcome to the AI Academic Assistant</h1>
                <p>Your one-stop solution for academic excellence! Ask questions, extract text, and get recommendations in seconds.</p>
                <a href="/ask" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.75rem 1.5rem; border-radius: 5px;">Get Started</a>
            </section>
            <section style="padding: 2rem; background-color: #f4f4f9;">
                <h2 style="text-align: center; margin-bottom: 1.5rem;">Our Features</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; max-width: 1000px; margin: 0 auto;">
                    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <h3>Ask a Question</h3>
                        <p>Get precise answers to your academic questions using our advanced AI system.</p>
                        <a href="#section1" style="color: #0078D7; text-decoration: none;">Learn More &rarr;</a>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <h3>PDF Text Extraction</h3>
                        <p>Upload your PDF files and extract text instantly for easy referencing.</p>
                        <a href="/#section2" style="color: #0078D7; text-decoration: none;">Learn More &rarr;</a>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <h3>Get Recommendations</h3>
                        <p>Receive personalized academic recommendations based on your queries.</p>
                        <a href="#section3" style="color: #0078D7; text-decoration: none;">Learn More &rarr;</a>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <h3>Contact Us</h3>
                        <p>Have questions or feedback? Get in touch with our team for assistance.</p>
                        <a href="/contact" style="color: #0078D7; text-decoration: none;">Contact Us &rarr;</a>
                    </div>
                </div>
            </section>
            <section style="padding: 2rem; background-color: #0078D7; color: white; text-align: center;">
                <h2>Ready to Elevate Your Academic Journey?</h2>
                <p>Join the hundreds of students and researchers already using AI Academic Assistant.</p>
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.75rem 1.5rem; border-radius: 5px;">Get Started Now</a>
            </section>
            <section id="section1">
                <h2>Section 1</h2>
                <p>Question Answering</p>
                <div class="container">
                <p>Curious about something? Our AI-powered question-answering system is here to help. Enter your question along with optional context, and let the AI provide you with accurate, concise answers in seconds.</p>
                <a href="/ask">Ask a Question</a><br>
            </div>
            </section>
            <section id="section2">
                <h2>Section 2</h2>
                <p>Recommendation.</p>
                <div class="container">
                <p>Need resources tailored to your academic needs? Enter your query, and our system will recommend books, articles, and other materials to help you succeed.</p>
                <a href="/recommend">Get Recommendations</a><br>
            </div>
            </section>
            <section id="section3">
                <h2>Section 3</h2>
                <p>PDF Extractor.</p>
                <div class="container">
                <p>Dealing with lengthy PDFs? Upload your files, and our system will extract the text for you, making it easier to search, highlight, and reference important information.</p>
                <a href="/extract_text">Extract Text from PDF</a>
            </div>
            </section>
        </main>
        <footer>
            &copy; 2024 AI Academic Assistant ~ Kevaughn Benjamin. All rights reserved.
    </footer>
    </body>
    </html>
    '''

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Contact Us</title>
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
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
        </header>
            <main>
                <div class="container">
                    <form method="POST" action="/contact">
                        <label for="name">Name:</label><br>
                        <input type="text" id="name" name="name" placeholder="Your Name" required><br><br>
                        <label for="message">Message:</label><br>
                        <textarea id="message" name="message" placeholder="Your Message" rows="5" required></textarea><br><br>
                        <button type="submit">Submit</button>
                    </form>
                </div>
            </main>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name')
        message = request.form.get('message')

        # Log or process the contact form submission (placeholder for now)
        print(f"Name: {name}, Message: {message}")

        # Return a success message
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Thank You</title>
        </head>
        <body>
            <h1>Thank You for Contacting Us!</h1>
            <p>We have received your message and will get back to you soon.</p>
            <a href="/">Return to Home</a>
        </body>
        </html>
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
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
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
        conn.close()

        if result and verify_password(password, result[0]):
            return f'<h1>Welcome, {username}!</h1><a href="/">Go to Homepage</a>'
        else:
            return '<h1>Invalid username or password. Try again.</h1>'

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
    return '<h1>You have been logged out.</h1><a href="/">Return to Homepage</a>'

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
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
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
        </html>
        '''
    else:
        question = request.form['question']
        context = request.form.get('context', '')

        result = qa_system.answer_question(question, context)

        return f'''
        <h1>Answer:</h1>
        <p><strong>{result["answer"]}</strong></p>
        <p><small>Confidence: {round(result["confidence"] * 100, 2)}%</small></p>
        <h3>Context:</h3>
        <p>{result["context"].replace(result["answer"], f'<span class="highlight">{result["answer"]}</span>')}</p>
        <a href="/ask">Ask Another Question</a>
        '''

@app.route('/answer', methods=['POST'])
def answer():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        context = data.get('context', '').strip()

        if not question:
            return jsonify({"error": "Missing question"}), 400

        result = qa_system.answer_question(question, context)

        return jsonify({
            "answer": result["answer"],
            "confidence": result["confidence"],
            "context": result["context"]
        })

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {e}"}), 500

@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Get Recommendations</title>
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
                <h1>Get Recommendations</h1>
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
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
        </header>
            <main>
                <div class="container">
                    <form method="POST" action="/recommend">
                        <label for="query">Enter a Query:</label><br>
                        <input type="text" id="query" name="query" placeholder="e.g., machine learning books" required><br><br>
                        <button type="submit">Get Recommendations</button>
                    </form>
                </div>
            </main>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        query = request.form.get('query')

        if not query:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
            </head>
            <body>
                <h1>Error</h1>
                <p>You must provide a query. <a href="/recommend">Try Again</a></p>
            </body>
            </html>
            '''

        # Get recommendations based on the query
        recommendations = recommender.get_recommendations(query)

        # Display the recommendations in an HTML list
        recommendations_html = ''.join(f'<li>{rec}</li>' for rec in recommendations)

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Recommendations</title>
        </head>
        <body>
            <h1>Recommendations for "{query}"</h1>
            <ul>
                {recommendations_html}
            </ul>
            <a href="/recommend">Get More Recommendations</a>
        </body>
        </html>
        '''

@app.route('/extract_text', methods=['GET', 'POST'])
def extract_text():
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
                <a href="/login" style="color: white; text-decoration: none; background-color: #005BB5; padding: 0.5rem 1rem; border-radius: 5px;">Login</a>
        </header>
            <main>
                <div class="container">
                    <section>
                        <h2>Extract Text from PDFs</h2>
                        <p>Upload your PDF files and extract text instantly for easy referencing.</p>
                        <form action="/extract_text" method="post" enctype="multipart/form-data">
                            <input type="file" name="pdf" accept=".pdf" multiple required>
                            <button type="submit">Upload & Extract</button>
                        </form>
                    </section>
                </div>
            </main>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        try:
            files = request.files.getlist('pdf')
            extracted_texts = {}

            for pdf_file in files:
                pdf_path = f"/tmp/{pdf_file.filename}"
                pdf_file.save(pdf_path)

                extracted_text = text_processor.extract_text_from_pdf(pdf_path)
                extracted_texts[pdf_file.filename] = extracted_text

            # Save extracted text to file for download
            output_file = "/tmp/extracted_text.txt"
            with open(output_file, "w") as f:
                for filename, text in extracted_texts.items():
                    f.write(f"=== {filename} ===\n{text}\n\n")

            return f'''
            <h1>Extracted Text</h1>
            <pre>{extracted_texts}</pre>
            <a href="/download_extracted_text">Download Extracted Text</a>
            <br><br>
            <a href="/">Back to Home</a>
            <a href="/ask">Ask a Question</a>
            '''
        except Exception as e:
            return f"<h1>Error: {e}</h1><a href='/'>Try Again</a>"

@app.route('/download_extracted_text')
def download_extracted_text():
    output_file = os.path.join(EXTRACTED_TEXT_FOLDER, "extracted_text.txt")
    return send_file(output_file, as_attachment=True, download_name="extracted_text.txt")

if __name__ == '__main__':
    app.run(port=5000, debug=True)