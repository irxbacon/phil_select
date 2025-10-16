"""Program routes"""


from flask import (Blueprint, request, session, redirect, render_template, url_for, flash)

from database import get_db_connection

from utils.crew import get_user_crew_id
from utils.admin import is_admin
from utils.scoring import get_crew_trek_type, PhilmontScorer

program_routes = Blueprint("program_routes", __name__, template_folder="templates")


@program_routes.route("/program_chart")
def program_chart():
    """Program scoring chart page"""
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
        return redirect(url_for("logout"))

    conn = get_db_connection()

    # No authentication required - access allowed

    if is_admin():
        # Admin sees all crews
        crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()
    else:
        # Regular user sees only their crew
        crews = conn.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchall()

    # Get program scores
    trek_type = get_crew_trek_type(crew_id)
    scorer = PhilmontScorer(crew_id, trek_type)
    program_scores = scorer.get_program_scores(method)

    # Apply program factor to match itinerary calculations
    program_factor = scorer.get_score_factor("programFactor")

    # Get program names and create chart data
    programs = conn.execute("SELECT id, name FROM programs ORDER BY name").fetchall()

    chart_data = []
    for program in programs:
        raw_score = program_scores.get(program["id"], 0)
        factored_score = raw_score * program_factor
        chart_data.append(
            {"id": program["id"], "name": program["name"], "score": factored_score}
        )

    # Sort by score (descending)
    chart_data.sort(key=lambda x: x["score"], reverse=True)

    conn.close()

    return render_template(
        "program_chart.html",
        chart_data=chart_data,
        method=method,
        crews=crews,
        selected_crew_id=crew_id,
        is_admin=is_admin(),
    )


@program_routes.route("/itinerary/<code>")
def itinerary_detail(code):
    """Detailed view of a specific itinerary"""
    conn = get_db_connection()

    # Query the unified itineraries table
    itinerary = conn.execute(
        "SELECT * FROM itineraries WHERE itinerary_code = ?", (code,)
    ).fetchone()

    if not itinerary:
        flash(f"Itinerary {code} not found", "error")
        return redirect(url_for("results"))

    # Get camps for this itinerary
    camps = conn.execute(
        """
        SELECT ic.day_number, c.name, c.elevation, c.country, c.is_staffed, c.is_trail_camp
        FROM itinerary_camps ic
        JOIN camps c ON ic.camp_id = c.id
        WHERE ic.itinerary_id = ?
        ORDER BY ic.day_number
    """,
        (itinerary["id"],),
    ).fetchall()

    conn.close()

    return render_template("itinerary_detail.html", itinerary=itinerary, camps=camps)
