#!/usr/bin/env python3
"""
Simple script to create database tables
"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///instance/plc_monitoring.db'

# Make sure instance directory exists
os.makedirs('instance', exist_ok=True)

from app import create_app
from db import db

# Create Flask app
app, socketio = create_app()

# Create all tables within app context
with app.app_context():
    try:
        db.create_all()
        print(" Database tables created successfully!")

        # Verify tables exist
        tables = list(db.metadata.tables.keys())
        print(f"📊 Created tables: {tables}")

    except Exception as e:
        print(f" Error creating tables: {e}")
        raise
