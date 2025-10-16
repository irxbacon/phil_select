"""Survey routes"""


from flask import (Blueprint, flash, request, redirect, render_template, url_for)

from database import get_db_connection

from utils.crew import get_programs
from utils.scoring import recalculate_crew_scores

survey_routes = Blueprint("survey_routes", __name__, template_folder="templates")


@survey_routes.route("/survey")
def survey():
    """Crew member program survey page"""
    # Always use crew ID 1 for surveys
    crew_id = 1

    # Get all programs organized by category
    programs = get_programs()

    return render_template("survey.html", programs=programs, selected_crew_id=crew_id)


@survey_routes.route("/survey", methods=["POST"])
def submit_survey():
    """Process crew member program survey submission"""
    # Always use crew ID 1 for survey submissions
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

    # Get form data
    member_type = request.form.get("member_type", "new")
    existing_member_id = safe_int(request.form.get("existing_member_id"))
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    age = safe_int(request.form.get("age"))
    skill_level = safe_int(request.form.get("skill_level", 6))

    # Validate required fields based on member type
    # crew_id is hardcoded to 1, no validation needed

    if member_type == "existing":
        if not existing_member_id:
            flash("Please select an existing crew member.", "error")
            return redirect(url_for("survey"))
    else:
        if not name:
            flash("Please fill in all required fields (Name).", "error")
            return redirect(url_for("survey"))

    try:
        if member_type == "existing" and existing_member_id:
            # Use existing crew member
            member_id = existing_member_id
            # Update their info if provided
            if name or email or age or skill_level:
                conn.execute(
                    """
                    UPDATE crew_members 
                    SET name = COALESCE(?, name), 
                        email = COALESCE(?, email), 
                        age = COALESCE(?, age), 
                        skill_level = COALESCE(?, skill_level)
                    WHERE id = ? AND crew_id = ?
                """,
                    (name or None, email or None, age, skill_level, member_id, crew_id),
                )
        else:
            # Handle new member creation or update existing member by email/name match
            existing_member = None
            if email:
                existing_member = conn.execute(
                    "SELECT * FROM crew_members WHERE crew_id = ? AND email = ?",
                    (crew_id, email),
                ).fetchone()

            if not existing_member and name:
                # Check by name and crew if no email match
                existing_member = conn.execute(
                    "SELECT * FROM crew_members WHERE crew_id = ? AND name = ?",
                    (crew_id, name),
                ).fetchone()

            if existing_member:
                member_id = existing_member["id"]
                # Update existing crew member info including email
                conn.execute(
                    """
                    UPDATE crew_members 
                    SET name = ?, email = ?, age = ?, skill_level = ?
                    WHERE id = ?
                """,
                    (name, email, age, skill_level, member_id),
                )
            else:
                # Get next member number for this crew
                max_member = conn.execute(
                    "SELECT MAX(member_number) as max_num FROM crew_members WHERE crew_id = ?",
                    (crew_id,),
                ).fetchone()
                member_number = (max_member["max_num"] or 0) + 1

                # Insert new crew member with email
                cursor = conn.execute(
                    """
                    INSERT INTO crew_members (crew_id, member_number, name, email, age, skill_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (crew_id, member_number, name, email, age, skill_level),
                )
                member_id = cursor.lastrowid

        # Process program scores
        programs = get_programs()

        # Delete existing scores for this crew member
        conn.execute(
            "DELETE FROM program_scores WHERE crew_member_id = ?", (member_id,)
        )

        # Insert new scores
        for program in programs:
            score_value = safe_int(request.form.get(f"program_{program['id']}", 10))
            if score_value is not None:
                conn.execute(
                    """
                    INSERT INTO program_scores (crew_id, crew_member_id, program_id, score)
                    VALUES (?, ?, ?, ?)
                """,
                    (crew_id, member_id, program["id"], score_value),
                )

        conn.commit()

        # Recalculate crew program scores after survey update
        try:
            recalculate_crew_scores(crew_id)
            flash(
                f"Survey submitted successfully for {name}! Crew scores have been updated.",
                "success",
            )
        except Exception as e:
            flash(
                f"Survey submitted for {name}, but there was an issue updating crew scores: {str(e)}",
                "warning",
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error submitting survey: {str(e)}", "error")
        return redirect(url_for("survey"))
    finally:
        conn.close()

    return redirect(url_for("survey"))
