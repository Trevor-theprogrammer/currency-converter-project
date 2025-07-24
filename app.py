from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
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
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

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
    
    # Check if users table exists and add missing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'users' not in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchall()]:
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
    else:
        # Add missing columns
        if 'last_login' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN last_login TIMESTAMP')
        if 'first_name' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT')
        if 'last_name' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN last_name TEXT')
        if 'phone' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN phone TEXT')
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        if 'is_active' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            amount REAL NOT NULL,
            converted_amount REAL NOT NULL,
            exchange_rate REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorite_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, from_currency, to_currency)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            target_rate REAL NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversion_history_user_id ON conversion_history(user_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at)
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

# Authentication helpers
def generate_session_token():
    """Generate a secure session token"""
    return str(uuid.uuid4())

def validate_session_token(token):
    """Validate session token and return user info"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id FROM user_sessions 
        WHERE session_token = ? AND expires_at > datetime('now')
    ''', (token,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

# Routes
@app.route('/')
def serve_landing():
    """Serve the landing page"""
    return send_from_directory('.', 'landing.html')

@app.route('/app')
def serve_app():
    """Serve the main application"""
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def serve_dashboard():
    """Serve the dashboard"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/dashboard-styles.css')
def serve_dashboard_css():
    """Serve the dashboard CSS file"""
    return send_from_directory('.', 'dashboard-styles.css')

@app.route('/dashboard-script.js')
def serve_dashboard_js():
    """Serve the dashboard JavaScript file"""
    return send_from_directory('.', 'dashboard-script.js')

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
    
    # Get session token to save to history if user is logged in
    session_token = request.headers.get('Authorization')
    if session_token:
        user_id = validate_session_token(session_token)
        if user_id:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversion_history 
                    (user_id, from_currency, to_currency, amount, converted_amount, exchange_rate)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, from_currency, to_currency, amount, round(converted_amount, 4), round(to_rate / from_rate, 6)))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error saving conversion history: {e}")
    
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
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        
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
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (email, password_hash, first_name, last_name))
        
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
        
        if not user:
            conn.close()
            return jsonify({"error": "Invalid email or password"}), 401
        
        user_id, password_hash = user
        
        # Verify password
        if not check_password_hash(password_hash, password):
            conn.close()
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Update last login
        cursor.execute('''
            UPDATE users SET last_login = datetime('now') WHERE id = ?
        ''', (user_id,))
        
        # Create session
        session_token = generate_session_token()
        expires_at = datetime.now() + timedelta(days=7)
        
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, session_token, expires_at, request.remote_addr, request.headers.get('User-Agent')))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            "message": "Login successful",
            "user_id": user_id,
            "email": email,
            "session_token": session_token
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user and invalidate session"""
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        
        if not session_token:
            return jsonify({"error": "Session token required"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Logout successful"}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, first_name, last_name, phone, created_at, last_login
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "id": user[0],
            "email": user[1],
            "first_name": user[2],
            "last_name": user[3],
            "phone": user[4],
            "created_at": user[5],
            "last_login": user[6]
        }), 200
        
    except Exception as e:
        logger.error(f"Profile fetch error: {e}")
        return jsonify({"error": "Failed to fetch profile"}), 500

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile information"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET first_name = ?, last_name = ?, phone = ?, updated_at = datetime('now')
            WHERE id = ?
        ''', (data.get('first_name', ''), data.get('last_name', ''), data.get('phone', ''), user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Profile updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

@app.route('/api/user/history', methods=['GET'])
def get_conversion_history():
    """Get user's conversion history"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, from_currency, to_currency, amount, converted_amount, 
                   exchange_rate, created_at
            FROM conversion_history 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        history = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "history": [{
                "id": h[0],
                "from_currency": h[1],
                "to_currency": h[2],
                "amount": h[3],
                "converted_amount": h[4],
                "exchange_rate": h[5],
                "created_at": h[6]
            } for h in history]
        }), 200
        
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

@app.route('/api/user/favorites', methods=['GET'])
def get_favorite_pairs():
    """Get user's favorite currency pairs"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, from_currency, to_currency, created_at
            FROM favorite_pairs
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        favorites = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "favorites": [{
                "id": f[0],
                "from_currency": f[1],
                "to_currency": f[2],
                "created_at": f[3]
            } for f in favorites]
        }), 200
        
    except Exception as e:
        logger.error(f"Favorites fetch error: {e}")
        return jsonify({"error": "Failed to fetch favorites"}), 500

@app.route('/api/user/favorites', methods=['POST'])
def add_favorite_pair():
    """Add a currency pair to favorites"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        from_currency = data.get('from_currency', '').upper()
        to_currency = data.get('to_currency', '').upper()
        
        if not from_currency or not to_currency:
            return jsonify({"error": "Both currencies are required"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO favorite_pairs (user_id, from_currency, to_currency)
                VALUES (?, ?, ?)
            ''', (user_id, from_currency, to_currency))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": "Pair already in favorites"}), 409
        
        conn.close()
        
        return jsonify({"message": "Favorite pair added successfully"}), 201
        
    except Exception as e:
        logger.error(f"Add favorite error: {e}")
        return jsonify({"error": "Failed to add favorite"}), 500

@app.route('/api/user/favorites/<int:favorite_id>', methods=['DELETE'])
def remove_favorite_pair(favorite_id):
    """Remove a currency pair from favorites"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM favorite_pairs 
            WHERE id = ? AND user_id = ?
        ''', (favorite_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Favorite pair removed successfully"}), 200
        
    except Exception as e:
        logger.error(f"Remove favorite error: {e}")
        return jsonify({"error": "Failed to remove favorite"}), 500

@app.route('/api/user/alerts', methods=['GET'])
def get_rate_alerts():
    """Get user's rate alerts"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, from_currency, to_currency, target_rate, is_active, created_at
            FROM rate_alerts
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        alerts = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "alerts": [{
                "id": a[0],
                "from_currency": a[1],
                "to_currency": a[2],
                "target_rate": a[3],
                "is_active": bool(a[4]),
                "created_at": a[5]
            } for a in alerts]
        }), 200
        
    except Exception as e:
        logger.error(f"Alerts fetch error: {e}")
        return jsonify({"error": "Failed to fetch alerts"}), 500

@app.route('/api/user/alerts', methods=['POST'])
def create_rate_alert():
    """Create a new rate alert"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        from_currency = data.get('from_currency', '').upper()
        to_currency = data.get('to_currency', '').upper()
        target_rate = data.get('target_rate', type=float)
        
        if not from_currency or not to_currency or target_rate is None:
            return jsonify({"error": "All fields are required"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rate_alerts (user_id, from_currency, to_currency, target_rate)
            VALUES (?, ?, ?, ?)
        ''', (user_id, from_currency, to_currency, target_rate))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rate alert created successfully"}), 201
        
    except Exception as e:
        logger.error(f"Create alert error: {e}")
        return jsonify({"error": "Failed to create alert"}), 500

@app.route('/api/user/alerts/<int:alert_id>', methods=['PUT'])
def update_rate_alert(alert_id):
    """Update rate alert status"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE rate_alerts 
            SET is_active = ?
            WHERE id = ? AND user_id = ?
        ''', (is_active, alert_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rate alert updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"Update alert error: {e}")
        return jsonify({"error": "Failed to update alert"}), 500

@app.route('/api/user/alerts/<int:alert_id>', methods=['DELETE'])
def delete_rate_alert(alert_id):
    """Delete a rate alert"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({"error": "Authorization required"}), 401
        
        user_id = validate_session_token(session_token)
        if not user_id:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM rate_alerts 
            WHERE id = ? AND user_id = ?
        ''', (alert_id, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Rate alert deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Delete alert error: {e}")
        return jsonify({"error": "Failed to delete alert"}), 500

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
