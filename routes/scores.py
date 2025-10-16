"""Scores routes"""


from flask import (Blueprint, flash, redirect, render_template, request, session, url_for)

from database import get_db_connection

from utils.admin import is_admin
from utils.crew import get_crew_info, get_programs, get_user_crew_id, get_existing_scores
from utils.scoring import get_crew_trek_type, PhilmontScorer

scoring_routes = Blueprint("scoring_routes", __name__, template_folder="templates")


@scoring_routes.route("/scores")
def scores():
    """Program scoring page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()

    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get("crew_id", type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session["admin_crew_id"] = crew_id

    if not crew_id:
        flash("No crew available. Contact administrator.", "error")
        return redirect(url_for("admin_routes.logout"))

    conn = get_db_connection()

    # No authentication required - access allowed

    if is_admin():
        # Admin sees all crews
        crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchall()

    conn.close()

    crew, crew_members, _ = get_crew_info(crew_id)
    programs = get_programs()
    existing_scores = get_existing_scores(crew_id)

    return render_template(
        "scores.html",
        crew=crew,
        crew_members=crew_members,
        programs=programs,
        existing_scores=existing_scores,
        crews=crews,
        selected_crew_id=crew_id,
    )


@scoring_routes.route("/scores", methods=["POST"])
def save_scores():
    """Save program scores"""
    # Always use crew ID 1 for scores
    crew_id = 1

    # Verify crew access permission
    # No authentication required - access allowed

    conn = get_db_connection()

    # Delete existing scores for this crew
    conn.execute("DELETE FROM program_scores WHERE crew_id = ?", (crew_id,))

    # Save new scores
    for key, value in request.form.items():
        if key.startswith("score_") and value and value.strip():
            parts = key.split("_")
            if len(parts) == 3:
                try:
                    member_id = int(parts[1])
                    program_id = int(parts[2])
                    score_value = int(value)
                except (ValueError, TypeError):
                    continue  # Skip invalid values

                conn.execute(
                    """
                    INSERT INTO program_scores (crew_id, crew_member_id, program_id, score)
                    VALUES (?, ?, ?, ?)
                """,
                    (crew_id, member_id, program_id, score_value),
                )

    conn.commit()
    conn.close()
    flash("Scores saved successfully!", "success")

    return redirect(url_for("scoring_routes.scores", crew_id=crew_id))


@scoring_routes.route("/results")
def results():
    """Results and rankings page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    method = request.args.get("method", "Total")

    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get("crew_id", type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session["admin_crew_id"] = crew_id

    if not crew_id:
        flash("No crew available. Contact administrator.", "error")
        return redirect(url_for("admin_routes.logout"))

    conn = get_db_connection()

    # No authentication required - access allowed

    if is_admin():
        # Admin sees all crews
        crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchall()
        crews = conn.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchall()

    conn.close()

    if not crew_id:
        flash("No crews found. Please create a crew first.", "error")
        return redirect(url_for("admin_routes.admin"))

    trek_type = get_crew_trek_type(crew_id)
    scorer = PhilmontScorer(crew_id, trek_type)
    results = scorer.calculate_itinerary_scores(method)

    return render_template(
        "results.html",
        results=results,
        calculation_method=method,
        crews=crews,
        selected_crew_id=crew_id,
    )
