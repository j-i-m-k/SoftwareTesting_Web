import sqlite3
import os
from flask import Flask, redirect, request, render_template,render_template_string
from datetime import datetime
import pickle, base64

app = Flask(__name__)

# --- CONFIGURATION ---
DB_NAME = "vulnerable_system.db"

# --- USER DATA TO SEED ---
SEED_DATA = [
    ("admin", "SuperSecretPass"),
    ("alice", "wonderland1"),
    ("bob", "builder99"),
    ("charlie", "chocolate_factory"),
    ("dave", "hal9000"),
    ("eve", "spy_vs_spy")
]

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    print(f"[*] Creating and seeding database: {DB_NAME}")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.executemany("INSERT INTO users (username, password) VALUES (?, ?)", SEED_DATA)
    conn.commit()
    conn.close()

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html', server_time=str(datetime.now()))

@app.route('/loginDanger', methods=['GET', 'POST'])
def login_danger():
    """
    VULNERABLE: Uses string concatenation.
    """
    if request.method == 'GET':
        return render_template('login.html', 
                               title="Vulnerable Login", 
                               method_description="String Concatenation (Unsafe)")

    # Handle POST
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # DANGER: Directly injecting user input
    sql_query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    print(f"[*] Executing Dangerous SQL: {sql_query}")
    
    try:

        # OLD LINE (Safe against stacked queries) - a bit safe but still bad due to no parameters
        # cursor.execute(sql_query)

        # NEW LINE (Vulnerable to stacked queries)
        cursor.executescript(sql_query)


        cursor.execute(sql_query)
        user = cursor.fetchone()
    except sqlite3.Error as e:
        return render_template('login.html', title="Vulnerable Login", error=f"Database Error: {e}")
    finally:
        conn.close()

    if user:
        return render_template('login.html', 
                               title="Vulnerable Login", 
                               success_user=user['username'],
                               leaked_password=user['password']) # Displaying the password to prove the leak
    else:
        return render_template('login.html', 
                               title="Vulnerable Login", 
                               error="Invalid Credentials",
                               method_description="String Concatenation (Unsafe)")

@app.route('/loginSafe', methods=['GET', 'POST'])
def login_safe():
    """
    SECURE: Uses parameterized queries.
    """
    if request.method == 'GET':
        return render_template('login.html', 
                               title="Secure Login", 
                               method_description="Parameterized Query (Safe)")

    # Handle POST
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # SAFE: Using ? placeholders
    sql_query = "SELECT * FROM users WHERE username = ? AND password = ?"
    
    cursor.execute(sql_query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return render_template('login.html', 
                               title="Secure Login", 
                               success_user=user['username'])
    else:
        return render_template('login.html', 
                               title="Secure Login", 
                               error="Invalid Credentials",
                               method_description="Parameterized Query (Safe)")

@app.route('/xss', methods=['GET', 'POST'])
def xss_demo():
    """
    VULNERABLE: Reflected XSS Demo.
    We take user input and render it back to the page without sanitization.
    """
    if request.method == 'GET':
        return render_template('xss.html')

    # Handle POST
    comment = request.form.get('comment', '')
    
    # We pass the comment back to the template. 
    # The template uses {{ comment | safe }} to render it as raw HTML/JS.
    return render_template('xss.html', user_input=comment)

@app.route('/hello')
def hello():

    # try this:
    """
    {{config.__class__.__init__.__globals__['os'].popen('hostname').read()}}
    {{config.__class__.__init__.__globals__['os'].environ['path']}}

    """
    name = request.args.get('name', 'Guest')
    # VULNERABLE: Direct concatenation into the template string
    template = f"<h1>Hello {name}!</h1>" 
    return render_template_string(template)


@app.route('/set_prefs')
def set_prefs():
    # User sends a base64 encoded pickle string
    data = request.cookies.get('preferences')
    if data:
        # VULNERABLE: Never unpickle untrusted data!
        obj = pickle.loads(base64.b64decode(data))
        return f"Preferences loaded for {obj['username']}"
    return "No prefs"

@app.route('/login')
def gotonext():
    # ... logic to authenticate user ...
    next_url = request.args.get('next')

    # VULNERABLE: Redirects to whatever URL is provided
    return redirect(next_url)


@app.route('/crash')
def crash():
    """
    This route intentionally raises an error to trigger the Flask Debugger.
    """
    # 1. We define some sensitive variables to prove they get leaked
    secret_key = "12345-SECRET-KEY"
    db_password = "password123!"
    
    # 2. We trigger a ZeroDivisionError
    # This unhandled exception forces the Debugger page to appear
    result = 10 / 0 
    
    return f"Result is {result}"
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)