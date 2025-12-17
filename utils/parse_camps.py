import camelot
import sqlite3
import re

pdf_file = './legacy_files/2026_Itinerary-Guidebook_12.15.25.pdf'
pages_map = {
    24: '12-day',
    25: '12-day',
    82: '9-day',
    114: '7-day',
    148: 'cavalcade'
}

conn = sqlite3.connect('philmont_selection.db')
cursor = conn.cursor()

# Trek code pattern
trek_pattern = re.compile(r'^(\d+-\d+|[NS]-\d+[AB])\s*-\s*\d+\s*Mi\.\s*-\s*[A-Z]+$')

# Collect all itinerary-camp relationships
itinerary_camps_data = []

for page, trek_type in pages_map.items():
    print(f"\nProcessing page {page} ({trek_type})...")
    tables = camelot.read_pdf(pdf_file, pages=str(page), flavor='stream')
    
    for table in tables:
        df = table.df
        
        if len(df) < 2:
            continue
        
        # Find all rows that contain trek codes (these are subtable headers)
        subtable_rows = []
        for row_idx in range(len(df)):
            # Check if this row has trek codes
            has_trek_code = False
            for col in df.columns:
                value = str(df[col][row_idx]).strip()
                if trek_pattern.match(value):
                    has_trek_code = True
                    break
            if has_trek_code:
                subtable_rows.append(row_idx)
        
        print(f"  Found {len(subtable_rows)} subtable(s)")
        
        # Process each subtable
        for subtable_idx, trek_code_row in enumerate(subtable_rows):
            # Extract trek codes from this row
            trek_codes = []
            for col in df.columns:
                value = str(df[col][trek_code_row]).strip()
                match = trek_pattern.match(value)
                if match:
                    trek_codes.append((col, match.group(1)))
            
            print(f"    Subtable {subtable_idx + 1} trek codes: {[code for _, code in trek_codes]}")
            
            # Determine the end row for this subtable
            if subtable_idx + 1 < len(subtable_rows):
                end_row = subtable_rows[subtable_idx + 1]
            else:
                end_row = len(df)
            
            # Process camp data for each trek in this subtable
            for col_idx, itinerary_code in trek_codes:
                camps_for_itinerary = []
                for row_idx in range(trek_code_row + 1, end_row):
                    camp_name = str(df[col_idx][row_idx]).strip()
                    # Skip empty, too short, or if contains digits
                    if (camp_name and 
                        len(camp_name) > 1 and 
                        not any(char.isdigit() for char in camp_name) and
                        camp_name not in ['Camp', 'Campsite', 'Rendezvous']):
                        camps_for_itinerary.append(camp_name)
                
                print(f"      {itinerary_code}: {len(camps_for_itinerary)} camps")
                
                # Store the data
                for day_number, camp_name in enumerate(camps_for_itinerary, start=1):
                    itinerary_camps_data.append({
                        'itinerary_code': itinerary_code,
                        'camp_name': camp_name,
                        'day_number': day_number,
                        'trek_type': trek_type
                    })

print(f"\n{'='*60}")
print(f"Total itinerary-camp relationships: {len(itinerary_camps_data)}")
print(f"{'='*60}")

# Now update the database
print("\nClearing existing 2026 itinerary_camps data...")
cursor.execute("DELETE FROM itinerary_camps WHERE year = 2026")
print(f"  Deleted {cursor.rowcount} records")

# Insert new data
print("\nInserting new camp data...")
inserted = 0
not_found_camps = set()
not_found_itineraries = set()

for data in itinerary_camps_data:
    # Get itinerary_id
    cursor.execute("""
        SELECT id FROM itineraries 
        WHERE itinerary_code = ? AND year = 2026
    """, (data['itinerary_code'],))
    itinerary_result = cursor.fetchone()
    
    if not itinerary_result:
        not_found_itineraries.add(data['itinerary_code'])
        continue
    
    itinerary_id = itinerary_result[0]
    
    # Get camp_id (should exist now)
    cursor.execute("SELECT id FROM camps WHERE name = ?", (data['camp_name'],))
    camp_result = cursor.fetchone()
    
    if not camp_result:
        not_found_camps.add(data['camp_name'])
        continue
    
    camp_id = camp_result[0]
    
    # Insert itinerary_camp relationship
    cursor.execute("""
        INSERT INTO itinerary_camps (itinerary_id, camp_id, day_number, year)
        VALUES (?, ?, ?, 2026)
    """, (itinerary_id, camp_id, data['day_number']))
    inserted += 1

conn.commit()

print(f"\n{'='*60}")
print(f"Successfully inserted {inserted} itinerary-camp relationships")
print(f"{'='*60}")

if not_found_camps:
    print(f"\nCamps not found in database ({len(not_found_camps)}):")
    for camp in sorted(not_found_camps):
        print(f"  - {camp}")

if not_found_itineraries:
    print(f"\nItineraries not found ({len(not_found_itineraries)}):")
    for code in sorted(not_found_itineraries):
        print(f"  - {code}")

# Verify the data
cursor.execute("""
    SELECT COUNT(*), i.trek_type 
    FROM itinerary_camps ic
    JOIN itineraries i ON ic.itinerary_id = i.id
    WHERE ic.year = 2026 
    GROUP BY i.trek_type
""")
print(f"\nVerification - Records by trek type:")
for count, trek_type in cursor.fetchall():
    print(f"  {trek_type}: {count} records")

# Count itineraries per trek type
cursor.execute("""
    SELECT COUNT(DISTINCT i.itinerary_code), i.trek_type 
    FROM itinerary_camps ic
    JOIN itineraries i ON ic.itinerary_id = i.id
    WHERE ic.year = 2026 
    GROUP BY i.trek_type
""")
print(f"\nItineraries with camp data:")
for count, trek_type in cursor.fetchall():
    print(f"  {trek_type}: {count} itineraries")

conn.close()
print("\nDone!")
