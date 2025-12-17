# Philmont Trek Data Importer

## Overview

This system imports Philmont trek data from the annual Itinerary Guidebook PDFs into the database. The importer extracts key information from the summary tables that appear in each PDF.

## Files Created

### `pdf_import_smart.py`
The main importer script that:
- Automatically finds the correct summary table pages in PDFs
- Extracts trek codes, difficulty ratings, distances, trail camps, and dry camps
- Handles all trek types: 12-day, 9-day, 7-day, and cavalcade
- Supports multiple years with proper database constraints

### `fix_database_schema.py` 
A utility script that updated the database schema to allow the same itinerary codes across different years (e.g., "12-1" can exist for both 2024 and 2025).

### Helper Scripts
- `examine_page.py`: Utility to examine specific PDF pages during development
- `search_pdf.py`: Utility to search for text patterns across PDFs

## Database Schema Updates

Updated the `itineraries` table to:
- Allow duplicate itinerary codes across different years
- Added `UNIQUE(itinerary_code, year)` constraint instead of just `UNIQUE(itinerary_code)`
- Proper support for the `trek_type` field

## Usage

### Import 2024 Data
```bash
python pdf_import_smart.py --pdf legacy_files/2024-Itinerary-Guidebook.pdf --year 2024
```

### Import 2025 Data  
```bash
python pdf_import_smart.py --pdf legacy_files/2025-Itinerary-Guidebook.pdf --year 2025
```

### Dry Run (Preview Only)
```bash
python pdf_import_smart.py --pdf legacy_files/2024-Itinerary-Guidebook.pdf --year 2024 --dry-run
```

## Data Extracted

For each trek, the importer extracts:
- **Trek Code**: e.g., "12-1", "9-15", "7-3", "1A-S"
- **Trek Type**: 12-day, 9-day, 7-day, or cavalcade
- **Difficulty**: Challenging, Rugged, Strenuous, Super Strenuous
- **Distance**: Approximate miles
- **Trail Camps**: Number of trail camps
- **Dry Camps**: Number of dry camps (when available)

## Current Database Status

After importing both 2024 and 2025 data:

| Year | Trek Type | Count |
|------|-----------|-------|
| 2024 | 12-day    | 34    |
| 2024 | 9-day     | 15    |
| 2024 | 7-day     | 16    |
| 2024 | cavalcade | 19    |
| 2025 | 12-day    | 24    |
| 2025 | 9-day     | 12    |
| 2025 | 7-day     | 14    |
| **Total** |       | **134 treks** |

## Trek Code Patterns

The importer recognizes these trek code patterns:
- **12-day treks**: `12-1` through `12-34` (varies by year)
- **9-day treks**: `9-1` through `9-15` (varies by year)  
- **7-day treks**: `7-1` through `7-16` (varies by year)
- **Cavalcade treks**: `1A-N`, `1A-S`, `1B-N`, `2A-S`, etc.

## Future Years

To import future years (e.g., 2026):

1. The page numbers will likely be different, but the script automatically finds the correct pages by searching for the table headers:
   - "Programs Included in 12-Day Itineraries"
   - "Programs Included in 9-Day Itineraries" 
   - "Programs Included in 7-Day Itineraries"
   - "Programs Included in Cavalcade Itineraries"

2. The table format should remain consistent

3. Simply run:
   ```bash
   python pdf_import_smart.py --pdf legacy_files/2026-Itinerary-Guidebook.pdf --year 2026
   ```

## Technical Notes

- Uses `pdfplumber` library for PDF text and table extraction
- Handles missing or empty cells in tables gracefully
- Updates existing records or inserts new ones as appropriate
- Provides detailed console output during import process
- Includes error handling for malformed data

## Error Handling

The importer includes robust error handling:
- Skips malformed trek codes
- Handles missing table cells
- Reports import statistics
- Continues processing even if individual records fail
- Provides detailed error messages

This system provides a reliable, automated way to keep the trek database up-to-date with each year's new Philmont guidebook.