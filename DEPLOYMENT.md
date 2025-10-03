# Philmont Trek Selector - Deployment Guide

## ✅ Database Now Persists Across Runs!

The executable now creates a **persistent database file** (`philmont_selection.db`) in the directory where you run it. This means:

- **Preferences are saved** between sessions
- **Program scores are preserved** 
- **Crew member data persists**
- **All changes are maintained** when you restart the app

## How It Works

### First Run
1. Run the executable: `./philmont-trek-selector`
2. The app automatically creates `philmont_selection.db` in the current directory
3. Database is populated with all Philmont itinerary and program data

### Subsequent Runs
- The app uses the existing `philmont_selection.db` file
- All your preferences, scores, and crew data are preserved
- Database location: same directory as where you run the executable

## Database Location

The database is created in your **current working directory** when you run the executable:

```bash
# Example: Running from Desktop
cd ~/Desktop
./philmont-trek-selector
# Creates: ~/Desktop/philmont_selection.db

# Example: Running from Documents
cd ~/Documents
./philmont-trek-selector  
# Creates: ~/Documents/philmont_selection.db
```

## Deployment Options

### Option 1: Single Directory (Recommended)
```bash
mkdir philmont-app
cd philmont-app
./philmont-trek-selector
# Database created: ./philmont_selection.db
```

### Option 2: Application Bundle
```bash
# Create application directory
mkdir PhilmontTrekSelector
cd PhilmontTrekSelector

# Copy executable
cp philmont-trek-selector .

# Run app
./philmont-trek-selector
# Database created: ./philmont_selection.db
```

## Features

- **Persistent Data**: All changes saved automatically
- **No Setup Required**: Database initialized on first run
- **Portable**: Move the directory anywhere, data stays intact
- **Backup Friendly**: Simply copy the `.db` file to backup your data

## Backup Your Data

To backup your preferences and scores:
```bash
cp philmont_selection.db philmont_backup_$(date +%Y%m%d).db
```

## Reset to Defaults

To start fresh:
```bash
rm philmont_selection.db
# Next run will create a fresh database
```

## Technical Details

- **Database**: SQLite 3 (`philmont_selection.db`)
- **Size**: ~500KB with all Philmont data
- **Format**: Standard SQLite database (can be opened with any SQLite tool)
- **Auto-Initialization**: First run copies embedded database to working directory