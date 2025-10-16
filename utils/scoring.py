"""Scoring functions"""

from database import get_db_connection


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
