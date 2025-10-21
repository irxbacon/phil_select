"""Database operations"""

import os
import shutil
import sqlite3
import sys


def get_database_path():
    """Get database path - always in the current working directory for persistence"""
    # Always use current working directory so database persists across runs
    return os.path.join(os.getcwd(), "philmont_selection.db")


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_db_connection():
    db_path = get_database_path()

    # If database doesn't exist, copy it from embedded resources
    if not os.path.exists(db_path):
        try:
            # Try to copy from PyInstaller bundle
            embedded_db_path = get_resource_path("philmont_selection.db")
            if os.path.exists(embedded_db_path):
                shutil.copy2(embedded_db_path, db_path)
                print(f"Database initialized from embedded copy: {db_path}")
        except Exception as e:
            print(f"Warning: Could not initialize database from embedded copy: {e}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn
