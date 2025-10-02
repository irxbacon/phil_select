# Philmont Trek Selection System

A Python web application that replicates the functionality of the original Excel spreadsheet for selecting Philmont Scout Ranch trek itineraries. This system helps Scout crews evaluate and rank 12-day trek options based on their preferences and activity interests.

## Features

- **Complete Database Schema**: SQLite database with all trek data from the original Excel file
- **Crew Preferences**: Configure regional preferences, difficulty levels, altitude factors, and peak climbing interests
- **Program Scoring**: Rate 56+ activity programs for each crew member
- **Advanced Scoring**: Multiple calculation methods (Total, Average, Median, Mode)
- **Results Dashboard**: Ranked itinerary list with detailed scoring breakdown
- **Detailed Views**: Complete itinerary information with daily camp schedules
- **Export Functionality**: Print and CSV export capabilities

## Database Contents

- **36 Trek Itineraries** (24 twelve-day treks + 12 nine-day treks)
- **56 Activity Programs** (climbing, historical, range sports, STEM, etc.)
- **169 Backcountry Camps** with elevation and facility data
- **701 Program Assignments** across all itineraries

## Installation

1. **Clone or extract the project files**
   ```bash
   cd /home/brian/git/philmont_selection
   ```

2. **Create a Python virtual environment** (already done)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Import the data** (already completed)
   ```bash
   python import_data.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser to** http://127.0.0.1:5000

## Quick Start Guide

### 1. Set Crew Preferences
- Navigate to **Preferences** in the main menu
- Configure regional preferences (South, Central, North, Valle Vidal)
- Set difficulty level acceptance (Challenging through Super Strenuous)
- Choose altitude considerations and peak climbing interests

### 2. Score Programs
- Go to **Program Scores** to rate activities
- Score each program 0-20 points for each crew member
- Higher scores = greater interest in that activity
- Use the bulk action tools for efficiency

### 3. View Results
- Check **Results** to see your ranked itinerary list
- Try different calculation methods (Total vs Average vs Median vs Mode)
- Click on any itinerary code to see detailed information
- Export results to CSV or print for planning

## Understanding the Scoring System

The application uses a complex scoring algorithm that considers multiple factors:

### Score Components
- **Program Score**: Based on individual activity ratings × program factor (1.5x)
- **Difficulty Score**: Matches accepted difficulty levels (100 points if accepted)
- **Area Score**: Regional preference ranking (if area is important)
- **Altitude Score**: Maximum altitude and daily change considerations
- **Distance Score**: Preference-based distance scoring

### Calculation Methods
- **Total**: Sum of all individual scores
- **Average**: Mean score across all crew members
- **Median**: Middle score when sorted
- **Mode**: Most frequently occurring score

## File Structure

```
philmont_selection/
├── app.py                 # Flask web application
├── schema.sql            # Database schema creation
├── import_data.py        # Excel data import script
├── analyze_excel.py      # Excel analysis utility
├── requirements.txt      # Python dependencies
├── philmont_selection.db # SQLite database (created after import)
├── treks.xlsm           # Original Excel file
├── templates/           # HTML templates
│   ├── base.html        # Base template
│   ├── index.html       # Home page
│   ├── preferences.html # Crew preferences form
│   ├── scores.html      # Program scoring interface
│   ├── results.html     # Results dashboard
│   └── itinerary_detail.html # Detailed itinerary view
└── README.md            # This file
```

## Database Schema

The SQLite database includes the following main tables:
- `programs` - Activity programs with categories
- `camps` - Backcountry camps with locations and facilities
- `itineraries` - Trek itineraries with difficulty and statistics
- `crews` - Crew information and members
- `crew_preferences` - Preference settings
- `program_scores` - Individual activity ratings
- `crew_results` - Calculated results and rankings

## Original Excel Features Replicated

✅ **Complete Data Import**: All worksheets and data tables  
✅ **Preference System**: Area, difficulty, altitude, and peak preferences  
✅ **Program Scoring**: Individual crew member activity ratings  
✅ **Complex Calculations**: Multi-factor scoring with weighted components  
✅ **Multiple Methods**: Total, Average, Median, Mode calculations  
✅ **Results Ranking**: Sorted itinerary list with detailed scores  
✅ **Itinerary Details**: Daily schedules, camps, and statistics  
✅ **Regional Coverage**: South, Central, North, Valle Vidal classification  
✅ **Difficulty Levels**: Challenging, Rugged, Strenuous, Super Strenuous  

## Technology Stack

- **Backend**: Python Flask web framework
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5 + HTML/CSS/JavaScript
- **Data Processing**: Pandas for Excel import
- **Icons**: Font Awesome 6

## Development Notes

This application was created to replace the Excel-based system while maintaining all original functionality. The scoring algorithms have been carefully replicated from the Excel macros to ensure consistent results.

### Key Features from Original Excel:
- Named ranges converted to database relationships
- Complex formulas implemented as Python functions
- VBA macro logic recreated in Flask routes
- User interface adapted for web with improved usability

## Support

For questions about the original Excel spreadsheet functionality, contact the original author. For issues with this web application, check the console output for error details.

## Future Enhancements

Potential improvements could include:
- Multi-crew comparison functionality
- Historical results tracking
- Advanced filtering and search
- Mobile-optimized interface
- Real-time collaboration features
- Integration with Philmont's official systems