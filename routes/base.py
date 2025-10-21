"""Base API routes"""

from flask import (Blueprint, flash, redirect, render_template, request, session, url_for)

from database import get_db_connection

from utils.crew import get_user_crew_id, get_current_user, get_crew_info
from utils.admin import is_admin

base_routes = Blueprint("base_routes", __name__, template_folder="templates")


@base_routes.route("/")
def index():
    """Home page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()

    conn = get_db_connection()

    if is_admin():
        # Admin sees all crews
        crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()
        if not crew_id and crews:
            crew_id = crews[0]["id"]
            session["admin_crew_id"] = crew_id  # Remember admin's choice
    else:
        # Regular users only see their assigned crew
        user = get_current_user()
        if user and user["crew_id"]:
            crews = conn.execute(
                "SELECT * FROM crews WHERE id = ?", (user["crew_id"],)
            ).fetchall()
            crew_id = user["crew_id"]
        else:
            flash("No crew assigned to your account. Contact administrator.", "error")
            return redirect(url_for("admin_routes.logout"))

    conn.close()

    return render_template("index.html", crews=crews, selected_crew_id=crew_id)


@base_routes.route("/preferences")
def preferences():
    """Crew preferences page"""
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

    crew, crew_members, preferences = get_crew_info(crew_id)

    # Calculate average skill score
    avg_skill_score = None
    if crew_members:
        skill_scores = [
            member["skill_level"]
            for member in crew_members
            if member["skill_level"] is not None
        ]
        if skill_scores:
            avg_skill_score = round(sum(skill_scores) / len(skill_scores), 1)

    return render_template(
        "preferences.html",
        crew=crew,
        crew_members=crew_members,
        preferences=preferences,
        crews=crews,
        selected_crew_id=crew_id,
        avg_skill_score=avg_skill_score,
    )


@base_routes.route("/preferences", methods=["POST"])
def save_preferences():
    """Save crew preferences"""
    # Always use crew ID 1 for preferences
    crew_id = 1

    # No authentication required - access allowed

    conn = get_db_connection()

    def safe_int(value):
        """Safely convert form value to int or None"""
        if not value or value.strip() == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    # Check if preferences exist
    existing = conn.execute(
        "SELECT id FROM crew_preferences WHERE crew_id = ?", (crew_id,)
    ).fetchone()

    if existing:
        # Update existing preferences
        conn.execute(
            """
            UPDATE crew_preferences SET
                area_important = ?,
                area_rank_south = ?,
                area_rank_central = ?,
                area_rank_north = ?,
                area_rank_valle_vidal = ?,
                max_altitude_important = ?,
                total_elevation_gain_important = ?,
                altitude_change_important = ?,
                daily_altitude_change_threshold = ?,
                difficulty_challenging = ?,
                difficulty_rugged = ?,
                difficulty_strenuous = ?,
                difficulty_super_strenuous = ?,
                climb_baldy = ?,
                climb_phillips = ?,
                climb_tooth = ?,
                climb_inspiration_point = ?,
                climb_trail_peak = ?,
                climb_others = ?,
                hike_in_preference = ?,
                hike_out_preference = ?,
                programs_important = ?,
                adult_program_weight_enabled = ?,
                adult_program_weight_percent = ?,
                max_dry_camps = ?,
                showers_required = ?,
                layovers_required = ?,
                prefer_low_starting_food = ?,
                prefer_shorter_resupply = ?,
                trek_type = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE crew_id = ?
        """,
            (
                "area_important" in request.form,
                safe_int(request.form.get("area_rank_south")),
                safe_int(request.form.get("area_rank_central")),
                safe_int(request.form.get("area_rank_north")),
                safe_int(request.form.get("area_rank_valle_vidal")),
                "max_altitude_important" in request.form,
                "total_elevation_gain_important" in request.form,
                "altitude_change_important" in request.form,
                safe_int(request.form.get("daily_altitude_change_threshold")),
                "difficulty_challenging" in request.form,
                "difficulty_rugged" in request.form,
                "difficulty_strenuous" in request.form,
                "difficulty_super_strenuous" in request.form,
                "climb_baldy" in request.form,
                "climb_phillips" in request.form,
                "climb_tooth" in request.form,
                "climb_inspiration_point" in request.form,
                "climb_trail_peak" in request.form,
                "climb_others" in request.form,
                "hike_in_preference" in request.form,
                "hike_out_preference" in request.form,
                "programs_important" in request.form,
                "adult_program_weight_enabled" in request.form,
                safe_int(request.form.get("adult_program_weight_percent", 50)),
                safe_int(request.form.get("max_dry_camps")),
                "showers_required" in request.form,
                "layovers_required" in request.form,
                "prefer_low_starting_food" in request.form,
                "prefer_shorter_resupply" in request.form,
                request.form.get("trek_type", "12-day"),
                crew_id,
            ),
        )
    else:
        # Insert new preferences
        conn.execute(
            """
            INSERT INTO crew_preferences
            (crew_id, area_important, area_rank_south, area_rank_central, area_rank_north, area_rank_valle_vidal,
             max_altitude_important, total_elevation_gain_important, altitude_change_important, daily_altitude_change_threshold, difficulty_challenging, difficulty_rugged,
             difficulty_strenuous, difficulty_super_strenuous, climb_baldy, climb_phillips, climb_tooth,
             climb_inspiration_point, climb_trail_peak, climb_others, hike_in_preference, hike_out_preference, programs_important, adult_program_weight_enabled, adult_program_weight_percent, max_dry_camps, showers_required, layovers_required, prefer_low_starting_food, prefer_shorter_resupply)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                crew_id,
                "area_important" in request.form,
                safe_int(request.form.get("area_rank_south")),
                safe_int(request.form.get("area_rank_central")),
                safe_int(request.form.get("area_rank_north")),
                safe_int(request.form.get("area_rank_valle_vidal")),
                "max_altitude_important" in request.form,
                "total_elevation_gain_important" in request.form,
                "altitude_change_important" in request.form,
                safe_int(request.form.get("daily_altitude_change_threshold")),
                "difficulty_challenging" in request.form,
                "difficulty_rugged" in request.form,
                "difficulty_strenuous" in request.form,
                "difficulty_super_strenuous" in request.form,
                "climb_baldy" in request.form,
                "climb_phillips" in request.form,
                "climb_tooth" in request.form,
                "climb_inspiration_point" in request.form,
                "climb_trail_peak" in request.form,
                "climb_others" in request.form,
                "hike_in_preference" in request.form,
                "hike_out_preference" in request.form,
                "programs_important" in request.form,
                "adult_program_weight_enabled" in request.form,
                safe_int(request.form.get("adult_program_weight_percent", 50)),
                safe_int(request.form.get("max_dry_camps")),
                "showers_required" in request.form,
                "layovers_required" in request.form,
                "prefer_low_starting_food" in request.form,
                "prefer_shorter_resupply" in request.form,
                request.form.get("trek_type", "12-day"),
            ),
        )

    conn.commit()
    conn.close()
    flash("Preferences saved successfully!", "success")

    return redirect(url_for("base_routes.preferences", crew_id=crew_id))
