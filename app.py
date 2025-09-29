#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime
import sqlite3
import json
import math
import bcrypt
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'philmont-trek-selection-2025'

# Authentication configuration
ADMIN_PASSWORD = 'philmont2025'  # In production, use environment variables

@app.context_processor
def inject_admin_status():
    """Inject admin status and user info into all templates"""
    return {
        'is_admin': is_admin(),
        'current_user': get_current_user(),
        'user_crew_id': get_user_crew_id()
    }

def get_current_user():
    """Get current authenticated user info"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    conn = get_db_connection()
    user = conn.execute('''
        SELECT u.*, c.crew_name 
        FROM users u 
        LEFT JOIN crews c ON u.crew_id = c.id 
        WHERE u.id = ? AND u.is_active = TRUE
    ''', (user_id,)).fetchone()
    conn.close()
    return user

def get_user_crew_id():
    """Get the crew_id that the current user should see"""
    user = get_current_user()
    if user:
        if user['is_admin']:
            # Admin can see any crew via query parameter or session
            return request.args.get('crew_id', type=int) or session.get('admin_crew_id')
        else:
            # Regular users can only see their assigned crew
            return user['crew_id']
    return None

def is_admin():
    """Check if current user is admin"""
    user = get_current_user()
    return user and user['is_admin']

def is_authenticated():
    """Check if user is authenticated (either admin or regular user)"""
    return get_current_user() is not None

def login_required(f):
    """Decorator to require any authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username, password):
    """Authenticate user credentials and return user info"""
    conn = get_db_connection()
    user = conn.execute('''
        SELECT * FROM users 
        WHERE username = ? AND is_active = TRUE
    ''', (username,)).fetchone()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        return user
    return None

def create_user(username, password, crew_id=None, is_admin=False):
    """Create a new user with hashed password"""
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO users (username, password_hash, crew_id, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, crew_id, is_admin))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_db_connection():
    conn = sqlite3.connect('philmont_selection.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# ===================================
# Helper Functions
# ===================================

def get_crew_info(crew_id=1):
    """Get crew information"""
    conn = get_db_connection()
    
    crew = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchone()
    crew_members = conn.execute(
        'SELECT * FROM crew_members WHERE crew_id = ? ORDER BY member_number', 
        (crew_id,)
    ).fetchall()
    preferences = conn.execute(
        'SELECT * FROM crew_preferences WHERE crew_id = ?', 
        (crew_id,)
    ).fetchone()
    
    conn.close()
    return crew, crew_members, preferences

def get_programs():
    """Get all programs"""
    conn = get_db_connection()
    programs = conn.execute('SELECT * FROM programs ORDER BY category, name').fetchall()
    conn.close()
    return programs

def get_existing_scores(crew_id=1):
    """Get existing program scores for a crew"""
    conn = get_db_connection()
    scores = conn.execute('''
        SELECT crew_member_id, program_id, score 
        FROM program_scores 
        WHERE crew_id = ?
    ''', (crew_id,)).fetchall()
    conn.close()
    
    score_dict = {}
    for score in scores:
        key = f"{score['crew_member_id']}_{score['program_id']}"
        score_dict[key] = score['score']
    
    return score_dict

# ===================================
# Scoring Logic (Replicated from Excel)
# ===================================

class PhilmontScorer:
    def __init__(self, crew_id):
        self.crew_id = crew_id
        self._scoring_factors = None
    
    def get_score_factor(self, factor_code):
        """Get scoring factor from database (replicates Excel getScoreFactor method)"""
        if self._scoring_factors is None:
            self._load_scoring_factors()
        
        return self._scoring_factors.get(factor_code, 1.0)
    
    def get_crew_skill_level(self):
        """Calculate average crew skill level"""
        conn = get_db_connection()
        skill_data = conn.execute('''
            SELECT AVG(skill_level) as avg_skill
            FROM crew_members 
            WHERE crew_id = ? AND skill_level IS NOT NULL
        ''', (self.crew_id,)).fetchone()
        conn.close()
        
        if skill_data and skill_data['avg_skill']:
            # Round to nearest integer skill level (1-5)
            return max(1, min(5, round(skill_data['avg_skill'])))
        return 3  # Default to skill level 3 if no data
    
    def set_itinerary_difficulty_factor(self, itinerary_difficulty, crew_skill_level=None):
        """
        Get difficulty factor based on crew skill level vs itinerary difficulty
        Replicates Excel setItineraryDifficultyFactor method
        """
        if crew_skill_level is None:
            crew_skill_level = self.get_crew_skill_level()
        
        # Get the factor from the lookup table
        if crew_skill_level in self._skill_difficulty_factors:
            if itinerary_difficulty in self._skill_difficulty_factors[crew_skill_level]:
                return self._skill_difficulty_factors[crew_skill_level][itinerary_difficulty]
        
        # Default fallback if not found
        return 2000
    
    def _load_scoring_factors(self):
        """Load scoring factors from database"""
        conn = get_db_connection()
        factors = conn.execute('''
            SELECT factor_code, multiplier 
            FROM scoring_factors 
            WHERE is_active = TRUE
        ''').fetchall()
        conn.close()
        
        self._scoring_factors = {}
        for factor in factors:
            self._scoring_factors[factor['factor_code']] = float(factor['multiplier'])
        
        # Set defaults if not found in database
        self._scoring_factors.setdefault('programFactor', 1.5)
        self._scoring_factors.setdefault('difficultDelta', 1.0)
        self._scoring_factors.setdefault('maxDifficult', 1000.0)
        self._scoring_factors.setdefault('maxSkill', 4000.0)
        self._scoring_factors.setdefault('skillDelta', 1.0)
        self._scoring_factors.setdefault('mileageFactor', 1.0)
        self._scoring_factors.setdefault('minDifficult', 500.0)
        
        # Load skill level difficulty factor lookup table (from Excel Tables sheet)
        self._skill_difficulty_factors = {
            1: {'C': 5000, 'R': 3500, 'S': 2000, 'SS': 500},
            2: {'C': 4500, 'R': 3333, 'S': 2167, 'SS': 1000},
            3: {'C': 4000, 'R': 3167, 'S': 2333, 'SS': 1500},
            4: {'C': 3500, 'R': 3000, 'S': 2500, 'SS': 2000},
            5: {'C': 3000, 'R': 2833, 'S': 2667, 'SS': 2500}
        }
        
    def get_program_scores(self, method='Total'):
        """Calculate program scores using specified method (Total, Average, Median, Mode)"""
        conn = get_db_connection()
        
        # Get all program scores for the crew
        scores = conn.execute('''
            SELECT p.id, p.name, ps.score
            FROM programs p
            JOIN program_scores ps ON p.id = ps.program_id
            WHERE ps.crew_id = ?
            ORDER BY p.id, ps.crew_member_id
        ''', (self.crew_id,)).fetchall()
        
        program_scores = {}
        current_program = None
        current_scores = []
        
        for score in scores:
            program_id = score['id']
            score_value = score['score']
            
            if current_program != program_id:
                if current_program is not None and current_scores:
                    program_scores[current_program] = self._calculate_aggregate(current_scores, method)
                current_program = program_id
                current_scores = [score_value]
            else:
                current_scores.append(score_value)
        
        # Don't forget the last program
        if current_program is not None and current_scores:
            program_scores[current_program] = self._calculate_aggregate(current_scores, method)
        
        conn.close()
        return program_scores
    
    def _calculate_aggregate(self, scores, method):
        """Calculate aggregate score using specified method"""
        if method == 'Total':
            return sum(scores)
        elif method == 'Average':
            return sum(scores) / len(scores)
        elif method == 'Median':
            sorted_scores = sorted(scores)
            n = len(sorted_scores)
            if n % 2 == 0:
                return (sorted_scores[n//2-1] + sorted_scores[n//2]) / 2
            else:
                return sorted_scores[n//2]
        elif method == 'Mode':
            from collections import Counter
            counter = Counter(scores)
            return counter.most_common(1)[0][0]
        else:
            return sum(scores)  # Default to total
    
    def calculate_itinerary_scores(self, method='Total'):
        """Calculate total scores for all itineraries"""
        program_scores = self.get_program_scores(method)
        crew_prefs = self._get_crew_preferences()
        
        conn = get_db_connection()
        
        # Get all itineraries
        itineraries = conn.execute('SELECT * FROM itineraries ORDER BY itinerary_code').fetchall()
        
        results = []
        
        for itin in itineraries:
            score_components = {
                'program_score': self._calculate_program_score(itin['id'], program_scores, conn),
                'difficulty_score': self._calculate_difficulty_score(itin, crew_prefs),
                'area_score': self._calculate_area_score(itin, crew_prefs),
                'altitude_score': self._calculate_altitude_score(itin, crew_prefs),
                'distance_score': self._calculate_distance_score(itin, crew_prefs),
                'hike_score': self._calculate_hike_score(itin, crew_prefs)
            }
            
            total_score = sum(score_components.values())
            
            results.append({
                'itinerary': dict(itin),
                'total_score': total_score,
                'components': score_components
            })
        
        # Sort by total score (descending)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Add rankings
        for i, result in enumerate(results, 1):
            result['ranking'] = i
        
        conn.close()
        return results
    
    def _get_crew_preferences(self):
        """Get crew preferences"""
        conn = get_db_connection()
        prefs = conn.execute('SELECT * FROM crew_preferences WHERE crew_id = ?', (self.crew_id,)).fetchone()
        conn.close()
        
        return dict(prefs) if prefs else {}
    
    def _calculate_program_score(self, itinerary_id, program_scores, conn):
        """Calculate program score for an itinerary"""
        # Get programs available for this itinerary
        available_programs = conn.execute('''
            SELECT ip.program_id 
            FROM itinerary_programs ip 
            WHERE ip.itinerary_id = ? AND ip.is_available = 1
        ''', (itinerary_id,)).fetchall()
        
        # Sum scores for available programs
        total_score = 0
        for prog in available_programs:
            program_id = prog['program_id']
            if program_id in program_scores:
                total_score += program_scores[program_id]
        
        # Apply program factor from database
        program_factor = self.get_score_factor('programFactor')
        return total_score * program_factor
    
    def _calculate_difficulty_score(self, itinerary, crew_prefs):
        """Calculate difficulty-based score"""
        difficulty = itinerary['difficulty']
        
        # Check if crew accepts this difficulty level
        difficulty_accepted = False
        if difficulty == 'C' and crew_prefs.get('difficulty_challenging', True):
            difficulty_accepted = True
        elif difficulty == 'R' and crew_prefs.get('difficulty_rugged', True):
            difficulty_accepted = True
        elif difficulty == 'S' and crew_prefs.get('difficulty_strenuous', True):
            difficulty_accepted = True
        elif difficulty == 'SS' and crew_prefs.get('difficulty_super_strenuous', True):
            difficulty_accepted = True
        
        if not difficulty_accepted:
            return 0
        
        # Apply skill level vs difficulty factor (replicates Excel setItineraryDifficultyFactor)
        difficulty_factor = self.set_itinerary_difficulty_factor(difficulty)
        
        # Apply additional multipliers from database
        difficulty_delta = self.get_score_factor('difficultDelta')
        
        return difficulty_factor * difficulty_delta
    
    def _calculate_area_score(self, itinerary, crew_prefs):
        """Calculate area preference score"""
        if not crew_prefs.get('area_important', False):
            return 0
        
        area_scores = {
            'covers_south': crew_prefs.get('area_rank_south', 0),
            'covers_central': crew_prefs.get('area_rank_central', 0),
            'covers_north': crew_prefs.get('area_rank_north', 0),
            'covers_valle_vidal': crew_prefs.get('area_rank_valle_vidal', 0)
        }
        
        score = 0
        for area_field, rank in area_scores.items():
            if itinerary[area_field] and rank:
                # Higher rank (1-4) gives more points
                score += (5 - rank) * 25
        
        return score
    
    def _calculate_altitude_score(self, itinerary, crew_prefs):
        """Calculate altitude-based score"""
        score = 0
        
        max_altitude = itinerary['max_altitude'] or 0
        if crew_prefs.get('max_altitude_important', False):
            threshold = crew_prefs.get('max_altitude_threshold', 10000)
            if max_altitude <= threshold:
                score += 50
        
        return score
    
    def _calculate_distance_score(self, itinerary, crew_prefs):
        """Calculate distance-based score"""
        distance = itinerary['distance'] or 50
        base_score = max(0, 100 - abs(distance - 50))  # Prefer distances around 50 miles
        mileage_factor = self.get_score_factor('mileageFactor')
        return base_score * mileage_factor
    
    def _calculate_hike_score(self, itinerary, crew_prefs):
        """Calculate hike in/out preference score"""
        score = 0
        
        # Check hike out preference (starts_at = 'Hike Out' means hiking out of base camp to start)
        if crew_prefs.get('hike_out_preference', True) and itinerary['starts_at'] == 'Hike Out':
            score += 500
        
        # Check hike in preference (ends_at = 'Hike In' means hiking in to base camp to end)
        if crew_prefs.get('hike_in_preference', True) and itinerary['ends_at'] == 'Hike In':
            score += 500
        
        return score

# ===================================
# Helper Functions for Score Management
# ===================================

def recalculate_crew_scores(crew_id):
    """Recalculate and cache crew program scores for faster access"""
    conn = get_db_connection()
    
    try:
        # Calculate aggregate scores for each program using different methods
        scorer = PhilmontScorer(crew_id)
        
        methods = ['Total', 'Average', 'Median']
        
        for method in methods:
            program_scores = scorer.get_program_scores(method)
            
            # Store or update cached scores (you could create a crew_program_scores table)
            # For now, we'll just ensure the calculation works and log it
            print(f"Recalculated {method} scores for crew {crew_id}: {len(program_scores)} programs")
        
        # Update crew preferences if needed (mark that scores have been updated)
        conn.execute('''
            UPDATE crews 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (crew_id,))
        
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User and admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Check for admin login (backward compatibility)
        if username.lower() == 'admin' and password == ADMIN_PASSWORD:
            # Create admin user if it doesn't exist
            conn = get_db_connection()
            admin_user = conn.execute('''
                SELECT * FROM users WHERE username = 'admin' AND is_admin = TRUE
            ''').fetchone()
            
            if not admin_user:
                admin_id = create_user('admin', ADMIN_PASSWORD, is_admin=True)
                admin_user = conn.execute('SELECT * FROM users WHERE id = ?', (admin_id,)).fetchone()
            
            conn.close()
            
            if admin_user:
                session['user_id'] = admin_user['id']
                # Update last login
                conn = get_db_connection()
                conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (admin_user['id'],))
                conn.commit()
                conn.close()
                
                flash('Successfully logged in as admin', 'success')
                return redirect(url_for('admin'))
        
        # Regular user authentication
        elif username and password:
            user = authenticate_user(username, password)
            if user:
                session['user_id'] = user['id']
                # Update last login
                conn = get_db_connection()
                conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
                conn.commit()
                conn.close()
                
                if user['is_admin']:
                    flash(f'Successfully logged in as admin', 'success')
                    return redirect(url_for('admin'))
                else:
                    flash(f'Welcome back, {user["username"]}!', 'success')
                    # Redirect to preferences for their crew
                    return redirect(url_for('preferences', crew_id=user['crew_id']))
            else:
                flash('Invalid username or password', 'error')
        else:
            flash('Please enter both username and password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()  # Clear all session data
    flash('Successfully logged out', 'success')
    return redirect(url_for('index'))

@app.route('/api/crews')
def api_crews():
    """API endpoint to list available crews (filtered by user permissions)"""
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    conn = get_db_connection()
    
    user = get_current_user()
    if user['is_admin']:
        # Admin can see all crews
        crews = conn.execute('SELECT id, crew_name, crew_size FROM crews ORDER BY crew_name').fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute('''
            SELECT id, crew_name, crew_size 
            FROM crews 
            WHERE id = ? 
            ORDER BY crew_name
        ''', (user['crew_id'],)).fetchall()
    
    conn.close()
    
    return jsonify([{
        'id': crew['id'],
        'name': crew['crew_name'],
        'size': crew['crew_size']
    } for crew in crews])

# ===================================
# Main Routes  
# ===================================

@app.route('/')
def index():
    """Home page"""
    # Check if user is authenticated
    if not is_authenticated():
        return redirect(url_for('login'))
    
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    
    conn = get_db_connection()
    
    if is_admin():
        # Admin sees all crews
        crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
        if not crew_id and crews:
            crew_id = crews[0]['id']
            session['admin_crew_id'] = crew_id  # Remember admin's choice
    else:
        # Regular users only see their assigned crew
        user = get_current_user()
        if user and user['crew_id']:
            crews = conn.execute('SELECT * FROM crews WHERE id = ?', (user['crew_id'],)).fetchall()
            crew_id = user['crew_id']
        else:
            flash('No crew assigned to your account. Contact administrator.', 'error')
            return redirect(url_for('logout'))
    
    conn.close()
    
    return render_template('index.html', 
                         crews=crews,
                         selected_crew_id=crew_id)

@app.route('/preferences')
@login_required
def preferences():
    """Crew preferences page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    
    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get('crew_id', type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session['admin_crew_id'] = crew_id
    
    if not crew_id:
        flash('No crew available. Contact administrator.', 'error')
        return redirect(url_for('logout'))
    
    conn = get_db_connection()
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('preferences'))
    
    if is_admin():
        # Admin sees all crews
        crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
    
    conn.close()
    
    crew, crew_members, preferences = get_crew_info(crew_id)
    
    return render_template('preferences.html', 
                         crew=crew, 
                         crew_members=crew_members, 
                         preferences=preferences,
                         crews=crews,
                         selected_crew_id=crew_id)

@app.route('/preferences', methods=['POST'])
@login_required
def save_preferences():
    """Save crew preferences"""
    # Get crew_id from form data
    crew_id = request.form.get('crew_id', type=int)
    if not crew_id:
        flash('Please select a crew.', 'error')
        return redirect(url_for('preferences'))
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('preferences'))
    
    conn = get_db_connection()
    
    def safe_int(value):
        """Safely convert form value to int or None"""
        if not value or value.strip() == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    # Check if preferences exist
    existing = conn.execute('SELECT id FROM crew_preferences WHERE crew_id = ?', (crew_id,)).fetchone()
    
    if existing:
        # Update existing preferences
        conn.execute('''
            UPDATE crew_preferences SET
                area_important = ?,
                area_rank_south = ?,
                area_rank_central = ?,
                area_rank_north = ?,
                area_rank_valle_vidal = ?,
                max_altitude_important = ?,
                max_altitude_threshold = ?,
                difficulty_challenging = ?,
                difficulty_rugged = ?,
                difficulty_strenuous = ?,
                difficulty_super_strenuous = ?,
                climb_baldy = ?,
                climb_phillips = ?,
                climb_tooth = ?,
                climb_inspiration_point = ?,
                hike_in_preference = ?,
                hike_out_preference = ?,
                programs_important = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE crew_id = ?
        ''', (
            'area_important' in request.form,
            safe_int(request.form.get('area_rank_south')),
            safe_int(request.form.get('area_rank_central')),
            safe_int(request.form.get('area_rank_north')),
            safe_int(request.form.get('area_rank_valle_vidal')),
            'max_altitude_important' in request.form,
            safe_int(request.form.get('max_altitude_threshold')),
            'difficulty_challenging' in request.form,
            'difficulty_rugged' in request.form,
            'difficulty_strenuous' in request.form,
            'difficulty_super_strenuous' in request.form,
            'climb_baldy' in request.form,
            'climb_phillips' in request.form,
            'climb_tooth' in request.form,
            'climb_inspiration_point' in request.form,
            'hike_in_preference' in request.form,
            'hike_out_preference' in request.form,
            'programs_important' in request.form,
            crew_id
        ))
    else:
        # Insert new preferences
        conn.execute('''
            INSERT INTO crew_preferences 
            (crew_id, area_important, area_rank_south, area_rank_central, area_rank_north, area_rank_valle_vidal,
             max_altitude_important, max_altitude_threshold, difficulty_challenging, difficulty_rugged, 
             difficulty_strenuous, difficulty_super_strenuous, climb_baldy, climb_phillips, climb_tooth, 
             climb_inspiration_point, hike_in_preference, hike_out_preference, programs_important)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            crew_id,
            'area_important' in request.form,
            safe_int(request.form.get('area_rank_south')),
            safe_int(request.form.get('area_rank_central')),
            safe_int(request.form.get('area_rank_north')),
            safe_int(request.form.get('area_rank_valle_vidal')),
            'max_altitude_important' in request.form,
            safe_int(request.form.get('max_altitude_threshold')),
            'difficulty_challenging' in request.form,
            'difficulty_rugged' in request.form,
            'difficulty_strenuous' in request.form,
            'difficulty_super_strenuous' in request.form,
            'climb_baldy' in request.form,
            'climb_phillips' in request.form,
            'climb_tooth' in request.form,
            'climb_inspiration_point' in request.form,
            'hike_in_preference' in request.form,
            'hike_out_preference' in request.form,
            'programs_important' in request.form
        ))
    
    conn.commit()
    conn.close()
    flash('Preferences saved successfully!', 'success')
    
    return redirect(url_for('preferences', crew_id=crew_id))

@app.route('/scores')
@login_required
def scores():
    """Program scoring page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    
    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get('crew_id', type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session['admin_crew_id'] = crew_id
    
    if not crew_id:
        flash('No crew available. Contact administrator.', 'error')
        return redirect(url_for('logout'))
    
    conn = get_db_connection()
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('scores'))
    
    if is_admin():
        # Admin sees all crews
        crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
    
    conn.close()
    
    crew, crew_members, _ = get_crew_info(crew_id)
    programs = get_programs()
    existing_scores = get_existing_scores(crew_id)
    
    return render_template('scores.html', 
                         crew=crew, 
                         crew_members=crew_members, 
                         programs=programs,
                         existing_scores=existing_scores,
                         crews=crews,
                         selected_crew_id=crew_id)

@app.route('/scores', methods=['POST'])
@login_required
def save_scores():
    """Save program scores"""
    # Get crew_id from form data
    crew_id = request.form.get('crew_id', type=int)
    if not crew_id:
        flash('Please select a crew.', 'error')
        return redirect(url_for('scores'))
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('scores'))
    
    conn = get_db_connection()
    
    # Delete existing scores for this crew
    conn.execute('DELETE FROM program_scores WHERE crew_id = ?', (crew_id,))
    
    # Save new scores
    for key, value in request.form.items():
        if key.startswith('score_') and value and value.strip():
            parts = key.split('_')
            if len(parts) == 3:
                try:
                    member_id = int(parts[1])
                    program_id = int(parts[2])
                    score_value = int(value)
                except (ValueError, TypeError):
                    continue  # Skip invalid values
                
                conn.execute('''
                    INSERT INTO program_scores (crew_id, crew_member_id, program_id, score)
                    VALUES (?, ?, ?, ?)
                ''', (crew_id, member_id, program_id, score_value))
    
    conn.commit()
    conn.close()
    flash('Scores saved successfully!', 'success')
    
    return redirect(url_for('scores', crew_id=crew_id))

@app.route('/results')
@login_required
def results():
    """Results and rankings page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    method = request.args.get('method', 'Total')
    
    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get('crew_id', type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session['admin_crew_id'] = crew_id
    
    if not crew_id:
        flash('No crew available. Contact administrator.', 'error')
        return redirect(url_for('logout'))
    
    conn = get_db_connection()
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('results'))
    
    if is_admin():
        # Admin sees all crews
        crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
    
    conn.close()
    
    if not crew_id:
        flash('No crews found. Please create a crew first.', 'error')
        return redirect(url_for('admin'))
    
    scorer = PhilmontScorer(crew_id)
    results = scorer.calculate_itinerary_scores(method)
    
    return render_template('results.html', 
                         results=results, 
                         calculation_method=method,
                         crews=crews,
                         selected_crew_id=crew_id)

@app.route('/api/calculate')
def api_calculate():
    """API endpoint to recalculate scores"""
    crew_id = request.args.get('crew_id', 1, type=int)
    method = request.args.get('method', 'Total')
    
    scorer = PhilmontScorer(crew_id)
    results = scorer.calculate_itinerary_scores(method)
    
    # Convert to JSON-friendly format
    json_results = []
    for result in results:
        json_results.append({
            'itinerary_code': result['itinerary']['itinerary_code'],
            'total_score': result['total_score'],
            'ranking': result['ranking'],
            'components': result['components']
        })
    
    return jsonify(json_results)

@app.route('/api/crew_members/<int:crew_id>')
def api_crew_members(crew_id):
    """API endpoint to get crew members for a specific crew"""
    conn = get_db_connection()
    
    crew_members = conn.execute('''
        SELECT id, name, email, age, skill_level
        FROM crew_members 
        WHERE crew_id = ? 
        ORDER BY member_number
    ''', (crew_id,)).fetchall()
    
    conn.close()
    
    # Convert to JSON-friendly format
    members = []
    for member in crew_members:
        members.append({
            'id': member['id'],
            'name': member['name'],
            'email': member['email'],
            'age': member['age'],
            'skill_level': member['skill_level']
        })
    
    return jsonify(members)

@app.route('/itinerary/<code>')
def itinerary_detail(code):
    """Detailed view of a specific itinerary"""
    conn = get_db_connection()
    
    itinerary = conn.execute('SELECT * FROM itineraries WHERE itinerary_code = ?', (code,)).fetchone()
    if not itinerary:
        flash(f'Itinerary {code} not found', 'error')
        return redirect(url_for('results'))
    
    # Get camps for this itinerary
    camps = conn.execute('''
        SELECT ic.day_number, c.name, c.elevation, c.country, c.is_staffed, c.is_trail_camp
        FROM itinerary_camps ic
        JOIN camps c ON ic.camp_id = c.id
        WHERE ic.itinerary_id = ?
        ORDER BY ic.day_number
    ''', (itinerary['id'],)).fetchall()
    
    conn.close()
    
    return render_template('itinerary_detail.html', 
                         itinerary=itinerary, 
                         camps=camps)

@app.route('/survey')
@login_required
def survey():
    """Crew member program survey page"""
    # Get appropriate crew_id based on user permissions
    crew_id = get_user_crew_id()
    
    # For admin users, allow crew_id override and remember choice
    if is_admin():
        requested_crew_id = request.args.get('crew_id', type=int)
        if requested_crew_id:
            crew_id = requested_crew_id
            session['admin_crew_id'] = crew_id
    
    if not crew_id:
        flash('No crew available. Contact administrator.', 'error')
        return redirect(url_for('logout'))
    
    # Get all programs organized by category
    programs = get_programs()
    
    # Get crews for the dropdown
    conn = get_db_connection()
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('survey'))
    
    if is_admin():
        # Admin sees all crews
        crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    else:
        # Regular users only see their assigned crew
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
        
        # Get user's crew from session or default to 1
        if not crew_id:
            crew_id = session.get('user_crew_id', 1)
        
        # Regular users only see their own crew
        crews = conn.execute('SELECT * FROM crews WHERE id = ?', (crew_id,)).fetchall()
    
    conn.close()
    
    return render_template('survey.html', 
                         programs=programs, 
                         crews=crews,
                         selected_crew_id=crew_id)

@app.route('/survey', methods=['POST'])
@login_required
def submit_survey():
    """Process crew member program survey submission"""
    # Get crew_id from form and verify access
    crew_id = request.form.get('crew_id', type=int)
    if not crew_id:
        flash('Please select a crew.', 'error')
        return redirect(url_for('survey'))
    
    # Verify crew access permission
    user = get_current_user()
    if not user['is_admin'] and user['crew_id'] != crew_id:
        flash('Access denied to that crew.', 'error')
        return redirect(url_for('survey'))
    
    conn = get_db_connection()
    
    def safe_int(value):
        """Safely convert form value to int or None"""
        if not value or value.strip() == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    # Get form data
    member_type = request.form.get('member_type', 'new')
    existing_member_id = safe_int(request.form.get('existing_member_id'))
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    crew_id = safe_int(request.form.get('crew_id'))
    age = safe_int(request.form.get('age'))
    skill_level = safe_int(request.form.get('skill_level', 3))
    
    # Validate required fields based on member type
    if not crew_id:
        flash('Please select a crew.', 'error')
        return redirect(url_for('survey'))
    
    if member_type == 'existing':
        if not existing_member_id:
            flash('Please select an existing crew member.', 'error')
            return redirect(url_for('survey'))
    else:
        if not name or not email:
            flash('Please fill in all required fields (Name and Email).', 'error')
            return redirect(url_for('survey'))
    
    try:
        if member_type == 'existing' and existing_member_id:
            # Use existing crew member
            member_id = existing_member_id
            # Update their info if provided
            if name or email or age or skill_level:
                conn.execute('''
                    UPDATE crew_members 
                    SET name = COALESCE(?, name), 
                        email = COALESCE(?, email), 
                        age = COALESCE(?, age), 
                        skill_level = COALESCE(?, skill_level)
                    WHERE id = ? AND crew_id = ?
                ''', (name or None, email or None, age, skill_level, member_id, crew_id))
        else:
            # Handle new member creation or update existing member by email/name match
            existing_member = None
            if email:
                existing_member = conn.execute(
                    'SELECT * FROM crew_members WHERE crew_id = ? AND email = ?', 
                    (crew_id, email)
                ).fetchone()
            
            if not existing_member and name:
                # Check by name and crew if no email match
                existing_member = conn.execute(
                    'SELECT * FROM crew_members WHERE crew_id = ? AND name = ?', 
                    (crew_id, name)
                ).fetchone()
            
            if existing_member:
                member_id = existing_member['id']
                # Update existing crew member info including email
                conn.execute('''
                    UPDATE crew_members 
                    SET name = ?, email = ?, age = ?, skill_level = ?
                    WHERE id = ?
                ''', (name, email, age, skill_level, member_id))
            else:
                # Get next member number for this crew
                max_member = conn.execute(
                    'SELECT MAX(member_number) as max_num FROM crew_members WHERE crew_id = ?', 
                    (crew_id,)
                ).fetchone()
                member_number = (max_member['max_num'] or 0) + 1
                
                # Insert new crew member with email
                cursor = conn.execute('''
                    INSERT INTO crew_members (crew_id, member_number, name, email, age, skill_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (crew_id, member_number, name, email, age, skill_level))
                member_id = cursor.lastrowid
        
        # Process program scores
        programs = get_programs()
        
        # Delete existing scores for this crew member
        conn.execute('DELETE FROM program_scores WHERE crew_member_id = ?', (member_id,))
        
        # Insert new scores
        for program in programs:
            score_value = safe_int(request.form.get(f'program_{program["id"]}', 10))
            if score_value is not None:
                conn.execute('''
                    INSERT INTO program_scores (crew_id, crew_member_id, program_id, score)
                    VALUES (?, ?, ?, ?)
                ''', (crew_id, member_id, program['id'], score_value))
        
        conn.commit()
        
        # Recalculate crew program scores after survey update
        try:
            recalculate_crew_scores(crew_id)
            flash(f'Survey submitted successfully for {name}! Crew scores have been updated.', 'success')
        except Exception as e:
            flash(f'Survey submitted for {name}, but there was an issue updating crew scores: {str(e)}', 'warning')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error submitting survey: {str(e)}', 'error')
        return redirect(url_for('survey'))
    finally:
        conn.close()
    
    return redirect(url_for('survey'))

@app.route('/admin')
@admin_required
def admin():
    """Admin page for managing crew members"""
    selected_crew_id = request.args.get('crew_id', type=int)
    
    conn = get_db_connection()
    
    # Get all crews
    crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    
    selected_crew = None
    crew_members = []
    
    if selected_crew_id:
        # Get selected crew info
        selected_crew = conn.execute('SELECT * FROM crews WHERE id = ?', (selected_crew_id,)).fetchone()
        
        if selected_crew:
            # Get crew members with survey completion status
            crew_members = conn.execute('''
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
            ''', (selected_crew_id,)).fetchall()
    
    conn.close()
    
    return render_template('admin.html', 
                         crews=crews, 
                         selected_crew=selected_crew,
                         selected_crew_id=selected_crew_id,
                         crew_members=crew_members)

@app.route('/admin/add_crew', methods=['POST'])
def add_crew():
    """Add a new crew"""
    crew_name = request.form.get('crew_name', '').strip()
    crew_size = request.form.get('crew_size', 9, type=int)
    
    if not crew_name:
        flash('Crew name is required.', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    
    try:
        cursor = conn.execute('''
            INSERT INTO crews (crew_name, crew_size) 
            VALUES (?, ?)
        ''', (crew_name, crew_size))
        
        conn.commit()
        flash(f'Crew "{crew_name}" created successfully!', 'success')
        return redirect(url_for('admin', crew_id=cursor.lastrowid))
        
    except Exception as e:
        conn.rollback()
        flash(f'Error creating crew: {str(e)}', 'error')
        return redirect(url_for('admin'))
    finally:
        conn.close()

@app.route('/admin/add_member', methods=['POST'])
def add_member():
    """Add a new crew member"""
    crew_id = request.form.get('crew_id', type=int)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    age = request.form.get('age', type=int)
    skill_level = request.form.get('skill_level', 3, type=int)
    
    if not crew_id or not name:
        flash('Crew and name are required.', 'error')
        return redirect(url_for('admin', crew_id=crew_id))
    
    conn = get_db_connection()
    
    try:
        # Get next member number for this crew
        max_member = conn.execute(
            'SELECT MAX(member_number) as max_num FROM crew_members WHERE crew_id = ?', 
            (crew_id,)
        ).fetchone()
        member_number = (max_member['max_num'] or 0) + 1
        
        # Insert new crew member with email
        conn.execute('''
            INSERT INTO crew_members (crew_id, member_number, name, email, age, skill_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (crew_id, member_number, name, email, age, skill_level))
        
        # If email is provided, we could store it in a separate table or extend the crew_members table
        # For now, let's extend the crew_members table to include email
        
        conn.commit()
        flash(f'Crew member "{name}" added successfully!', 'success')
        
        # Note: No need to recalculate scores here since new member has no program scores yet
        
    except Exception as e:
        conn.rollback()
        flash(f'Error adding crew member: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin', crew_id=crew_id))

@app.route('/admin/edit_member', methods=['POST'])
def edit_member():
    """Edit an existing crew member"""
    member_id = request.form.get('member_id', type=int)
    crew_id = request.form.get('crew_id', type=int)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    age = request.form.get('age', type=int)
    skill_level = request.form.get('skill_level', 3, type=int)
    
    if not member_id or not name:
        flash('Member ID and name are required.', 'error')
        return redirect(url_for('admin', crew_id=crew_id))
    
    conn = get_db_connection()
    
    try:
        conn.execute('''
            UPDATE crew_members 
            SET name = ?, email = ?, age = ?, skill_level = ?
            WHERE id = ?
        ''', (name, email, age, skill_level, member_id))
        
        conn.commit()
        
        # Recalculate crew scores after member info update (in case skill level affects scoring)
        try:
            recalculate_crew_scores(crew_id)
            flash(f'Crew member "{name}" updated successfully! Crew scores have been updated.', 'success')
        except Exception as e:
            flash(f'Crew member "{name}" updated, but there was an issue updating crew scores: {str(e)}', 'warning')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error updating crew member: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin', crew_id=crew_id))

@app.route('/admin/delete_member', methods=['POST'])
def delete_member():
    """Delete a crew member and all associated data"""
    member_id = request.form.get('member_id', type=int)
    crew_id = request.form.get('crew_id', type=int)
    
    if not member_id:
        flash('Member ID is required.', 'error')
        return redirect(url_for('admin', crew_id=crew_id))
    
    conn = get_db_connection()
    
    try:
        # Delete program scores first (foreign key constraint)
        conn.execute('DELETE FROM program_scores WHERE crew_member_id = ?', (member_id,))
        
        # Delete the crew member
        cursor = conn.execute('DELETE FROM crew_members WHERE id = ?', (member_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            
            # Recalculate crew scores after member deletion
            try:
                recalculate_crew_scores(crew_id)
                flash('Crew member deleted successfully! Crew scores have been updated.', 'success')
            except Exception as e:
                flash(f'Crew member deleted, but there was an issue updating crew scores: {str(e)}', 'warning')
        else:
            flash('Crew member not found.', 'error')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting crew member: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin', crew_id=crew_id))

# ===================================
# User Management Routes (Admin Only)
# ===================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin page for managing user accounts"""
    conn = get_db_connection()
    
    # Get all users with their crew information
    users = conn.execute('''
        SELECT u.*, c.crew_name
        FROM users u
        LEFT JOIN crews c ON u.crew_id = c.id
        ORDER BY u.is_admin DESC, u.username
    ''').fetchall()
    
    # Get all crews for the dropdown
    crews = conn.execute('SELECT * FROM crews ORDER BY crew_name').fetchall()
    
    conn.close()
    
    return render_template('admin_users.html', users=users, crews=crews)

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create a new user account"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    crew_id = request.form.get('crew_id', type=int)
    is_admin = 'is_admin' in request.form
    
    # Validation
    if not username:
        flash('Username is required', 'error')
        return redirect(url_for('admin_users'))
    
    if not password:
        flash('Password is required', 'error')
        return redirect(url_for('admin_users'))
    
    if not is_admin and not crew_id:
        flash('Regular users must be assigned to a crew', 'error')
        return redirect(url_for('admin_users'))
    
    if is_admin and crew_id:
        flash('Admin users cannot be assigned to a specific crew', 'error')
        return redirect(url_for('admin_users'))
    
    # Create user
    user_id = create_user(username, password, crew_id if not is_admin else None, is_admin)
    
    if user_id:
        flash(f'User "{username}" created successfully!', 'success')
    else:
        flash(f'Error creating user "{username}" - username may already exist', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    conn = get_db_connection()
    
    try:
        # Get user info first
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if user:
            # Don't allow deleting the current admin user
            current_user = get_current_user()
            if user_id == current_user['id']:
                flash('Cannot delete your own account while logged in', 'error')
                return redirect(url_for('admin_users'))
            
            # Delete the user
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            flash(f'User "{user["username"]}" deleted successfully', 'success')
        else:
            flash('User not found', 'error')
    
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    conn = get_db_connection()
    
    try:
        # Get current status
        user = conn.execute('SELECT username, is_active FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if user:
            new_status = not user['is_active']
            conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
            conn.commit()
            
            status_text = 'activated' if new_status else 'deactivated'
            flash(f'User "{user["username"]}" {status_text} successfully', 'success')
        else:
            flash('User not found', 'error')
    
    except Exception as e:
        conn.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)