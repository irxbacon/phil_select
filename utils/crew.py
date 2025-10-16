"""User related utilities"""

from flask import (
    request,
    session,
)

from database import get_db_connection


def get_current_user():
    """Get current authenticated user info"""
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db_connection()
    user = conn.execute(
        """
        SELECT u.*, c.crew_name 
        FROM users u 
        LEFT JOIN crews c ON u.crew_id = c.id 
        WHERE u.id = ? AND u.is_active = TRUE
    """,
        (user_id,),
    ).fetchone()
    conn.close()
    return user


def get_user_crew_id():
    """Get the crew_id that the current user should see"""
    # Since login is not required, return the first crew or crew from query parameter
    crew_id = request.args.get("crew_id", type=int)
    if crew_id:
        return crew_id

    # Return first available crew as default
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM crews ORDER BY id LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    if result:
        return result["id"]
    return 1  # Fallback to crew id 1



def get_crew_info(crew_id=1):
    """Get crew information"""
    conn = get_db_connection()

    crew = conn.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchone()
    crew_members = conn.execute(
        "SELECT * FROM crew_members WHERE crew_id = ? ORDER BY member_number",
        (crew_id,),
    ).fetchall()
    preferences = conn.execute(
        "SELECT * FROM crew_preferences WHERE crew_id = ?", (crew_id,)
    ).fetchone()

    conn.close()
    return crew, crew_members, preferences


def get_programs():
    """Get all programs"""
    conn = get_db_connection()
    programs = conn.execute("SELECT * FROM programs ORDER BY category, name").fetchall()
    conn.close()
    return programs


def get_existing_scores(crew_id=1):
    """Get existing program scores for a crew"""
    conn = get_db_connection()
    scores = conn.execute(
        """
        SELECT crew_member_id, program_id, score 
        FROM program_scores 
        WHERE crew_id = ?
    """,
        (crew_id,),
    ).fetchall()
    conn.close()

    score_dict = {}
    for score in scores:
        key = f"{score['crew_member_id']}_{score['program_id']}"
        score_dict[key] = score["score"]

    return score_dict
