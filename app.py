import sqlite3
import os
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
DB_NAME = "vulnerable_system.db"

# --- USER DATA TO SEED ---
# Plain text passwords as requested
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
    """Initializes the DB and seeds a list of users."""
    # Remove old DB to ensure clean state for this demo
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    print(f"[*] Creating and seeding database: {DB_NAME}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Seed data
    cursor.executemany("INSERT INTO users (username, password) VALUES (?, ?)", SEED_DATA)
    
    conn.commit()
    conn.close()
    print(f"[*] Database seeded with {len(SEED_DATA)} users.")

# --- ROUTES ---

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to the Vulnerable API",
        "server_time": str(datetime.now())
    })

@app.route('/loginDanger', methods=['POST'])
def login_danger():
    """
    VULNERABLE: Uses string concatenation.
    Allows UNION BASED SQL INJECTION to leak data.
    """
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # The query expects 3 columns in the table: id, username, password
    sql_query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    
    print(f"[*] Executing Dangerous SQL: {sql_query}")
    
    try:
        cursor.execute(sql_query)
        user = cursor.fetchone() # Fetches the FIRST match
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    if user:
        # We return the username found. If an attacker injects a UNION, 
        # they can make this return ANY data they want.
        return jsonify({
            "status": "success", 
            "logged_in_user": user['username'], 
            "password_leaked_in_object": user['password'], # Startlingly common API mistake
            "method": "DANGER"
        })
    else:
        return jsonify({"status": "failure", "message": "Invalid credentials"}), 401

@app.route('/loginSafe', methods=['POST'])
def login_safe():
    """
    SECURE: Uses parameterized queries.
    """
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    sql_query = "SELECT * FROM users WHERE username = ? AND password = ?"
    
    cursor.execute(sql_query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"status": "success", "user": user['username'], "method": "SAFE"})
    else:
        return jsonify({"status": "failure", "message": "Invalid credentials"}), 401

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)