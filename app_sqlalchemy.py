#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sqlite3
import argparse

app = Flask(__name__)
app.config["SECRET_KEY"] = "philmont-trek-selection-2025"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///philmont_selection.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


def get_db_connection():
    conn = sqlite3.connect("philmont_selection.db")
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn


# ===================================
# Database Models
# ===================================


class Program(db.Model):
    __tablename__ = "programs"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    old_name_comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class Camp(db.Model):
    __tablename__ = "camps"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(20))
    easting = db.Column(db.Integer)
    northing = db.Column(db.Integer)
    elevation = db.Column(db.Integer)
    has_commissary = db.Column(db.Boolean, default=False)
    has_trading_post = db.Column(db.Boolean, default=False)
    is_staffed = db.Column(db.Boolean, default=False)
    is_trail_camp = db.Column(db.Boolean, default=False)
    is_dry_camp = db.Column(db.Boolean, default=False)
    has_showers = db.Column(db.Boolean, default=False)
    camp_map = db.Column(db.String(20))
    added_year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class Itinerary(db.Model):
    __tablename__ = "itineraries"
    id = db.Column(db.Integer, primary_key=True)
    itinerary_code = db.Column(db.String(10), unique=True, nullable=False)
    expedition_number = db.Column(db.String(20))
    difficulty = db.Column(db.String(20))
    distance = db.Column(db.Integer)
    days_food_from_base = db.Column(db.Integer)
    max_days_food = db.Column(db.Integer)
    staffed_camps = db.Column(db.Integer)
    trail_camps = db.Column(db.Integer)
    layovers = db.Column(db.Integer)
    total_camps = db.Column(db.Integer)
    dry_camps = db.Column(db.Integer)
    min_altitude = db.Column(db.Integer)
    max_altitude = db.Column(db.Integer)
    total_elevation_gain = db.Column(db.Integer)
    avg_daily_elevation_change = db.Column(db.Float)
    description = db.Column(db.Text)
    starts_at = db.Column(db.String(100))
    ends_at = db.Column(db.String(100))
    via_tooth = db.Column(db.Boolean, default=False)
    crosses_us64 = db.Column(db.Boolean, default=False)
    us64_crossing_day = db.Column(db.Integer)
    us64_crossing_direction = db.Column(db.String(20))
    baldy_mountain = db.Column(db.Boolean, default=False)
    inspiration_point = db.Column(db.Boolean, default=False)
    mount_phillips = db.Column(db.Boolean, default=False)
    mountaineering = db.Column(db.Boolean, default=False)
    tooth_of_time = db.Column(db.Boolean, default=False)
    trail_peak = db.Column(db.Boolean, default=False)
    covers_south = db.Column(db.Boolean, default=False)
    covers_central = db.Column(db.Boolean, default=False)
    covers_north = db.Column(db.Boolean, default=False)
    covers_valle_vidal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class Crew(db.Model):
    __tablename__ = "crews"
    id = db.Column(db.Integer, primary_key=True)
    crew_name = db.Column(db.String(100))
    crew_size = db.Column(db.Integer, default=9)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class CrewMember(db.Model):
    __tablename__ = "crew_members"
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crews.id"), nullable=False)
    member_number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    skill_level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CrewPreferences(db.Model):
    __tablename__ = "crew_preferences"
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crews.id"), nullable=False)
    area_important = db.Column(db.Boolean, default=False)
    area_rank_south = db.Column(db.Integer)
    area_rank_central = db.Column(db.Integer)
    area_rank_north = db.Column(db.Integer)
    area_rank_valle_vidal = db.Column(db.Integer)
    max_altitude_important = db.Column(db.Boolean, default=False)
    max_altitude_threshold = db.Column(db.Integer)
    altitude_change_important = db.Column(db.Boolean, default=False)
    daily_altitude_change_threshold = db.Column(db.Integer)
    difficulty_challenging = db.Column(db.Boolean, default=True)
    difficulty_rugged = db.Column(db.Boolean, default=True)
    difficulty_strenuous = db.Column(db.Boolean, default=True)
    difficulty_super_strenuous = db.Column(db.Boolean, default=True)
    climb_baldy = db.Column(db.Boolean, default=False)
    climb_phillips = db.Column(db.Boolean, default=False)
    climb_tooth = db.Column(db.Boolean, default=False)
    climb_inspiration_point = db.Column(db.Boolean, default=False)
    climb_others = db.Column(db.Boolean, default=False)
    climb_trail_peak = db.Column(db.Boolean, default=False)
    hike_in_preference = db.Column(db.Boolean, default=True)
    hike_out_preference = db.Column(db.Boolean, default=True)
    programs_important = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProgramScore(db.Model):
    __tablename__ = "program_scores"
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crews.id"), nullable=False)
    crew_member_id = db.Column(
        db.Integer, db.ForeignKey("crew_members.id"), nullable=False
    )
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CrewResult(db.Model):
    __tablename__ = "crew_results"
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crews.id"), nullable=False)
    itinerary_id = db.Column(
        db.Integer, db.ForeignKey("itineraries.id"), nullable=False
    )
    total_score = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.Integer)
    choice_number = db.Column(db.Integer)
    program_score = db.Column(db.Float, default=0)
    difficulty_score = db.Column(db.Float, default=0)
    area_score = db.Column(db.Float, default=0)
    altitude_score = db.Column(db.Float, default=0)
    distance_score = db.Column(db.Float, default=0)
    calculation_method = db.Column(db.String(20), default="Total")
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===================================
# Scoring Logic (Replicated from Excel)
# ===================================


class PhilmontScorer:
    def __init__(self, crew_id):
        self.crew_id = crew_id

    def get_program_scores(self, method="Total"):
        """Calculate program scores using specified method (Total, Average, Median, Mode)"""
        conn = sqlite3.connect("philmont_selection.db")

        # Get all program scores for the crew
        query = """
            SELECT p.id, p.name, ps.score
            FROM programs p
            JOIN program_scores ps ON p.id = ps.program_id
            WHERE ps.crew_id = ?
            ORDER BY p.id, ps.crew_member_id
        """

        cursor = conn.execute(query, (self.crew_id,))
        results = cursor.fetchall()

        program_scores = {}
        current_program = None
        current_scores = []

        for program_id, program_name, score in results:
            if current_program != program_id:
                if current_program is not None and current_scores:
                    program_scores[current_program] = self._calculate_aggregate(
                        current_scores, method
                    )
                current_program = program_id
                current_scores = [score]
            else:
                current_scores.append(score)

        # Don't forget the last program
        if current_program is not None and current_scores:
            program_scores[current_program] = self._calculate_aggregate(
                current_scores, method
            )

        conn.close()
        return program_scores

    def _calculate_aggregate(self, scores, method):
        """Calculate aggregate score using specified method"""
        if method == "Total":
            return sum(scores)
        elif method == "Average":
            return sum(scores) / len(scores)
        elif method == "Median":
            sorted_scores = sorted(scores)
            n = len(sorted_scores)
            if n % 2 == 0:
                return (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
            else:
                return sorted_scores[n // 2]
        elif method == "Mode":
            from collections import Counter

            counter = Counter(scores)
            return counter.most_common(1)[0][0]
        else:
            return sum(scores)  # Default to total

    def calculate_itinerary_scores(self, method="Total"):
        """Calculate total scores for all itineraries"""
        program_scores = self.get_program_scores(method)
        crew_prefs = self._get_crew_preferences()

        conn = sqlite3.connect("philmont_selection.db")

        # Get all itineraries
        cursor = conn.execute("SELECT * FROM itineraries ORDER BY itinerary_code")
        itineraries = cursor.fetchall()

        results = []

        for itin in itineraries:
            itin_dict = dict(zip([col[0] for col in cursor.description], itin))

            score_components = {
                "program_score": self._calculate_program_score(
                    itin_dict["id"], program_scores, conn
                ),
                "difficulty_score": self._calculate_difficulty_score(
                    itin_dict, crew_prefs
                ),
                "area_score": self._calculate_area_score(itin_dict, crew_prefs),
                "altitude_score": self._calculate_altitude_score(itin_dict, crew_prefs),
                "distance_score": self._calculate_distance_score(itin_dict, crew_prefs),
            }

            total_score = sum(score_components.values())

            results.append(
                {
                    "itinerary": itin_dict,
                    "total_score": total_score,
                    "components": score_components,
                }
            )

        # Sort by total score (descending)
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # Add rankings
        for i, result in enumerate(results, 1):
            result["ranking"] = i

        conn.close()
        return results

    def _get_crew_preferences(self):
        """Get crew preferences"""
        conn = sqlite3.connect("philmont_selection.db")
        cursor = conn.execute(
            "SELECT * FROM crew_preferences WHERE crew_id = ?", (self.crew_id,)
        )
        prefs = cursor.fetchone()
        conn.close()

        if prefs:
            # Convert to dict
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, prefs))
        else:
            return {}

    def _calculate_program_score(self, itinerary_id, program_scores, conn):
        """Calculate program score for an itinerary"""
        # Get programs available for this itinerary
        cursor = conn.execute(
            """
            SELECT ip.program_id 
            FROM itinerary_programs ip 
            WHERE ip.itinerary_id = ? AND ip.is_available = 1
        """,
            (itinerary_id,),
        )

        available_programs = [row[0] for row in cursor.fetchall()]

        # Sum scores for available programs
        total_score = 0
        for program_id in available_programs:
            if program_id in program_scores:
                total_score += program_scores[program_id]

        # Apply program factor (typically 1.5x)
        program_factor = 1.5
        return total_score * program_factor

    def _calculate_difficulty_score(self, itinerary, crew_prefs):
        """Calculate difficulty-based score"""
        difficulty = itinerary.get("difficulty", "")

        # Check if crew accepts this difficulty level
        difficulty_accepted = False
        if difficulty == "C" and crew_prefs.get("difficulty_challenging", True):
            difficulty_accepted = True
        elif difficulty == "R" and crew_prefs.get("difficulty_rugged", True):
            difficulty_accepted = True
        elif difficulty == "S" and crew_prefs.get("difficulty_strenuous", True):
            difficulty_accepted = True
        elif difficulty == "SS" and crew_prefs.get("difficulty_super_strenuous", True):
            difficulty_accepted = True

        return 100 if difficulty_accepted else 0

    def _calculate_area_score(self, itinerary, crew_prefs):
        """Calculate area preference score"""
        if not crew_prefs.get("area_important", False):
            return 0

        area_scores = {
            "covers_south": crew_prefs.get("area_rank_south", 0),
            "covers_central": crew_prefs.get("area_rank_central", 0),
            "covers_north": crew_prefs.get("area_rank_north", 0),
            "covers_valle_vidal": crew_prefs.get("area_rank_valle_vidal", 0),
        }

        score = 0
        for area_field, rank in area_scores.items():
            if itinerary.get(area_field, False) and rank:
                # Higher rank (1-4) gives more points
                score += (5 - rank) * 25

        return score

    def _calculate_altitude_score(self, itinerary, crew_prefs):
        """Calculate altitude-based score"""
        score = 0

        max_altitude = itinerary.get("max_altitude", 0)
        if crew_prefs.get("max_altitude_important", False):
            threshold = crew_prefs.get("max_altitude_threshold", 10000)
            if max_altitude <= threshold:
                score += 50

        # Add more altitude scoring logic as needed
        return score

    def _calculate_distance_score(self, itinerary, crew_prefs):
        """Calculate distance-based score"""
        # For now, return a neutral score
        # Could add distance preferences in the future
        distance = itinerary.get("distance", 0)
        return max(0, 100 - (distance - 50))  # Prefer distances around 50 miles


# ===================================
# Routes
# ===================================


@app.route("/")
def index():
    """Home page"""
    return render_template("index.html")


@app.route("/preferences")
def preferences():
    """Crew preferences page"""
    crew_id = 1  # Default to sample crew

    # Get current crew info
    crew = Crew.query.get(crew_id)
    crew_members = (
        CrewMember.query.filter_by(crew_id=crew_id)
        .order_by(CrewMember.member_number)
        .all()
    )
    preferences = CrewPreferences.query.filter_by(crew_id=crew_id).first()

    return render_template(
        "preferences.html",
        crew=crew,
        crew_members=crew_members,
        preferences=preferences,
    )


@app.route("/preferences", methods=["POST"])
def save_preferences():
    """Save crew preferences"""
    crew_id = 1  # Default to sample crew

    # Get or create preferences record
    preferences = CrewPreferences.query.filter_by(crew_id=crew_id).first()
    if not preferences:
        preferences = CrewPreferences(crew_id=crew_id)
        db.session.add(preferences)

    # Update preferences from form
    preferences.area_important = "area_important" in request.form
    preferences.area_rank_south = int(request.form.get("area_rank_south", 0)) or None
    preferences.area_rank_central = (
        int(request.form.get("area_rank_central", 0)) or None
    )
    preferences.area_rank_north = int(request.form.get("area_rank_north", 0)) or None
    preferences.area_rank_valle_vidal = (
        int(request.form.get("area_rank_valle_vidal", 0)) or None
    )

    preferences.max_altitude_important = "max_altitude_important" in request.form
    preferences.max_altitude_threshold = (
        int(request.form.get("max_altitude_threshold", 0)) or None
    )

    preferences.difficulty_challenging = "difficulty_challenging" in request.form
    preferences.difficulty_rugged = "difficulty_rugged" in request.form
    preferences.difficulty_strenuous = "difficulty_strenuous" in request.form
    preferences.difficulty_super_strenuous = (
        "difficulty_super_strenuous" in request.form
    )

    preferences.climb_baldy = "climb_baldy" in request.form
    preferences.climb_phillips = "climb_phillips" in request.form
    preferences.climb_tooth = "climb_tooth" in request.form
    preferences.climb_inspiration_point = "climb_inspiration_point" in request.form

    preferences.programs_important = "programs_important" in request.form

    db.session.commit()
    flash("Preferences saved successfully!", "success")

    return redirect(url_for("preferences"))


@app.route("/scores")
def scores():
    """Program scoring page"""
    crew_id = 1  # Default to sample crew

    crew = Crew.query.get(crew_id)
    crew_members = (
        CrewMember.query.filter_by(crew_id=crew_id)
        .order_by(CrewMember.member_number)
        .all()
    )
    programs = Program.query.order_by(Program.category, Program.name).all()

    # Get existing scores
    existing_scores = {}
    scores_query = ProgramScore.query.filter_by(crew_id=crew_id).all()
    for score in scores_query:
        key = f"{score.crew_member_id}_{score.program_id}"
        existing_scores[key] = score.score

    return render_template(
        "scores.html",
        crew=crew,
        crew_members=crew_members,
        programs=programs,
        existing_scores=existing_scores,
    )


@app.route("/scores", methods=["POST"])
def save_scores():
    """Save program scores"""
    crew_id = 1  # Default to sample crew

    # Delete existing scores for this crew
    ProgramScore.query.filter_by(crew_id=crew_id).delete()

    # Save new scores
    for key, value in request.form.items():
        if key.startswith("score_") and value:
            parts = key.split("_")
            if len(parts) == 3:
                member_id = int(parts[1])
                program_id = int(parts[2])
                score_value = int(value)

                score = ProgramScore(
                    crew_id=crew_id,
                    crew_member_id=member_id,
                    program_id=program_id,
                    score=score_value,
                )
                db.session.add(score)

    db.session.commit()
    flash("Scores saved successfully!", "success")

    return redirect(url_for("scores"))


@app.route("/results")
def results():
    """Results and rankings page"""
    crew_id = 1  # Default to sample crew
    method = request.args.get("method", "Total")

    scorer = PhilmontScorer(crew_id)
    results = scorer.calculate_itinerary_scores(method)

    return render_template("results.html", results=results, calculation_method=method)


@app.route("/api/calculate")
def api_calculate():
    """API endpoint to recalculate scores"""
    crew_id = request.args.get("crew_id", 1, type=int)
    method = request.args.get("method", "Total")

    scorer = PhilmontScorer(crew_id)
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


@app.route("/itinerary/<code>")
def itinerary_detail(code):
    """Detailed view of a specific itinerary"""
    itinerary = Itinerary.query.filter_by(itinerary_code=code).first_or_404()

    # Get camps for this itinerary
    conn = sqlite3.connect("philmont_selection.db")
    cursor = conn.execute(
        """
        SELECT ic.day_number, c.name, c.elevation, c.country, c.is_staffed, c.is_trail_camp
        FROM itinerary_camps ic
        JOIN camps c ON ic.camp_id = c.id
        WHERE ic.itinerary_id = ?
        ORDER BY ic.day_number
    """,
        (itinerary.id,),
    )

    camps = []
    for row in cursor.fetchall():
        camps.append(
            {
                "day": row[0],
                "name": row[1],
                "elevation": row[2],
                "country": row[3],
                "is_staffed": row[4],
                "is_trail_camp": row[5],
            }
        )

    conn.close()

    return render_template("itinerary_detail.html", itinerary=itinerary, camps=camps)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Philmont Trek Selection Application (SQLAlchemy)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run Flask app in debug mode"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the Flask app on (default: 5000)",
    )
    args = parser.parse_args()

    with app.app_context():
        # Don't create tables - use existing database
        pass
    app.run(debug=args.debug, port=args.port)
