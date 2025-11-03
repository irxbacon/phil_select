"""Scores routes"""

import json
import re
import requests
from flask import (Blueprint, flash, redirect, render_template, request, session, url_for, jsonify)

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


@scoring_routes.route("/import-google-sheets", methods=["POST"])
def import_google_sheets():
    """Import scores from Google Sheets"""
    try:
        data = request.get_json()
        sheet_url = data.get("sheet_url")
        sheet_name = data.get("sheet_name", "Form Responses 1")
        overwrite = data.get("overwrite", True)
        crew_id = data.get("crew_id")

        if not sheet_url or not crew_id:
            return jsonify({"success": False, "error": "Missing sheet URL or crew ID"})

        # Extract sheet ID from URL
        sheet_id = extract_sheet_id(sheet_url)
        if not sheet_id:
            return jsonify({"success": False, "error": "Invalid Google Sheets URL"})

        # Convert to CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

        # Fetch the CSV data
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()

        # Parse CSV data
        import csv
        from io import StringIO
        
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        rows = list(reader)

        if len(rows) < 2:
            return jsonify({"success": False, "error": "Sheet must have at least a header row and one data row"})

        # Get header row (program names)
        headers = [h.strip().strip('"') for h in rows[0]]
        
        # Get crew members and programs from database
        conn = get_db_connection()
        
        crew_members = conn.execute(
            "SELECT id, name, member_number FROM crew_members WHERE crew_id = ? ORDER BY member_number",
            (crew_id,)
        ).fetchall()
        
        programs = conn.execute(
            "SELECT id, name, code FROM programs ORDER BY category, name"
        ).fetchall()
        
        # Create mapping of program names to IDs
        program_name_to_id = {}
        for program in programs:
            program_name_to_id[program['name'].strip().lower()] = program['id']
            if program['code']:
                program_name_to_id[program['code'].strip().lower()] = program['id']
        
        # Create mapping of member names to IDs
        member_name_to_id = {}
        for member in crew_members:
            if member['name']:
                member_name_to_id[member['name'].strip().lower()] = member['id']
            member_name_to_id[f"member {member['member_number']}"] = member['id']

        # Find program columns (skip first five columns: ID, Email, Name, Age, Skill Level)
        program_columns = {}
        for i, header in enumerate(headers[5:], 5):  # Skip first five columns
            header_lower = header.strip().lower()
            if header_lower in program_name_to_id:
                program_columns[i] = program_name_to_id[header_lower]

        if not program_columns:
            return jsonify({"success": False, "error": "No matching programs found in sheet headers"})

        # Process data rows
        scores_imported = 0
        members_processed = 0
        imported_scores = {}
        new_members_added = 0
        members_updated = 0

        for row in rows[1:]:  # Skip header row
            if len(row) < 5:  # Need at least ID, Email, Name, Age, and Skill Level columns
                continue
                
            # Get member name from third column (index 2) - email is now at index 1
            member_name_original = row[2].strip().strip('"')
            member_name = member_name_original.lower()
            
            # Email is at index 1 (ignored but available if needed in future)
            # email = row[1].strip().strip('"') if len(row) > 1 else ""
            
            # Get age and skill level from columns 3 and 4 (shifted due to email column)
            try:
                age = int(row[3].strip().strip('"')) if row[3].strip().strip('"') else 16
                age = max(1, min(age, 99))  # Clamp age between 1 and 99
            except (ValueError, IndexError):
                age = 16  # Default age
            
            try:
                skill_level = int(row[4].strip().strip('"')) if row[4].strip().strip('"') else 1
                skill_level = max(1, min(skill_level, 5))  # Clamp skill level between 1 and 5
            except (ValueError, IndexError):
                skill_level = 1  # Default skill level
            
            # Find matching member
            member_id = member_name_to_id.get(member_name)
            
            # If member doesn't exist, add them to the database
            if not member_id:
                # Get the next available member number for this crew
                max_member_result = conn.execute(
                    "SELECT MAX(member_number) FROM crew_members WHERE crew_id = ?",
                    (crew_id,)
                ).fetchone()
                next_member_number = (max_member_result[0] or 0) + 1
                
                # Insert new member with age and skill level from sheet
                cursor = conn.execute(
                    "INSERT INTO crew_members (crew_id, member_number, name, age, skill_level) VALUES (?, ?, ?, ?, ?)",
                    (crew_id, next_member_number, member_name_original, age, skill_level)
                )
                member_id = cursor.lastrowid
                
                # Add to member mapping for future reference in this import
                member_name_to_id[member_name] = member_id
                new_members_added += 1
            else:
                # Update existing member's age and skill level
                conn.execute(
                    "UPDATE crew_members SET age = ?, skill_level = ? WHERE id = ?",
                    (age, skill_level, member_id)
                )
                members_updated += 1
            
            members_processed += 1

            # Process scores for this member across all program columns
            for col_idx, program_id in program_columns.items():
                if col_idx < len(row):
                    try:
                        score_str = row[col_idx].strip().strip('"')
                        if score_str:
                            score = float(score_str)
                            if 0 <= score <= 20:
                                # Delete existing score if overwriting
                                if overwrite:
                                    conn.execute(
                                        "DELETE FROM program_scores WHERE crew_id = ? AND crew_member_id = ? AND program_id = ?",
                                        (crew_id, member_id, program_id)
                                    )
                                
                                # Insert new score
                                conn.execute(
                                    "INSERT INTO program_scores (crew_id, crew_member_id, program_id, score) VALUES (?, ?, ?, ?)",
                                    (crew_id, member_id, program_id, int(score))
                                )
                                
                                # Store for frontend update
                                imported_scores[f"{member_id}_{program_id}"] = int(score)
                                scores_imported += 1
                    except (ValueError, IndexError):
                        continue

        conn.commit()
        conn.close()

        if members_processed == 0:
            return jsonify({"success": False, "error": "No matching crew members found in name column"})

        return jsonify({
            "success": True,
            "scores_imported": scores_imported,
            "members_processed": members_processed,
            "new_members_added": new_members_added,
            "members_updated": members_updated,
            "scores": imported_scores
        })

    except requests.RequestException as e:
        return jsonify({"success": False, "error": f"Failed to fetch Google Sheet: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Import failed: {str(e)}"})


def extract_sheet_id(url):
    """Extract Google Sheets ID from various URL formats"""
    patterns = [
        r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'^([a-zA-Z0-9-_]+)$'  # Just the ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
