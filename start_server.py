#!/usr/bin/env python3
"""
Simple server starter script
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Import and run the app
from app import app, init_db

if __name__ == '__main__':
    print("Starting Currency Converter Server...")
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print("Server starting on http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    try:
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Make sure port 5000 is not already in use")
