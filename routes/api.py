"""API routes"""

from flask import (Blueprint, jsonify, request)

from database import get_db_connection

from utils.crew import get_current_user
from utils.admin import is_authenticated
from utils.scoring import get_crew_trek_type, PhilmontScorer

api_routes = Blueprint("api_routes", __name__)


@api_routes.route("/api/crews")
def api_crews():
    """API endpoint to list available crews (filtered by user permissions)"""
    if not is_authenticated():
        return jsonify({"error": "Authentication required"}), 401

    conn = get_db_connection()

    user = get_current_user()
    if user["is_admin"]:
        # Admin can see all crews
        crews = conn.execute(
            "SELECT id, crew_name, crew_size FROM crews ORDER BY crew_name"
        ).fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute(
            """
            SELECT id, crew_name, crew_size 
            FROM crews 
            WHERE id = ? 
            ORDER BY crew_name
        """,
            (user["crew_id"],),
        ).fetchall()

    conn.close()

    return jsonify(
        [
            {"id": crew["id"], "name": crew["crew_name"], "size": crew["crew_size"]}
            for crew in crews
        ]
    )


@api_routes.route("/api/calculate")
def api_calculate():
    """API endpoint to recalculate scores"""
    crew_id = request.args.get("crew_id", 1, type=int)
    method = request.args.get("method", "Total")

    trek_type = get_crew_trek_type(crew_id)
    scorer = PhilmontScorer(crew_id, trek_type)
    results = scorer.calculate_itinerary_scores(method)

    # Convert to JSON-friendly format
    json_results = []
    for result in results:
        json_results.append(
            {
                "itinerary_code": result["itinerary"]["itinerary_code"],
                "total_score": result["total_score"],
                "ranking": result["ranking"],
                "components": result["components"],
            }
        )

    return jsonify(json_results)


@api_routes.route("/api/crew_members/<int:crew_id>")
def api_crew_members(crew_id):
    """API endpoint to get crew members for a specific crew"""
    conn = get_db_connection()

    crew_members = conn.execute(
        """
        SELECT id, name, email, age, skill_level
        FROM crew_members 
        WHERE crew_id = ? 
        ORDER BY member_number
    """,
        (crew_id,),
    ).fetchall()

    conn.close()

    # Convert to JSON-friendly format
    members = []
    for member in crew_members:
        members.append(
            {
                "id": member["id"],
                "name": member["name"],
                "email": member["email"],
                "age": member["age"],
                "skill_level": member["skill_level"],
            }
        )

    return jsonify(members)
