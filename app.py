from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
API_KEY = os.getenv('EXCHANGE_API_KEY', 'demo')
DB_PATH = 'exchange_rates.db'

# Initialize database
def init_db():
    """Initialize SQLite database for caching exchange rates and user management"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rates (
            base_currency TEXT,
            target_currency TEXT,
            rate REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (base_currency, target_currency)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index on email for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# Cache management
def get_cached_rate(base_currency, target_currency):
    """Get cached exchange rate if valid"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT rate FROM exchange_rates 
        WHERE base_currency = ? AND target_currency = ? 
        AND last_updated > datetime('now', '-1 hour')
    ''', (base_currency.upper(), target_currency.upper()))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def cache_rate(base_currency, target_currency, rate):
    """Cache exchange rate in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO exchange_rates 
        (base_currency, target_currency, rate, last_updated)
        VALUES (?, ?, ?, datetime('now'))
    ''', (base_currency.upper(), target_currency.upper(), rate))
    
    conn.commit()
    conn.close()

# API functions
def fetch_from_exchangerate_api(base_currency):
    """Fetch exchange rates from external API"""
    try:
        if API_KEY == 'demo':
            # Demo data for testing without API key
            demo_rates = {
                "USD": 1.0,
                "EUR": 0.85,
                "GBP": 0.73,
                "JPY": 110.0,
                "CAD": 1.25,
                "AUD": 1.35,
                "CHF": 0.92,
                "CNY": 6.45,
                "INR": 74.5,
                "BRL": 5.2
            }
            return {"result": "success", "base_code": base_currency, "rates": demo_rates}
        
        # Real API call
        url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{base_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("result") == "success":
            return {
                "result": "success",
                "base_code": data["base_code"],
                "rates": data["conversion_rates"]
            }
        return None
            
    except Exception as e:
        logger.error(f"Error fetching rates: {e}")
        return None

def get_exchange_rates(base_currency):
    """Get exchange rates with caching"""
    base_currency = base_currency.upper()
    
    api_data = fetch_from_exchangerate_api(base_currency)
    if not api_data:
        return None
    
    # Cache the rates
    if API_KEY != 'demo':
        for target_currency, rate in api_data["rates"].items():
            if target_currency != base_currency:
                cache_rate(base_currency, target_currency, rate)
    
    return api_data

# Routes
@app.route('/')
def serve_landing():
    """Serve the landing page"""
    return send_from_directory('.', 'landing.html')

@app.route('/app')
def serve_app():
    """Serve the main application"""
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def serve_css():
    """Serve the CSS file"""
    return send_from_directory('.', 'styles.css')

@app.route('/script.js')
def serve_js():
    """Serve the JavaScript file"""
    return send_from_directory('.', 'script.js')

@app.route('/landing-styles.css')
def serve_landing_css():
    """Serve the landing page CSS file"""
    return send_from_directory('.', 'landing-styles.css')

@app.route('/landing-script.js')
def serve_landing_js():
    """Serve the landing page JavaScript file"""
    return send_from_directory('.', 'landing-script.js')

@app.route('/Assets/<path:filename>')
def serve_assets(filename):
    """Serve assets from Assets folder"""
    return send_from_directory('Assets', filename)

@app.route('/api/currencies')
def get_currencies():
    """Get list of available currencies"""
    rates_data = get_exchange_rates("USD")
    if rates_data and rates_data["result"] == "success":
        currencies = list(rates_data["rates"].keys())
        return jsonify({"currencies": sorted(currencies)})
    return jsonify({"error": "Failed to fetch currencies"}), 500

@app.route('/api/convert')
def convert_currency():
    """Convert between currencies"""
    from_currency = request.args.get('from', '').upper()
    to_currency = request.args.get('to', '').upper()
    amount = request.args.get('amount', type=float)
    
    if not from_currency or not to_currency or amount is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    rates_data = get_exchange_rates(from_currency)
    if not rates_data or rates_data["result"] != "success":
        return jsonify({"error": "Failed to fetch exchange rates"}), 500
    
    from_rate = rates_data["rates"].get(from_currency, 1)
    to_rate = rates_data["rates"].get(to_currency)
    
    if to_rate is None:
        return jsonify({"error": f"Currency {to_currency} not found"}), 400
    
    converted_amount = amount * (to_rate / from_rate)
    
    return jsonify({
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "converted_amount": round(converted_amount, 4),
        "rate": round(to_rate / from_rate, 6),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/rates/<base_currency>')
def get_all_rates(base_currency):
    """Get all exchange rates for a base currency"""
    base_currency = base_currency.upper()
    rates_data = get_exchange_rates(base_currency)
    
    if not rates_data or rates_data["result"] != "success":
        return jsonify({"error": "Failed to fetch exchange rates"}), 500
    
    return jsonify({
        "base": base_currency,
        "rates": rates_data["rates"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        
        # Validation
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Password validation
        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters long"}), 400
        
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400
        
        # Check if user already exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Email already registered"}), 409
        
        # Hash password and create user
        password_hash = generate_password_hash(password)
        
        cursor.execute('''
            INSERT INTO users (email, password_hash)
            VALUES (?, ?)
        ''', (email, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"User registered: {email}")
        
        return jsonify({
            "message": "Registration successful",
            "user_id": user_id,
            "email": email
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and login"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        # Find user
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password_hash FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        user_id, password_hash = user
        
        # Verify password
        if not check_password_hash(password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            "message": "Login successful",
            "user_id": user_id,
            "email": email
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500

@app.route('/api/check-email', methods=['GET'])
def check_email():
    """Check if email is already registered"""
    try:
        email = request.args.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        exists = cursor.fetchone() is not None
        conn.close()
        
        return jsonify({"available": not exists}), 200
        
    except Exception as e:
        logger.error(f"Email check error: {e}")
        return jsonify({"error": "Failed to check email"}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
