#!/usr/bin/env python3

import argparse
import os
import sqlite3
import sys
import threading
import time
import webbrowser
from functools import wraps

import bcrypt
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "philmont-trek-selection-2025"


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_database_path():
    """Get database path - always in the current working directory for persistence"""
    # Always use current working directory so database persists across runs
    return os.path.join(os.getcwd(), "philmont_selection.db")


# Add custom Jinja2 filter for formatting arrival dates
@app.template_filter("format_arrival_date")
def format_arrival_date(date_str):
    """Format MMDD to MM/DD for display"""
    if date_str and len(date_str) == 4:
        return f"{date_str[:2]}/{date_str[2:]}"
    return date_str


# Authentication configuration
ADMIN_PASSWORD = "philmont2025"  # In production, use environment variables


@app.context_processor
def inject_admin_status():
    """Inject admin status and user info into all templates"""
    return {
        "is_admin": is_admin(),
        "current_user": get_current_user(),
        "user_crew_id": get_user_crew_id(),
        "available_trek_types": get_available_trek_types(),
    }


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
    conn = get_db_connection()
    user = conn.execute(
        """
        SELECT * FROM users 
        WHERE username = ? AND is_active = TRUE
    """,
        (username,),
    ).fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
        return user
    return None


def create_user(username, password, crew_id=None, is_admin=False):
    """Create a new user with hashed password"""
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

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


def get_db_connection():
    db_path = get_database_path()

    # If database doesn't exist, copy it from embedded resources
    if not os.path.exists(db_path):
        try:
            # Try to copy from PyInstaller bundle
            embedded_db_path = get_resource_path("philmont_selection.db")
            if os.path.exists(embedded_db_path):
                import shutil

                shutil.copy2(embedded_db_path, db_path)
                print(f"Database initialized from embedded copy: {db_path}")
        except Exception as e:
            print(f"Warning: Could not initialize database from embedded copy: {e}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn


# ===================================
# Helper Functions
# ===================================


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


# ===================================
# Scoring Logic (Replicated from Excel)
# ===================================


def get_crew_trek_type(crew_id):
    """Get the trek type preference for a crew, falling back to available types"""
    conn = get_db_connection()
    prefs = conn.execute(
        "SELECT trek_type FROM crew_preferences WHERE crew_id = ?", (crew_id,)
    ).fetchone()
    conn.close()

    preferred_type = prefs["trek_type"] if prefs and prefs["trek_type"] else "12-day"
    available_types = get_available_trek_types()

    # If the preferred type has no data, fall back to the first available type
    if preferred_type in available_types:
        return preferred_type
    elif available_types:
        return available_types[0]  # Return first available type
    else:
        return "12-day"  # Ultimate fallback


def get_available_trek_types():
    """Get all trek types that have itinerary data available"""
    conn = get_db_connection()
    trek_types = conn.execute(
        "SELECT DISTINCT trek_type FROM itineraries ORDER BY trek_type"
    ).fetchall()
    conn.close()

    return [row["trek_type"] for row in trek_types]


def get_all_trek_types():
    """Get all possible trek types (including those without data)"""
    return ["12-day", "9-day", "7-day", "Cavalcade"]


class PhilmontScorer:
    def __init__(self, crew_id, trek_type="12-day"):
        self.crew_id = crew_id
        self.trek_type = trek_type
        self._scoring_factors = None

    def get_score_factor(self, factor_code):
        """Get scoring factor from database (replicates Excel getScoreFactor method)"""
        if self._scoring_factors is None:
            self._load_scoring_factors()

        return self._scoring_factors.get(factor_code, 1.0)

    def get_crew_skill_level(self):
        """Calculate average crew skill level"""
        conn = get_db_connection()
        skill_data = conn.execute(
            """
            SELECT AVG(skill_level) as avg_skill
            FROM crew_members 
            WHERE crew_id = ? AND skill_level IS NOT NULL
        """,
            (self.crew_id,),
        ).fetchone()
        conn.close()

        if skill_data and skill_data["avg_skill"]:
            # Round to nearest integer skill level (1-10)
            return max(1, min(10, round(skill_data["avg_skill"])))
        return 5  # Default to skill level 5 if no data (middle of 1-10 range)

    def set_itinerary_difficulty_factor(
        self, itinerary_difficulty, crew_skill_level=None
    ):
        """
        Get difficulty factor based on crew skill level vs itinerary difficulty
        Replicates Excel setItineraryDifficultyFactor method
        """
        if crew_skill_level is None:
            crew_skill_level = self.get_crew_skill_level()

        # Get the factor from the lookup table
        if crew_skill_level in self._skill_difficulty_factors:
            if itinerary_difficulty in self._skill_difficulty_factors[crew_skill_level]:
                return self._skill_difficulty_factors[crew_skill_level][
                    itinerary_difficulty
                ]

        # Default fallback if not found
        return 2000

    def _load_scoring_factors(self):
        """Load scoring factors from database"""
        conn = get_db_connection()
        factors = conn.execute(
            """
            SELECT factor_code, multiplier 
            FROM scoring_factors 
            WHERE is_active = TRUE
        """
        ).fetchall()
        conn.close()

        self._scoring_factors = {}
        for factor in factors:
            self._scoring_factors[factor["factor_code"]] = float(factor["multiplier"])

        # Set defaults if not found in database
        self._scoring_factors.setdefault("programFactor", 1.5)
        self._scoring_factors.setdefault("difficultDelta", 1.0)
        self._scoring_factors.setdefault("maxDifficult", 1000.0)
        self._scoring_factors.setdefault("maxSkill", 4000.0)
        self._scoring_factors.setdefault("skillDelta", 1.0)
        self._scoring_factors.setdefault("mileageFactor", 100.0)
        self._scoring_factors.setdefault("minDifficult", 500.0)

        # Load skill level difficulty factor lookup table (from Excel Tables sheet)
        self._skill_difficulty_factors = {
            1: {"C": 5000, "R": 3500, "S": 2000, "SS": 500},
            2: {"C": 4500, "R": 3333, "S": 2167, "SS": 1000},
            3: {"C": 4000, "R": 3167, "S": 2333, "SS": 1500},
            4: {"C": 3500, "R": 3000, "S": 2500, "SS": 2000},
            5: {"C": 3000, "R": 2833, "S": 2667, "SS": 2500},
            6: {"C": 2500, "R": 2667, "S": 2833, "SS": 3000},
            7: {"C": 2000, "R": 2500, "S": 3000, "SS": 3500},
            8: {"C": 1500, "R": 2333, "S": 3167, "SS": 4000},
            9: {"C": 1000, "R": 2167, "S": 3333, "SS": 4500},
            10: {"C": 500, "R": 2000, "S": 3500, "SS": 5000},
        }

    def get_program_scores(self, method="Total"):
        """Calculate program scores using specified method (Total, Average, Median, Mode)"""
        conn = get_db_connection()

        # Get crew preferences for adult program weighting
        prefs = conn.execute(
            """
            SELECT adult_program_weight_enabled, adult_program_weight_percent
            FROM crew_preferences
            WHERE crew_id = ?
        """,
            (self.crew_id,),
        ).fetchone()

        adult_weight_enabled = prefs["adult_program_weight_enabled"] if prefs else False
        adult_weight_percent = prefs["adult_program_weight_percent"] if prefs else 100

        # Get all program scores for the crew with member ages
        scores = conn.execute(
            """
            SELECT p.id, p.name, ps.score, cm.age
            FROM programs p
            JOIN program_scores ps ON p.id = ps.program_id
            JOIN crew_members cm ON ps.crew_member_id = cm.id
            WHERE ps.crew_id = ?
            ORDER BY p.id, ps.crew_member_id
        """,
            (self.crew_id,),
        ).fetchall()

        program_scores = {}
        current_program = None
        current_scores = []

        for score in scores:
            program_id = score["id"]
            score_value = score["score"]
            member_age = score["age"]

            # Apply adult program weight if enabled and member is over 20
            if adult_weight_enabled and member_age > 20:
                score_value = score_value * (adult_weight_percent / 100.0)

            if current_program != program_id:
                if current_program is not None and current_scores:
                    program_scores[current_program] = self._calculate_aggregate(
                        current_scores, method
                    )
                current_program = program_id
                current_scores = [score_value]
            else:
                current_scores.append(score_value)

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

        conn = get_db_connection()

        # Get all itineraries based on trek type
        itineraries = conn.execute(
            "SELECT * FROM itineraries WHERE trek_type = ? ORDER BY itinerary_code",
            (self.trek_type,),
        ).fetchall()

        results = []

        # Handle case where no itineraries exist for this trek type
        if not itineraries:
            conn.close()
            return results

        for itin in itineraries:
            score_components = {
                "program_score": self._calculate_program_score(
                    itin["id"], program_scores, conn
                ),
                "difficulty_score": self._calculate_difficulty_score(itin, crew_prefs),
                "area_score": self._calculate_area_score(itin, crew_prefs),
                "altitude_score": self._calculate_altitude_score(itin, crew_prefs),
                "distance_score": self._calculate_distance_score(itin, crew_prefs),
                "hike_score": self._calculate_hike_score(itin, crew_prefs),
                "camp_score": self._calculate_camp_score(itin, crew_prefs, conn),
                "peak_score": self._calculate_peak_score(
                    itin, crew_prefs, conn, method
                ),
            }

            total_score = sum(score_components.values())

            results.append(
                {
                    "itinerary": dict(itin),
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
        conn = get_db_connection()
        prefs = conn.execute(
            "SELECT * FROM crew_preferences WHERE crew_id = ?", (self.crew_id,)
        ).fetchone()
        conn.close()

        return dict(prefs) if prefs else {}

    def _calculate_program_score(self, itinerary_id, program_scores, conn):
        """Calculate program score for an itinerary"""
        # Get programs available for this itinerary based on trek type
        available_programs = conn.execute(
            """
            SELECT ip.program_id 
            FROM itinerary_programs ip 
            WHERE ip.itinerary_id = ? AND ip.is_available = 1 AND ip.trek_type = ?
        """,
            (itinerary_id, self.trek_type),
        ).fetchall()

        # Sum scores for available programs
        total_score = 0
        for prog in available_programs:
            program_id = prog["program_id"]
            if program_id in program_scores:
                total_score += program_scores[program_id]

        # Apply program factor from database
        program_factor = self.get_score_factor("programFactor")
        return total_score * program_factor

    def _calculate_difficulty_score(self, itinerary, crew_prefs):
        """Calculate difficulty-based score"""
        difficulty = itinerary["difficulty"]

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

        if not difficulty_accepted:
            return 0

        # Apply skill level vs difficulty factor (replicates Excel setItineraryDifficultyFactor)
        difficulty_factor = self.set_itinerary_difficulty_factor(difficulty)

        # Apply additional multipliers from database
        difficulty_delta = self.get_score_factor("difficultDelta")

        return difficulty_factor * difficulty_delta

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

        # Define rank-based scoring table
        rank_scores = {1: 1000, 2: 600, 3: 200, 4: 150}

        score = 0
        for area_field, rank in area_scores.items():
            if itinerary[area_field] and rank:
                # Use rank-based scoring table
                score += rank_scores.get(rank, 0)

        return score

    def _calculate_altitude_score(self, itinerary, crew_prefs):
        """Calculate altitude-based score"""
        score = 0

        # Highest Camp Elevation Scoring - using altitude preference chart
        max_altitude = itinerary["max_altitude"] or 0
        if crew_prefs.get("max_altitude_important", False) and max_altitude > 0:
            # Altitude scoring chart
            altitude_scores = {
                8999: 20,  # below 9,000
                9000: 30,
                9100: 40,
                9200: 50,
                9800: 60,
                10000: 70,
                10500: 80,
                10600: 90,
                10800: 100,
                11000: 110,
                11800: 120,
                12441: 130,
            }

            # Find the appropriate score based on max altitude
            altitude_score = 20  # Default to lowest score
            for threshold, points in sorted(altitude_scores.items(), reverse=True):
                if max_altitude >= threshold:
                    altitude_score = points
                    break

            score += altitude_score

        # Overall Elevation Change Scoring - using elevation gain preference chart
        total_gain = (
            itinerary["total_elevation_gain"]
            if itinerary["total_elevation_gain"]
            else 0
        )
        if crew_prefs.get("total_elevation_gain_important", False) and total_gain > 0:
            # Elevation gain scoring chart
            elevation_gain_scores = {
                1499: 40,  # below 1,500
                1500: 50,
                2000: 60,
                2500: 70,
                3000: 80,
                3500: 90,
                4000: 100,
                4500: 90,
                5000: 80,
                5500: 70,
                6000: 60,
                6500: 50,
            }

            # Find the appropriate score based on total elevation gain
            gain_score = 40  # Default to lowest score
            for threshold, points in sorted(
                elevation_gain_scores.items(), reverse=True
            ):
                if total_gain >= threshold:
                    gain_score = points
                    break

            score += gain_score

        # Average Daily Change Scoring - using daily elevation change chart
        if crew_prefs.get("altitude_change_important", False):
            daily_change = (
                itinerary["avg_daily_elevation_change"]
                if itinerary["avg_daily_elevation_change"]
                else 0
            )

            if daily_change > 0:
                # Daily elevation change scoring chart
                daily_change_scores = {300: 100, 600: 300, 900: 200, 1200: 100}

                # Find the appropriate score based on daily elevation change
                daily_score = 100  # Default to lowest score
                for threshold, points in sorted(
                    daily_change_scores.items(), reverse=True
                ):
                    if daily_change >= threshold:
                        daily_score = points
                        break

                score += daily_score

        return score

    def _calculate_distance_score(self, itinerary, crew_prefs):
        """Calculate distance-based score"""
        distance = itinerary["distance"] if itinerary["distance"] is not None else 50
        # base_score = max(0, 100 - abs(distance - 50))  # Prefer distances around 50 miles
        base_score = distance  # This seems to be what the spreadsheet is really doing
        mileage_factor = self.get_score_factor("mileageFactor")
        return base_score * mileage_factor

    def _calculate_hike_score(self, itinerary, crew_prefs):
        """Calculate hike in/out preference score"""
        score = 0

        # Check hike out preference (starts_at = 'Hike Out' means hiking out of base camp to start)
        if (
            crew_prefs.get("hike_out_preference", True)
            and itinerary["starts_at"] == "Hike Out"
        ):
            score += 500

        # Check hike in preference (ends_at = 'Hike In' means hiking in to base camp to end)
        if (
            crew_prefs.get("hike_in_preference", True)
            and itinerary["ends_at"] == "Hike In"
        ):
            score += 500

        return score

    def _calculate_camp_score(self, itinerary, crew_prefs, conn):
        """Calculate camp and layover preference score"""
        score = 0

        # Use dry_camps field from itineraries table
        dry_camp_count = itinerary["dry_camps"] or 0
        max_dry_camps = crew_prefs.get("max_dry_camps")
        dry_camp_scores = {0: 300, 1: 250, 2: 225, 3: 200, 4: 150, 5: 100, 6: 50, 7: 20}
        if max_dry_camps is not None:
            if dry_camp_count <= max_dry_camps:
                # Award points for staying within limit, more points for fewer dry camps
                score += dry_camp_scores.get(
                    min(dry_camp_count, 7), 20
                )  # Use 20 for 7+ camps
            else:
                # Penalize for exceeding limit
                score -= (dry_camp_count - max_dry_camps) * 500
        else:
            # Use dry camp scoring table when no maximum is set
            score += dry_camp_scores.get(
                min(dry_camp_count, 7), 20
            )  # Use 20 for 7+ camps

        # Use trail_camps field from itineraries table for trail camp scoring
        trail_camp_count = itinerary["trail_camps"] or 0
        trail_camp_scores = {
            0: 250,
            1: 200,
            2: 175,
            3: 150,
            4: 125,
            5: 100,
            6: 75,
            7: 50,
            8: 25,
        }
        score += trail_camp_scores.get(
            min(trail_camp_count, 8), 25
        )  # Use 25 for 8+ camps

        # Total camps scoring (based on total number of camps in itinerary)
        total_camps = dry_camp_count + trail_camp_count
        total_camp_scores = {3: 60, 4: 70, 5: 80, 6: 90, 7: 100, 8: 75, 9: 60, 10: 50}
        if total_camps in total_camp_scores:
            score += total_camp_scores[total_camps]

        # Check for showers if required
        if crew_prefs.get("showers_required", False):
            # Get camps to check for showers
            camps = conn.execute(
                """
                SELECT c.has_showers
                FROM camps c
                JOIN itinerary_camps ic ON c.id = ic.camp_id
                WHERE ic.itinerary_id = ?
            """,
                (itinerary["id"],),
            ).fetchall()

            has_showers = any(camp["has_showers"] for camp in camps)
            if has_showers:
                score += 1000  # Significant bonus for having showers
            else:
                score -= 1500  # Penalty for no showers when required

        # Check for layovers if required
        if crew_prefs.get("layovers_required", False):
            # Get camps to check for layovers
            layovers = conn.execute(
                """
                SELECT ic.is_layover
                FROM itinerary_camps ic
                WHERE ic.itinerary_id = ? AND ic.is_layover = 1
            """,
                (itinerary["id"],),
            ).fetchall()

            has_layovers = len(layovers) > 0
            if has_layovers:
                score += 800  # Bonus for having layovers
            else:
                score -= 1200  # Penalty for no layovers when required

        # Food resupply preferences
        days_food_from_base = itinerary["days_food_from_base"] or 0
        max_days_food = itinerary["max_days_food"] or 0

        if crew_prefs.get("prefer_low_starting_food", False):
            # Score based on days_food_from_base: 20 points for 1 day, 100 points for 9 days
            # Formula: 20 + (days-1)*10, but inverted since we want fewer days to score higher
            if days_food_from_base > 0:
                # Invert the scoring: fewer days = higher score
                base_score = 20 + (days_food_from_base - 1) * 10
                score += base_score

        if crew_prefs.get("prefer_shorter_resupply", False):
            # Score based on max_days_food: 100 points for 1 day, 50 points for 6 days
            # Already decreasing, so use directly
            if max_days_food > 0:
                food_score = 100 + (max_days_food - 1) * (-10)
                score += max(food_score, 0)  # Don't go negative

        return score

    def _calculate_peak_score(self, itinerary, crew_prefs, conn, method="Total"):
        """Calculate peak climbing score based on Landmarks program scores

        This matches the VBA implementation which uses program scores from
        Landmarks columns rather than a fixed 500-point bonus system.
        Uses the same calculation method (Total/Average/Median/Mode) as other scoring.
        Applies additional multiplication factors based on peak difficulty/importance.
        """
        score = 0

        # Map peak preferences to their corresponding Landmarks programs
        peak_to_landmark = {
            "climb_baldy": "Landmarks: Baldy Mountain",
            "climb_phillips": "Landmarks: Mount Phillips",
            "climb_tooth": "Landmarks: Tooth of Time",
            "climb_inspiration_point": "Landmarks: Inspiration Point",
            "climb_trail_peak": "Landmarks: Trail Peak",
            "climb_others": "Landmarks: Mountaineering",
        }

        # Peak multiplication factors based on difficulty/importance
        peak_multipliers = {
            "climb_baldy": 2.0,  # Baldy Mountain - highest peak at Philmont
            "climb_phillips": 1.5,  # Mount Phillips - second highest peak
            "climb_tooth": 1.5,  # Tooth of Time - iconic landmark
            "climb_inspiration_point": 1.0,  # Inspiration Point - standard difficulty
            "climb_trail_peak": 1.5,  # Trail Peak - moderate difficulty
            "climb_others": 1.2,  # Mountaineering - various peaks
        }

        # Map peak preferences to itinerary columns
        peak_preferences = {
            "climb_baldy": itinerary["baldy_mountain"] or False,
            "climb_phillips": itinerary["mount_phillips"] or False,
            "climb_tooth": itinerary["tooth_of_time"] or False,
            "climb_inspiration_point": itinerary["inspiration_point"] or False,
            "climb_trail_peak": itinerary["trail_peak"] or False,
            "climb_others": itinerary["mountaineering"] or False,
        }

        # Get program scores for this crew using the same method as other calculations
        program_scores = {}
        for pref_key, landmark_name in peak_to_landmark.items():
            # Get program ID for this landmark
            program_result = conn.execute(
                "SELECT id FROM programs WHERE name = ?", (landmark_name,)
            ).fetchone()

            if program_result:
                program_id = program_result["id"]
                # Get all scores for this program for this crew
                score_results = conn.execute(
                    """
                    SELECT score 
                    FROM program_scores 
                    WHERE program_id = ? AND crew_id = ?
                    """,
                    (program_id, self.crew_id),
                ).fetchall()

                if score_results:
                    scores = [row["score"] for row in score_results]
                    # Use the same aggregation method as other program scoring
                    program_scores[pref_key] = self._calculate_aggregate(scores, method)

        # Add scores for peaks that the itinerary includes
        for pref_key, itin_has_peak in peak_preferences.items():
            if itin_has_peak and pref_key in program_scores:
                base_score = program_scores[pref_key]
                program_factor = self.get_score_factor("programFactor")

                if crew_prefs.get(pref_key, False):
                    # Crew wants this peak - apply peak-specific multiplication factor
                    multiplier = peak_multipliers.get(pref_key, 1.0)
                    score += base_score * multiplier * program_factor
                else:
                    # Crew doesn't want this peak but it's available - give base benefit only
                    score += base_score * program_factor
        return score


# ===================================
# Helper Functions for Score Management
# ===================================


def recalculate_crew_scores(crew_id):
    """Recalculate and cache crew program scores for faster access"""
    conn = get_db_connection()

    try:
        # Calculate aggregate scores for each program using different methods
        trek_type = get_crew_trek_type(crew_id)
        scorer = PhilmontScorer(crew_id, trek_type)

        methods = ["Total", "Average", "Median"]

        for method in methods:
            program_scores = scorer.get_program_scores(method)

            # Store or update cached scores (you could create a crew_program_scores table)
            # For now, we'll just ensure the calculation works and log it
            print(
                f"Recalculated {method} scores for crew {crew_id}: {len(program_scores)} programs"
            )

        # Update crew preferences if needed (mark that scores have been updated)
        conn.execute(
            """
            UPDATE crews 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """,
            (crew_id,),
        )

        conn.commit()

    except Exception as e:
        print(f"Error recalculating scores for crew {crew_id}: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()


def invalidate_crew_cache(crew_id):
    """Invalidate any cached calculations for a crew"""
    # This function can be used if we implement caching in the future
    pass


# ===================================
# Authentication Routes
# ===================================


@app.route("/login", methods=["GET", "POST"])
def login():
    """User and admin login page"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Check for admin login (backward compatibility)
        if username.lower() == "admin" and password == ADMIN_PASSWORD:
            # Create admin user if it doesn't exist
            conn = get_db_connection()
            admin_user = conn.execute(
                """
                SELECT * FROM users WHERE username = 'admin' AND is_admin = TRUE
            """
            ).fetchone()

            if not admin_user:
                admin_id = create_user("admin", ADMIN_PASSWORD, is_admin=True)
                admin_user = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (admin_id,)
                ).fetchone()

            conn.close()

            if admin_user:
                session["user_id"] = admin_user["id"]
                # Update last login
                conn = get_db_connection()
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (admin_user["id"],),
                )
                conn.commit()
                conn.close()

                flash("Successfully logged in as admin", "success")
                return redirect(url_for("admin"))

        # Regular user authentication
        elif username and password:
            user = authenticate_user(username, password)
            if user:
                session["user_id"] = user["id"]
                # Update last login
                conn = get_db_connection()
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user["id"],),
                )
                conn.commit()
                conn.close()

                if user["is_admin"]:
                    flash("Successfully logged in as admin", "success")
                    return redirect(url_for("admin"))
                else:
                    flash(f"Welcome back, {user['username']}!", "success")
                    # Redirect to preferences for their crew
                    return redirect(url_for("preferences", crew_id=user["crew_id"]))
            else:
                flash("Invalid username or password", "error")
        else:
            flash("Please enter both username and password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout and clear session"""
    session.clear()  # Clear all session data
    flash("Successfully logged out", "success")
    return redirect(url_for("index"))


@app.route("/api/crews")
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


# ===================================
# Main Routes
# ===================================


@app.route("/")
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
            return redirect(url_for("logout"))

    conn.close()

    return render_template("index.html", crews=crews, selected_crew_id=crew_id)


@app.route("/preferences")
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
        return redirect(url_for("logout"))

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


@app.route("/preferences", methods=["POST"])
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

    return redirect(url_for("preferences", crew_id=crew_id))


@app.route("/scores")
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
        return redirect(url_for("logout"))

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


@app.route("/scores", methods=["POST"])
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

    return redirect(url_for("scores", crew_id=crew_id))


@app.route("/results")
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
        return redirect(url_for("logout"))

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
        return redirect(url_for("admin"))

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


@app.route("/program_chart")
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


@app.route("/api/calculate")
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


@app.route("/api/crew_members/<int:crew_id>")
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


@app.route("/itinerary/<code>")
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


@app.route("/survey")
def survey():
    """Crew member program survey page"""
    # Always use crew ID 1 for surveys
    crew_id = 1

    # Get all programs organized by category
    programs = get_programs()

    return render_template("survey.html", programs=programs, selected_crew_id=crew_id)


@app.route("/survey", methods=["POST"])
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


@app.route("/admin")
@admin_required
def admin():
    """Admin page for managing crew members"""
    selected_crew_id = request.args.get("crew_id", type=int)

    conn = get_db_connection()

    # Get all crews
    crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()

    selected_crew = None
    crew_members = []

    if selected_crew_id:
        # Get selected crew info
        selected_crew = conn.execute(
            "SELECT * FROM crews WHERE id = ?", (selected_crew_id,)
        ).fetchone()

        if selected_crew:
            # Get crew members with survey completion status
            crew_members = conn.execute(
                """
                SELECT cm.*, 
                       CASE 
                           WHEN EXISTS (
                               SELECT 1 FROM program_scores ps 
                               WHERE ps.crew_member_id = cm.id
                           ) THEN 1 
                           ELSE 0 
                       END as survey_completed
                FROM crew_members cm 
                WHERE cm.crew_id = ? 
                ORDER BY cm.member_number
            """,
                (selected_crew_id,),
            ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        crews=crews,
        selected_crew=selected_crew,
        selected_crew_id=selected_crew_id,
        crew_members=crew_members,
    )


# @app.route('/admin/add_crew', methods=['POST'])
# @admin_required
# def add_crew():
#     """Add a new crew"""
#     crew_name = request.form.get('crew_name', '').strip()
#     crew_size = request.form.get('crew_size', 9, type=int)
#
#     if not crew_name:
#         flash('Crew name is required.', 'error')
#         return redirect(url_for('admin'))
#
#     conn = get_db_connection()
#
#     try:
#         cursor = conn.execute('''
#             INSERT INTO crews (crew_name, crew_size)
#             VALUES (?, ?)
#         ''', (crew_name, crew_size))
#
#         conn.commit()
#         flash(f'Crew "{crew_name}" created successfully!', 'success')
#         return redirect(url_for('admin', crew_id=cursor.lastrowid))
#
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error creating crew: {str(e)}', 'error')
#         return redirect(url_for('admin'))
#     finally:
#         conn.close()


@app.route("/admin/edit_crew", methods=["POST"])
@admin_required
def edit_crew():
    """Edit crew details"""
    crew_id = request.form.get("crew_id", type=int)
    crew_name = request.form.get("crew_name", "").strip()
    crew_size = request.form.get("crew_size", type=int)

    if not crew_id or not crew_name:
        flash("Crew ID and name are required.", "error")
        return redirect(url_for("admin"))

    conn = get_db_connection()

    try:
        conn.execute(
            """
            UPDATE crews 
            SET crew_name = ?, crew_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (crew_name, crew_size, crew_id),
        )

        conn.commit()
        flash(f'Crew "{crew_name}" updated successfully!', "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error updating crew: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin", crew_id=crew_id))


@app.route("/admin/add_member", methods=["POST"])
def add_member():
    """Add a new crew member"""
    crew_id = request.form.get("crew_id", type=int)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    age = request.form.get("age", type=int)
    skill_level = request.form.get("skill_level", 6, type=int)
    redirect_to = request.form.get(
        "redirect_to", "admin"
    )  # Default to admin for backward compatibility

    if not crew_id or not name:
        flash("Crew and name are required.", "error")
        if redirect_to == "preferences":
            return redirect(url_for("preferences"))
        return redirect(url_for("admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        # Get next member number for this crew
        max_member = conn.execute(
            "SELECT MAX(member_number) as max_num FROM crew_members WHERE crew_id = ?",
            (crew_id,),
        ).fetchone()
        member_number = (max_member["max_num"] or 0) + 1

        # Insert new crew member with email
        conn.execute(
            """
            INSERT INTO crew_members (crew_id, member_number, name, email, age, skill_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (crew_id, member_number, name, email, age, skill_level),
        )

        # If email is provided, we could store it in a separate table or extend the crew_members table
        # For now, let's extend the crew_members table to include email

        conn.commit()
        flash(f'Crew member "{name}" added successfully!', "success")

        # Note: No need to recalculate scores here since new member has no program scores yet

    except Exception as e:
        conn.rollback()
        flash(f"Error adding crew member: {str(e)}", "error")
    finally:
        conn.close()

    # Redirect based on the source page
    if redirect_to == "preferences":
        return redirect(url_for("preferences"))
    return redirect(url_for("admin", crew_id=crew_id))


@app.route("/admin/edit_member", methods=["POST"])
def edit_member():
    """Edit an existing crew member"""
    member_id = request.form.get("member_id", type=int)
    crew_id = request.form.get("crew_id", type=int)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    age = request.form.get("age", type=int)
    skill_level = request.form.get("skill_level", 6, type=int)

    if not member_id or not name:
        flash("Member ID and name are required.", "error")
        return redirect(url_for("admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        conn.execute(
            """
            UPDATE crew_members 
            SET name = ?, email = ?, age = ?, skill_level = ?
            WHERE id = ?
        """,
            (name, email, age, skill_level, member_id),
        )

        conn.commit()

        # Recalculate crew scores after member info update (in case skill level affects scoring)
        try:
            recalculate_crew_scores(crew_id)
            flash(
                f'Crew member "{name}" updated successfully! Crew scores have been updated.',
                "success",
            )
        except Exception as e:
            flash(
                f'Crew member "{name}" updated, but there was an issue updating crew scores: {str(e)}',
                "warning",
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error updating crew member: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin", crew_id=crew_id))


@app.route("/admin/delete_member", methods=["POST"])
def delete_member():
    """Delete a crew member and all associated data"""
    member_id = request.form.get("member_id", type=int)
    crew_id = request.form.get("crew_id", type=int)
    redirect_to = request.form.get(
        "redirect_to", "admin"
    )  # Default to admin for backward compatibility

    if not member_id:
        flash("Member ID is required.", "error")
        if redirect_to == "preferences":
            return redirect(url_for("preferences"))
        return redirect(url_for("admin", crew_id=crew_id))

    conn = get_db_connection()

    try:
        # Delete program scores first (foreign key constraint)
        conn.execute(
            "DELETE FROM program_scores WHERE crew_member_id = ?", (member_id,)
        )

        # Delete the crew member
        cursor = conn.execute("DELETE FROM crew_members WHERE id = ?", (member_id,))

        if cursor.rowcount > 0:
            conn.commit()

            # Recalculate crew scores after member deletion
            try:
                recalculate_crew_scores(crew_id)
                flash(
                    "Crew member deleted successfully! Crew scores have been updated.",
                    "success",
                )
            except Exception as e:
                flash(
                    f"Crew member deleted, but there was an issue updating crew scores: {str(e)}",
                    "warning",
                )
        else:
            flash("Crew member not found.", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting crew member: {str(e)}", "error")
    finally:
        conn.close()

    # Redirect based on the source page
    if redirect_to == "preferences":
        return redirect(url_for("preferences"))
    return redirect(url_for("admin", crew_id=crew_id))


@app.route("/admin/delete_all_members", methods=["POST"])
def delete_all_members():
    """Delete all crew members and their associated data"""
    crew_id = request.form.get("crew_id", type=int)

    if not crew_id:
        flash("Crew ID is required.", "error")
        return redirect(url_for("preferences"))

    conn = get_db_connection()

    try:
        # Get count of members to be deleted for feedback
        member_count = conn.execute(
            "SELECT COUNT(*) as count FROM crew_members WHERE crew_id = ?", (crew_id,)
        ).fetchone()["count"]

        if member_count == 0:
            flash("No crew members to delete.", "info")
            return redirect(url_for("preferences"))

        # Delete program scores first (foreign key constraint)
        conn.execute("DELETE FROM program_scores WHERE crew_id = ?", (crew_id,))

        # Delete all crew members for this crew
        conn.execute("DELETE FROM crew_members WHERE crew_id = ?", (crew_id,))

        conn.commit()

        # Recalculate crew scores after all member deletion (will result in no scores)
        try:
            recalculate_crew_scores(crew_id)
            flash(
                f"All {member_count} crew members deleted successfully! All program scores have been cleared.",
                "success",
            )
        except Exception as e:
            flash(
                f"All crew members deleted, but there was an issue updating crew scores: {str(e)}",
                "warning",
            )

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting crew members: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("preferences"))


# ===================================
# User Management Routes (Admin Only)
# ===================================


@app.route("/admin/users")
@admin_required
def admin_users():
    """Admin page for managing user accounts"""
    conn = get_db_connection()

    # Get all users with their crew information
    users = conn.execute(
        """
        SELECT u.*, c.crew_name
        FROM users u
        LEFT JOIN crews c ON u.crew_id = c.id
        ORDER BY u.is_admin DESC, u.username
    """
    ).fetchall()

    # Get all crews for the dropdown
    crews = conn.execute("SELECT * FROM crews ORDER BY crew_name").fetchall()

    conn.close()

    return render_template("admin_users.html", users=users, crews=crews)


@app.route("/admin/users/create", methods=["POST"])
@admin_required
def admin_create_user():
    """Create a new user account"""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    crew_id = request.form.get("crew_id", type=int)
    is_admin = "is_admin" in request.form

    # Validation
    if not username:
        flash("Username is required", "error")
        return redirect(url_for("admin_users"))

    if not password:
        flash("Password is required", "error")
        return redirect(url_for("admin_users"))

    if not is_admin and not crew_id:
        flash("Regular users must be assigned to a crew", "error")
        return redirect(url_for("admin_users"))

    if is_admin and crew_id:
        flash("Admin users cannot be assigned to a specific crew", "error")
        return redirect(url_for("admin_users"))

    # Create user
    user_id = create_user(
        username, password, crew_id if not is_admin else None, is_admin
    )

    if user_id:
        flash(f'User "{username}" created successfully!', "success")
    else:
        flash(f'Error creating user "{username}" - username may already exist', "error")

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    conn = get_db_connection()

    try:
        # Get user info first
        user = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user:
            # Don't allow deleting the current admin user
            current_user = get_current_user()
            if user_id == current_user["id"]:
                flash("Cannot delete your own account while logged in", "error")
                return redirect(url_for("admin_users"))

            # Delete the user
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash(f'User "{user["username"]}" deleted successfully', "success")
        else:
            flash("User not found", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting user: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    conn = get_db_connection()

    try:
        # Get current status
        user = conn.execute(
            "SELECT username, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user:
            new_status = not user["is_active"]
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id)
            )
            conn.commit()

            status_text = "activated" if new_status else "deactivated"
            flash(f'User "{user["username"]}" {status_text} successfully', "success")
        else:
            flash("User not found", "error")

    except Exception as e:
        conn.rollback()
        flash(f"Error updating user: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_users"))


# ===================================
# Contingent Management Routes (Admin Only) - DISABLED
# ===================================

# @app.route('/contingents/create', methods=['POST'])
# @admin_required
# def create_contingent():
#     """Create a new contingent"""
#     year = request.form.get('year', type=int)
#     contingent_identifier = request.form.get('contingent_identifier', '').strip().upper()
#     description = request.form.get('description', '').strip()
#
#     # Validation
#     if not year or not contingent_identifier:
#         flash('Year and contingent identifier are required', 'error')
#         return redirect(url_for('index'))
#
#     # Validate contingent identifier format (###-A or ####-AB)
#     import re
#     if not re.match(r'^[0-9]{3,4}-[A-Z]{1,2}$', contingent_identifier):
#         flash('Contingent identifier must be in format ###-A or ####-AB (e.g., 714-A, 0714-AB)', 'error')
#         return redirect(url_for('index'))
#
#     # Parse the contingent identifier
#     parts = contingent_identifier.split('-')
#     designation = parts[0]
#     expedition_letter = parts[1]
#
#     # Generate arrival date from designation (assume it's MMDD format)
#     if len(designation) == 3:
#         # Convert ###  to 0### format for consistency
#         arrival_date = '0' + designation
#     else:
#         arrival_date = designation
#
#     conn = get_db_connection()
#
#     try:
#         # Check if contingent already exists
#         existing = conn.execute('''
#             SELECT id FROM contingents
#             WHERE year = ? AND designation = ? AND expedition_letter = ?
#         ''', (year, designation, expedition_letter)).fetchone()
#
#         if existing:
#             flash(f'Contingent {contingent_identifier} for {year} already exists', 'error')
#             return redirect(url_for('index'))
#
#         # Insert new contingent
#         cursor = conn.execute('''
#             INSERT INTO contingents (year, designation, arrival_date, expedition_letter, description)
#             VALUES (?, ?, ?, ?, ?)
#         ''', (year, designation, arrival_date, expedition_letter, description or None))
#
#         conn.commit()
#         contingent_id = cursor.lastrowid
#
#         flash(f'Contingent {contingent_identifier} for {year} created successfully!', 'success')
#
#     except sqlite3.IntegrityError as e:
#         conn.rollback()
#         flash(f'Error creating contingent: This contingent may already exist', 'error')
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error creating contingent: {str(e)}', 'error')
#     finally:
#         conn.close()
#
#     return redirect(url_for('index'))

# @app.route('/contingents/<int:contingent_id>')
# @admin_required
# def view_contingent(contingent_id):
#     """View contingent details and manage crews"""
#     conn = get_db_connection()
#
#     # Get contingent details
#     contingent = conn.execute('''
#         SELECT * FROM contingents WHERE id = ?
#     ''', (contingent_id,)).fetchone()
#
#     if not contingent:
#         flash('Contingent not found', 'error')
#         return redirect(url_for('index'))
#
#     # Get crews in this contingent
#     crews_in_contingent = conn.execute('''
#         SELECT c.*, cm_count.member_count
#         FROM crews c
#         LEFT JOIN (
#             SELECT crew_id, COUNT(*) as member_count
#             FROM crew_members
#             GROUP BY crew_id
#         ) cm_count ON c.id = cm_count.crew_id
#         WHERE c.contingent_id = ?
#         ORDER BY c.crew_name
#     ''', (contingent_id,)).fetchall()
#
#     # Get crews not in any contingent
#     unassigned_crews = conn.execute('''
#         SELECT c.*, cm_count.member_count
#         FROM crews c
#         LEFT JOIN (
#             SELECT crew_id, COUNT(*) as member_count
#             FROM crew_members
#             GROUP BY crew_id
#         ) cm_count ON c.id = cm_count.crew_id
#         WHERE c.contingent_id IS NULL
#         ORDER BY c.crew_name
#     ''', ()).fetchall()
#
#     conn.close()
#
#     return render_template('contingent_detail.html',
#                          contingent=contingent,
#                          crews_in_contingent=crews_in_contingent,
#                          unassigned_crews=unassigned_crews)

# @app.route('/contingents/<int:contingent_id>/add_crew', methods=['POST'])
# @admin_required
# def add_crew_to_contingent(contingent_id):
#     """Add a crew to a contingent"""
#     crew_id = request.form.get('crew_id', type=int)
#
#     if not crew_id:
#         flash('Please select a crew', 'error')
#         return redirect(url_for('view_contingent', contingent_id=contingent_id))
#
#     conn = get_db_connection()
#
#     try:
#         # Update crew to belong to this contingent
#         cursor = conn.execute('''
#             UPDATE crews
#             SET contingent_id = ?
#             WHERE id = ?
#         ''', (contingent_id, crew_id))
#
#         if cursor.rowcount > 0:
#             conn.commit()
#             flash('Crew added to contingent successfully!', 'success')
#         else:
#             flash('Crew not found', 'error')
#
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error adding crew to contingent: {str(e)}', 'error')
#     finally:
#         conn.close()
#
#     return redirect(url_for('view_contingent', contingent_id=contingent_id))

# @app.route('/contingents/<int:contingent_id>/remove_crew', methods=['POST'])
# @admin_required
# def remove_crew_from_contingent(contingent_id):
#     """Remove a crew from a contingent"""
#     crew_id = request.form.get('crew_id', type=int)
#
#     if not crew_id:
#         flash('Please select a crew', 'error')
#         return redirect(url_for('view_contingent', contingent_id=contingent_id))
#
#     conn = get_db_connection()
#
#     try:
#         # Remove crew from contingent
#         cursor = conn.execute('''
#             UPDATE crews
#             SET contingent_id = NULL
#             WHERE id = ? AND contingent_id = ?
#         ''', (crew_id, contingent_id))
#
#         if cursor.rowcount > 0:
#             conn.commit()
#             flash('Crew removed from contingent successfully!', 'success')
#         else:
#             flash('Crew not found in this contingent', 'error')
#
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error removing crew from contingent: {str(e)}', 'error')
#     finally:
#         conn.close()
#
#     return redirect(url_for('view_contingent', contingent_id=contingent_id))

# @app.route('/contingents/<int:contingent_id>/create_crew', methods=['POST'])
# @admin_required
# def create_crew_for_contingent(contingent_id):
#     """Create a new crew and assign it to a contingent"""
#     crew_name = request.form.get('crew_name', '').strip()
#     crew_size = request.form.get('crew_size', 9, type=int)
#
#     # Validation
#     if not crew_name:
#         flash('Crew name is required.', 'error')
#         return redirect(url_for('view_contingent', contingent_id=contingent_id))
#
#     if crew_size < 6 or crew_size > 12:
#         flash('Crew size must be between 6 and 12 members.', 'error')
#         return redirect(url_for('view_contingent', contingent_id=contingent_id))
#
#     conn = get_db_connection()
#
#     try:
#         # Verify contingent exists
#         contingent = conn.execute('SELECT * FROM contingents WHERE id = ?', (contingent_id,)).fetchone()
#         if not contingent:
#             flash('Contingent not found.', 'error')
#             return redirect(url_for('index'))
#
#         # Check if crew name already exists
#         existing_crew = conn.execute('SELECT id FROM crews WHERE crew_name = ?', (crew_name,)).fetchone()
#         if existing_crew:
#             flash(f'A crew named "{crew_name}" already exists.', 'error')
#             return redirect(url_for('view_contingent', contingent_id=contingent_id))
#
#         # Create the new crew with contingent assignment
#         cursor = conn.execute('''
#             INSERT INTO crews (crew_name, crew_size, contingent_id)
#             VALUES (?, ?, ?)
#         ''', (crew_name, crew_size, contingent_id))
#
#         new_crew_id = cursor.lastrowid
#         conn.commit()
#
#         flash(f'Crew "{crew_name}" created and assigned to contingent {contingent["full_designation"]} successfully!', 'success')
#
#         # Redirect to admin with the new crew selected for member management
#         return redirect(url_for('admin', crew_id=new_crew_id))
#
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error creating crew: {str(e)}', 'error')
#     finally:
#         conn.close()
#
#     return redirect(url_for('view_contingent', contingent_id=contingent_id))


def open_browser(port):
    """Open web browser to the application URL after a short delay"""

    def delayed_open():
        time.sleep(1.5)  # Wait for Flask to start up
        webbrowser.open(f"http://localhost:{port}")

    thread = threading.Thread(target=delayed_open)
    thread.daemon = True  # Dies when main thread dies
    thread.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Philmont Trek Selection Application")
    parser.add_argument(
        "--debug", action="store_true", help="Run Flask app in debug mode"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5002,
        help="Port to run the Flask app on (default: 5002)",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't automatically open web browser"
    )
    args = parser.parse_args()

    # Automatically open browser unless disabled or in debug mode
    if not args.no_browser and not args.debug:
        open_browser(args.port)
        print(f"Opening browser to http://localhost:{args.port}")
    else:
        print(f"Server starting at http://localhost:{args.port}")

    app.run(debug=args.debug, port=args.port)
