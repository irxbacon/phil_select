#!/usr/bin/env python3

import argparse
import threading
import time
import webbrowser

from flask import (
    Flask,
)

from utils.admin import is_admin
from utils.crew import get_current_user, get_user_crew_id
from utils.scoring import get_available_trek_types
from utils import config

from routes.admin import admin_routes
from routes.api import api_routes
from routes.base import base_routes
from routes.scores import scoring_routes
from routes.survey import survey_routes
from routes.program import program_routes

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

app.register_blueprint(admin_routes)
app.register_blueprint(api_routes)
app.register_blueprint(base_routes)
app.register_blueprint(scoring_routes)
app.register_blueprint(survey_routes)
app.register_blueprint(program_routes)


# Add custom Jinja2 filter for formatting arrival dates
@app.template_filter("format_arrival_date")
def format_arrival_date(date_str):
    """Format MMDD to MM/DD for display"""
    if date_str and len(date_str) == 4:
        return f"{date_str[:2]}/{date_str[2:]}"
    return date_str


# Add custom Jinja2 filter for difficulty CSS class
@app.template_filter("difficulty_class")
def difficulty_class(difficulty):
    """Convert difficulty to CSS class name"""
    if not difficulty:
        return "secondary"
    difficulty_lower = difficulty.lower()
    if "challenging" in difficulty_lower:
        return "C"
    elif "rugged" in difficulty_lower:
        return "R"
    elif "super strenuous" in difficulty_lower:
        return "SS"
    elif "strenuous" in difficulty_lower:
        return "S"
    else:
        return "secondary"


# Add custom Jinja2 filter for difficulty abbreviation
@app.template_filter("difficulty_abbrev")
def difficulty_abbrev(difficulty):
    """Convert difficulty to abbreviated form"""
    if not difficulty:
        return difficulty
    difficulty_lower = difficulty.lower()
    if "challenging" in difficulty_lower:
        return "C"
    elif "rugged" in difficulty_lower:
        return "R"
    elif "super strenuous" in difficulty_lower:
        return "SS"
    elif "strenuous" in difficulty_lower:
        return "S"
    else:
        return difficulty


@app.context_processor
def inject_admin_status():
    """Inject admin status and user info into all templates"""
    return {
        "is_admin": is_admin(),
        "current_user": get_current_user(),
        "user_crew_id": get_user_crew_id(),
        "available_trek_types": get_available_trek_types(),
    }


def invalidate_crew_cache(crew_id):
    """Invalidate any cached calculations for a crew"""
    # This function can be used if we implement caching in the future
    pass


def open_browser(port):
    """Open web browser to the application URL after a short delay"""

    def delayed_open():
        time.sleep(1.5)  # Wait for Flask to start up
        webbrowser.open(f"http://localhost:{port}")

    thread = threading.Thread(target=delayed_open)
    thread.daemon = True  # Dies when main thread dies
    thread.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Philmont Trek Selection Application"
    )
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
        "--no-browser",
        action="store_true",
        help="Don't automatically open web browser"
    )
    args = parser.parse_args()

    # Automatically open browser unless disabled or in debug mode
    if not args.no_browser and not args.debug:
        open_browser(args.port)
        print(f"Opening browser to http://localhost:{args.port}")
    else:
        print(f"Server starting at http://localhost:{args.port}")

    app.run(debug=args.debug, port=args.port)
