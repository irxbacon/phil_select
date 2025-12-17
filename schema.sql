-- Philmont Trek Selection Database Schema
-- SQLite Database Creation Script

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ===================================
-- Core Reference Tables
-- ===================================

-- Programs offered at Philmont
CREATE TABLE programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(10) UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    old_name_comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Camps at Philmont with their details
CREATE TABLE camps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    country VARCHAR(20), -- South, Central, North, Valle Vidal
    easting INTEGER,
    northing INTEGER,
    elevation INTEGER,
    has_commissary BOOLEAN DEFAULT FALSE,
    has_trading_post BOOLEAN DEFAULT FALSE,
    is_staffed BOOLEAN DEFAULT FALSE,
    is_trail_camp BOOLEAN DEFAULT FALSE,
    is_dry_camp BOOLEAN DEFAULT FALSE,
    has_showers BOOLEAN DEFAULT FALSE,
    camp_map VARCHAR(20),
    added_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trek itineraries (unified table for both 12-day and 9-day treks)
CREATE TABLE itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_code VARCHAR(10) UNIQUE NOT NULL, -- e.g., "12-1", "12-2", "9-1", "9-2"
    trek_type TEXT DEFAULT '12-day', -- '12-day' or '9-day'
    expedition_number VARCHAR(20),
    difficulty VARCHAR(20), -- C, R, S, SS (Challenging, Rugged, Strenuous, Super Strenuous)
    distance INTEGER, -- approximate miles
    days_food_from_base INTEGER,
    max_days_food INTEGER,
    staffed_camps INTEGER,
    trail_camps INTEGER,
    layovers INTEGER,
    total_camps INTEGER,
    dry_camps INTEGER,
    min_altitude INTEGER,
    max_altitude INTEGER,
    total_elevation_gain INTEGER,
    avg_daily_elevation_change DECIMAL(10,2),
    description TEXT,
    starts_at VARCHAR(100), -- Starting trailhead
    ends_at VARCHAR(100), -- Ending trailhead
    via_tooth BOOLEAN DEFAULT FALSE,
    crosses_us64 BOOLEAN DEFAULT FALSE,
    us64_crossing_day INTEGER,
    us64_crossing_direction VARCHAR(20),
    -- Peak opportunities
    baldy_mountain BOOLEAN DEFAULT FALSE,
    inspiration_point BOOLEAN DEFAULT FALSE,
    mount_phillips BOOLEAN DEFAULT FALSE,
    mountaineering BOOLEAN DEFAULT FALSE,
    tooth_of_time BOOLEAN DEFAULT FALSE,
    trail_peak BOOLEAN DEFAULT FALSE,
    -- Regional coverage
    covers_south BOOLEAN DEFAULT FALSE,
    covers_central BOOLEAN DEFAULT FALSE,
    covers_north BOOLEAN DEFAULT FALSE,
    covers_valle_vidal BOOLEAN DEFAULT FALSE,
    year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================
-- Itinerary Details
-- ===================================

-- Daily camps for each itinerary
CREATE TABLE itinerary_camps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL, -- 2, 3, 4, etc. (Day 1 is base camp)
    camp_id INTEGER NOT NULL,
    is_layover BOOLEAN DEFAULT FALSE,
    food_pickup BOOLEAN DEFAULT FALSE,
    year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id),
    FOREIGN KEY (camp_id) REFERENCES camps(id),
    UNIQUE(itinerary_id, day_number)
);

-- Programs available on each itinerary (unified table for both 12-day and 9-day treks)
CREATE TABLE itinerary_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    trek_type TEXT DEFAULT '12-day', -- '12-day' or '9-day'
    is_available BOOLEAN DEFAULT TRUE,
    year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id),
    FOREIGN KEY (program_id) REFERENCES programs(id),
    UNIQUE(itinerary_id, program_id)
);

-- Programs available at each camp
CREATE TABLE camp_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camp_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camp_id) REFERENCES camps(id),
    FOREIGN KEY (program_id) REFERENCES programs(id),
    UNIQUE(camp_id, program_id)
);

-- ===================================
-- Crew Preferences and Scoring
-- ===================================

-- Crew information
CREATE TABLE crews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_name VARCHAR(100),
    crew_size INTEGER DEFAULT 9,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User authentication and crew assignment
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Store password (simplified for this system)
    crew_id INTEGER, -- NULL for admin users
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE SET NULL,
    -- Ensure admin users don't have crew assignments
    CHECK ((is_admin = TRUE AND crew_id IS NULL) OR (is_admin = FALSE AND crew_id IS NOT NULL))
);

-- Individual crew members
CREATE TABLE crew_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    member_number INTEGER NOT NULL, -- 1, 2, 3, etc.
    name VARCHAR(100),
    age INTEGER,
    skill_level INTEGER DEFAULT 1, -- 1-5 scale
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id),
    UNIQUE(crew_id, member_number)
);

-- Crew preferences for various factors
CREATE TABLE crew_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL UNIQUE, -- Ensure one preference set per crew
    -- Area preferences
    area_important BOOLEAN DEFAULT FALSE,
    area_rank_south INTEGER, -- 1-4 ranking
    area_rank_central INTEGER,
    area_rank_north INTEGER,
    area_rank_valle_vidal INTEGER,
    -- Altitude preferences  
    max_altitude_important BOOLEAN DEFAULT FALSE,
    max_altitude_threshold INTEGER,
    altitude_change_important BOOLEAN DEFAULT FALSE,
    daily_altitude_change_threshold INTEGER,
    -- Difficulty preferences
    difficulty_challenging BOOLEAN DEFAULT TRUE,
    difficulty_rugged BOOLEAN DEFAULT TRUE,
    difficulty_strenuous BOOLEAN DEFAULT TRUE,
    difficulty_super_strenuous BOOLEAN DEFAULT TRUE,
    -- Peak climbing preferences
    climb_baldy BOOLEAN DEFAULT FALSE,
    climb_phillips BOOLEAN DEFAULT FALSE,
    climb_tooth BOOLEAN DEFAULT FALSE,
    climb_inspiration_point BOOLEAN DEFAULT FALSE,
    climb_others BOOLEAN DEFAULT FALSE,
    climb_trail_peak BOOLEAN DEFAULT FALSE,
    -- Hiking preferences
    hike_in_preference BOOLEAN DEFAULT TRUE,
    hike_out_preference BOOLEAN DEFAULT TRUE,
    -- Program importance
    programs_important BOOLEAN DEFAULT FALSE,
    -- Year for multi-year support
    year INTEGER DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE,
    -- Ensure valid area rankings (1-4)
    CHECK (area_rank_south IS NULL OR (area_rank_south >= 1 AND area_rank_south <= 4)),
    CHECK (area_rank_central IS NULL OR (area_rank_central >= 1 AND area_rank_central <= 4)),
    CHECK (area_rank_north IS NULL OR (area_rank_north >= 1 AND area_rank_north <= 4)),
    CHECK (area_rank_valle_vidal IS NULL OR (area_rank_valle_vidal >= 1 AND area_rank_valle_vidal <= 4))
);

-- Individual program scores from crew members
CREATE TABLE program_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    crew_member_id INTEGER NOT NULL,
    program_id INTEGER NOT NULL,
    score INTEGER NOT NULL, -- 0-20 scale typically
    year INTEGER DEFAULT 2025, -- Year for crew-specific scoring
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE,
    FOREIGN KEY (crew_member_id) REFERENCES crew_members(id) ON DELETE CASCADE,
    FOREIGN KEY (program_id) REFERENCES programs(id),
    UNIQUE(crew_member_id, program_id, year), -- Ensure crew member scores are unique per program per year
    CHECK (score >= 0 AND score <= 20) -- Validate score range
);

-- ===================================
-- Scoring and Calculation Tables
-- ===================================

-- Scoring factors and weights used in calculations
CREATE TABLE scoring_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_name VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL, -- 'Program', 'Area', 'Difficulty', etc.
    factor_code VARCHAR(50),
    base_value DECIMAL(10,2) DEFAULT 0,
    multiplier DECIMAL(10,2) DEFAULT 1.0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Results and rankings for crews
CREATE TABLE crew_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    itinerary_id INTEGER NOT NULL,
    total_score DECIMAL(12,2) NOT NULL,
    ranking INTEGER,
    choice_number INTEGER, -- #1, #2, etc.
    program_score DECIMAL(10,2) DEFAULT 0,
    difficulty_score DECIMAL(10,2) DEFAULT 0,
    area_score DECIMAL(10,2) DEFAULT 0,
    altitude_score DECIMAL(10,2) DEFAULT 0,
    distance_score DECIMAL(10,2) DEFAULT 0,
    calculation_method VARCHAR(20) DEFAULT 'Total', -- Total, Average, Median, Mode
    year INTEGER DEFAULT 2025, -- Year for crew-specific results
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE,
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id),
    UNIQUE(crew_id, itinerary_id, year) -- Ensure crew-specific results per year
);

-- Audit log for score calculations
CREATE TABLE calculation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    calculation_type VARCHAR(50),
    parameters TEXT, -- JSON of parameters used
    results_count INTEGER,
    year INTEGER DEFAULT 2025, -- Year for crew-specific calculations
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE
);

-- ===================================
-- System Configuration
-- ===================================

-- Application settings and configuration
CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string', -- string, integer, decimal, boolean, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================
-- Views for Common Queries
-- ===================================

-- View for itinerary summary with all key details
CREATE VIEW itinerary_summary AS
SELECT 
    i.id,
    i.itinerary_code,
    i.difficulty,
    i.distance,
    i.total_camps,
    i.staffed_camps,
    i.trail_camps,
    i.dry_camps,
    i.max_altitude,
    i.total_elevation_gain,
    i.description,
    i.covers_south,
    i.covers_central, 
    i.covers_north,
    i.covers_valle_vidal,
    CASE 
        WHEN i.covers_south THEN 'South'
        WHEN i.covers_central THEN 'Central'
        WHEN i.covers_north THEN 'North'
        WHEN i.covers_valle_vidal THEN 'Valle Vidal'
        ELSE 'Mixed'
    END as primary_region
FROM itineraries i;

-- View for program popularity (how many itineraries offer each program)
CREATE VIEW program_popularity AS
SELECT 
    p.id,
    p.name as program_name,
    p.category,
    COUNT(ip.itinerary_id) as itinerary_count,
    ROUND(COUNT(ip.itinerary_id) * 100.0 / (SELECT COUNT(*) FROM itineraries), 2) as percentage_coverage
FROM programs p
LEFT JOIN itinerary_programs ip ON p.id = ip.program_id AND ip.is_available = TRUE
GROUP BY p.id, p.name, p.category
ORDER BY itinerary_count DESC, p.name;

-- View for crew summary with preferences
CREATE VIEW crew_summary AS
SELECT 
    c.id as crew_id,
    c.crew_name,
    c.crew_size,
    COUNT(cm.id) as actual_members,
    cp.area_important,
    cp.programs_important,
    CASE 
        WHEN cp.area_important THEN 'Area preferences set'
        WHEN cp.programs_important THEN 'Program preferences set' 
        ELSE 'Basic preferences'
    END as preference_type,
    cp.year as preference_year,
    c.created_at as crew_created
FROM crews c
LEFT JOIN crew_members cm ON c.id = cm.crew_id
LEFT JOIN crew_preferences cp ON c.id = cp.crew_id
GROUP BY c.id, c.crew_name, c.crew_size, cp.area_important, cp.programs_important, cp.year, c.created_at;

-- View for crew program scoring summary
CREATE VIEW crew_program_summary AS
SELECT 
    c.id as crew_id,
    c.crew_name,
    COUNT(DISTINCT cm.id) as members_count,
    COUNT(DISTINCT ps.program_id) as programs_scored,
    COUNT(ps.id) as total_scores,
    ROUND(AVG(ps.score), 2) as avg_score,
    ps.year as score_year
FROM crews c
JOIN crew_members cm ON c.id = cm.crew_id
JOIN program_scores ps ON cm.id = ps.crew_member_id AND c.id = ps.crew_id
GROUP BY c.id, c.crew_name, ps.year
ORDER BY c.crew_name, ps.year;

-- View for crew results with year isolation
CREATE VIEW crew_results_summary AS
SELECT 
    c.crew_name,
    cr.year,
    COUNT(*) as itineraries_scored,
    MIN(cr.ranking) as best_ranking,
    MAX(cr.total_score) as highest_score,
    cr.calculation_method,
    MAX(cr.calculated_at) as last_calculation
FROM crews c
JOIN crew_results cr ON c.id = cr.crew_id
GROUP BY c.id, c.crew_name, cr.year, cr.calculation_method
ORDER BY c.crew_name, cr.year DESC;

-- ===================================
-- Indexes for Performance
-- ===================================

CREATE INDEX idx_itineraries_difficulty ON itineraries(difficulty);
CREATE INDEX idx_itineraries_distance ON itineraries(distance);
CREATE INDEX idx_itineraries_region ON itineraries(covers_south, covers_central, covers_north, covers_valle_vidal);
CREATE INDEX idx_itineraries_trek_type ON itineraries(trek_type);
CREATE INDEX idx_itinerary_programs_trek_type ON itinerary_programs(trek_type);
CREATE INDEX idx_camps_country ON camps(country);
CREATE INDEX idx_camps_type ON camps(is_staffed, is_trail_camp, is_dry_camp);
CREATE INDEX idx_program_scores_crew ON program_scores(crew_id, program_id);
CREATE INDEX idx_crew_results_ranking ON crew_results(crew_id, ranking);
CREATE INDEX idx_itinerary_camps_day ON itinerary_camps(itinerary_id, day_number);
-- Crew-specific indexes for better performance
CREATE INDEX idx_crew_preferences_crew ON crew_preferences(crew_id);
CREATE INDEX idx_crew_members_crew ON crew_members(crew_id, member_number);
CREATE INDEX idx_program_scores_crew_year ON program_scores(crew_id, year);
CREATE INDEX idx_crew_results_crew_year ON crew_results(crew_id, year, ranking);
CREATE INDEX idx_calculation_log_crew ON calculation_log(crew_id, year);
-- User authentication indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_crew ON users(crew_id);
CREATE INDEX idx_users_active ON users(is_active, is_admin);

-- ===================================
-- Default Configuration Data
-- ===================================

-- Default scoring factors
INSERT INTO scoring_factors (factor_name, category, factor_code, base_value, multiplier, description) VALUES
('Program Factor', 'Program', 'programFactor', 0, 1.5, 'Multiplier applied to each program score in the calculation'),
('Difficulty Delta', 'Difficulty', 'difficultDelta', 0, 1.0, 'Adjustment for difficulty preferences'),
('Max Difficulty', 'Difficulty', 'maxDifficult', 0, 1.0, 'Maximum difficulty threshold'),
('Max Skill', 'Skill', 'maxSkill', 0, 1.0, 'Maximum skill level threshold'),
('Skill Delta', 'Skill', 'skillDelta', 0, 1.0, 'Skill level adjustment factor'),
('Mileage Factor', 'Distance', 'mileageFactor', 0, 1.0, 'Distance scoring multiplier');

-- Default app settings
INSERT INTO app_settings (setting_key, setting_value, setting_type, description) VALUES
('calculation_method', 'Total', 'string', 'Default scoring method: Total, Average, Median, or Mode'),
('program_factor', '1.5', 'decimal', 'Multiplier for activity scores'),
('trek_year', '2025', 'integer', 'Current trek year'),
('max_crew_size', '12', 'integer', 'Maximum number of crew members'),
('revision', '1.0', 'string', 'Database schema revision');

-- ===================================
-- Sample Triggers for Data Integrity
-- ===================================

-- Update timestamp on crew preferences changes
CREATE TRIGGER update_crew_preferences_timestamp 
    AFTER UPDATE ON crew_preferences
    BEGIN
        UPDATE crew_preferences SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamp on crew changes  
CREATE TRIGGER update_crews_timestamp 
    AFTER UPDATE ON crews
    BEGIN
        UPDATE crews SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamp on itinerary changes
CREATE TRIGGER update_itineraries_timestamp 
    AFTER UPDATE ON itineraries
    BEGIN
        UPDATE itineraries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Update timestamp on user changes
CREATE TRIGGER update_users_timestamp 
    AFTER UPDATE ON users
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;