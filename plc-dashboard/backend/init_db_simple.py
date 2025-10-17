#!/usr/bin/env python3
"""
Simple database initialization script
Creates all tables defined in models.py
"""
import os
import sys

# Set DATABASE_URL before importing app
os.environ['DATABASE_URL'] = 'sqlite:///instance/plc_monitoring.db'

# Import app after setting environment
from app import create_app
from db import db

def init_database():
    """Initialize database with all tables"""
    app, socketio = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database initialized successfully!")
        print(f"📊 Tables created: {list(db.metadata.tables.keys())}")

if __name__ == "__main__":
    init_database()
