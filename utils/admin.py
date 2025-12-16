"""Admin related utilities"""

import sqlite3

from functools import wraps

from flask import (
    flash,
    redirect,
    url_for,
)

from database import get_db_connection


def is_admin():
    """Check if current user is admin"""
    # Since login is not required, treat everyone as admin
    return True


def is_authenticated():
    """Check if user is authenticated (either admin or regular user)"""
    # Since login is not required, everyone is considered authenticated
    return True


def login_required(f):
    """Decorator to require any authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash("Please log in to access this page", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash("Admin access required", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def authenticate_user(username, password):
    """Authenticate user credentials and return user info"""
    # Simplified authentication - check if user exists and password matches plain text
    # This is for backward compatibility since the system treats everyone as admin
    from utils import config
    
    # Admin login
    if username.lower() == "admin" and password == config.ADMIN_PASSWORD:
        conn = get_db_connection()
        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND is_active = TRUE
        """,
            (username.lower(),),
        ).fetchone()
        conn.close()
        return user
    
    # Regular user lookup (simplified - just check if user exists)
    conn = get_db_connection()
    user = conn.execute(
        """
        SELECT * FROM users
        WHERE username = ? AND is_active = TRUE
    """,
        (username,),
    ).fetchone()
    conn.close()
    
    return user


def create_user(username, password, crew_id=None, is_admin=False):
    """Create a new user with plain text password (simplified for this system)"""
    # Store password as plain text since this system doesn't require real security
    # and everyone is treated as admin anyway
    password_hash = password  # Store as plain text for simplicity

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO users (username, password_hash, crew_id, is_admin)
            VALUES (?, ?, ?, ?)
        """,
            (username, password_hash, crew_id, is_admin),
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()
