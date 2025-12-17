# Philmont Trek Selection System - Getting Started Guide

A Python web application that helps Scout crews evaluate and rank Philmont trek itineraries based on their preferences and activity interests.

## Prerequisites

- Python 3.8 or higher
- Git (to clone the repository)
- Web browser (Chrome, Firefox, Safari, Edge)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/bcox-ctv/phil_select.git
cd phil_select
```

### 2. Create a Python Virtual Environment
```bash
# Create virtual environment
python -m venv phil_select

# Activate virtual environment
# On macOS/Linux:
source phil_select/bin/activate

# On Windows:
phil_select\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

You should see output similar to:
```
* Running on http://127.0.0.1:5002
* Debug mode: off
```

### 5. Open Your Browser
Navigate to: `http://127.0.0.1:5002`

## First Time Setup

The application comes with a pre-configured database and sample data, so you can start using it immediately.

## Using the Application

### Step 1: Set Crew Preferences

1. **Navigate to "Preferences"** from the main menu
2. **Configure your crew's preferences:**

   **Regional Preferences (Optional):**
   - Check "Area preferences are important" if you want regional scoring
   - Rank areas 1-4 (1 = most preferred): South, Central, North, Valle Vidal

   **Difficulty Levels:**
   - Select which difficulty levels your crew accepts
   - Options: Challenging (C), Rugged (R), Strenuous (S), Super Strenuous (SS)

   **Altitude Preferences:**
   - Maximum altitude importance
   - Total elevation gain importance  
   - Daily altitude change importance

   **Peak Climbing:**
   - Select which peaks your crew wants to climb
   - Baldy Mountain, Mount Phillips, Tooth of Time, etc.

   **Camp Preferences:**
   - Maximum dry camps allowed
   - Showers required (yes/no)
   - Layovers required (yes/no)
   - Food resupply preferences

3. **Add Crew Members** (if not already done):
   - Click "Add New Member"
   - Enter name, age, and skill level (1-10 scale)
   - Repeat for all crew members

4. **Save Preferences**

### Step 2: Score Activity Programs

1. **Go to "Program Scores"** from the main menu
2. **Rate each activity program** for each crew member:
   - Score each program 0-20 (20 = highest interest)
   - Programs include: climbing, historical sites, STEM activities, etc.
   - Categories: Climbing, Historical, Range Sports, STEM, Nature, Crafts, etc.

3. **Scoring Tips:**
   - Higher scores = more interest in that activity
   - Consider each member's individual interests
   - You can use the same score for multiple members if they have similar interests

4. **Save Scores**

### Step 3: View Results

1. **Navigate to "Results"** from the main menu
2. **Choose calculation method:**
   - **Total**: Sum all crew member scores (good for larger crews)
   - **Average**: Mean score across crew (good for comparing different crew sizes)
   - **Median**: Middle score (less affected by outliers)
   - **Mode**: Most common score (rarely used)

3. **Review ranked itineraries:**
   - Itineraries are ranked by total score (highest first)
   - Each row shows:
     - Itinerary code (e.g., "12-1", "12-10")
     - Total score
     - Score breakdown by component
     - Distance, difficulty, and other details

4. **Click on any itinerary code** to see detailed information:
   - Daily camp schedule
   - Available programs at each location
   - Elevation profile and statistics
   - Difficulty rating and area coverage

## Understanding the Scoring System

### Score Components

Your final itinerary scores include multiple weighted factors:

1. **Program Score** (largest component)
   - Based on your activity program ratings
   - Multiplied by 1.5x factor
   - Higher for itineraries with activities you rated highly

2. **Camp Score**
   - Dry camps: Scored by count (fewer = higher score)
   - Trail camps: Similar scoring system
   - Total camps bonus: 7 total camps = optimal (100 bonus points)
   - Shower/layover bonuses if required

3. **Difficulty Score**
   - Full points if itinerary matches accepted difficulty levels
   - Zero points if difficulty level not accepted

4. **Area Score** (if enabled)
   - Based on your regional preferences
   - Higher for preferred regions

5. **Distance Score**
   - Based on trek mileage
   - Optimized around 50-mile range

6. **Altitude Score** (if enabled)
   - Maximum elevation reached
   - Total elevation gain
   - Daily elevation change

7. **Peak Score**
   - Bonus points for desired peak climbs
   - Baldy Mountain = highest bonus
   - Based on your Landmarks program scores

### Interpreting Results

- **High scores (600+)**: Excellent matches for your preferences
- **Medium scores (400-600)**: Good options worth considering  
- **Low scores (<400)**: May not align well with your preferences
- **Negative scores**: Usually indicate violated requirements (like exceeding max dry camps)

## Tips for Best Results

### Setting Preferences
- **Be realistic** about your crew's skill level and preferences
- **Don't over-constrain** - too many requirements may eliminate good options
- **Consider compromise** - perfect matches are rare

### Program Scoring
- **Score honestly** - inflated scores won't improve your results
- **Consider all members** - balance individual vs. group interests
- **Use the full scale** - don't be afraid of low scores for uninteresting programs

### Reviewing Results
- **Look beyond the top choice** - the #2 or #3 option might be better for specific reasons
- **Check the detailed view** - daily schedules matter more than overall scores
- **Consider backup options** - popular itineraries may not be available

## Advanced Features

### Multiple Calculation Methods
Try different calculation methods to see how they affect rankings:
- **Total**: Best for crews where everyone participates equally
- **Average**: Better for mixed-age crews or varying participation levels

### Program Chart
Visit the "Program Chart" to see which activities your crew scored highest - helps understand why certain itineraries rank well.

### Admin Features
The application includes admin features for managing multiple crews and user accounts (if needed for large groups).

## Troubleshooting

### Common Issues

**"No results showing"**
- Make sure you've saved both preferences and program scores
- Check that you've accepted at least one difficulty level

**"All scores are very low"**
- Review your program scores - make sure you're using the full 0-20 scale
- Check if you've set impossible constraints (like max 0 dry camps)

**"Application won't start"**
- Make sure virtual environment is activated
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

### Getting Help

1. Check the terminal output for error messages
2. Make sure you're using the correct URL: `http://127.0.0.1:5002`
3. Try refreshing your browser or clearing cache
4. Restart the application if needed (Ctrl+C, then `python app.py` again)

## Sample Workflow

Here's a typical session for a new crew:

1. **Start the app**: `python app.py`
2. **Add crew members** (Preferences page)
3. **Set basic preferences**: difficulty levels, maybe max dry camps
4. **Score programs** for each member (30-45 minutes)
5. **View results** with "Total" method
6. **Review top 5-10 itineraries** in detail
7. **Adjust preferences** if needed and re-check results
8. **Export or print** final rankings for crew discussion

## Next Steps

Once you have your rankings:
1. **Discuss results** with your crew
2. **Research specific itineraries** using Philmont's official resources
3. **Prepare backup choices** in case your top picks aren't available
4. **Submit your trek application** through official Philmont channels

Remember: This tool helps you make informed decisions, but the final trek selection is handled by Philmont Scout Ranch through their official reservation system.