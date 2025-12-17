import camelot
import sqlite3
import re

pdf_file = './legacy_files/2026_Itinerary-Guidebook_12.15.25.pdf'
pages = [22, 23, 80, 81, 112, 113, 146, 147]

conn = sqlite3.connect('philmont_selection.db')
cursor = conn.cursor()

# Collect all program-camp relationships
camp_programs_data = []
programs_not_found = set()
camps_not_found = set()

for page in pages:
    print(f"\n{'='*80}")
    print(f"Processing page {page}...")
    print('='*80)
    
    tables = camelot.read_pdf(pdf_file, pages=str(page), flavor='stream')
    
    for table_idx, table in enumerate(tables):
        df = table.df
        
        if len(df) < 2 or len(df.columns) < 3:
            print(f"  Skipping table {table_idx + 1}: Not enough columns ({len(df.columns)})")
            continue
        
        print(f"\n  Table {table_idx + 1}: {len(df)} rows x {len(df.columns)} columns")
        
        # Show first few rows for debugging
        print("\n  First 5 rows:")
        for i in range(min(5, len(df))):
            print(f"    Row {i}: {[str(df[col][i])[:30] for col in df.columns]}")
        
        # Process each row (skip header rows)
        for row_idx in range(len(df)):
            # Column 0 = Program name
            # Column 1 = Itineraries (ignore)
            # Column 2 or last column = Camps
            
            program_name = str(df[0][row_idx]).strip()
            camps_str = str(df[len(df.columns) - 1][row_idx]).strip()
            
            # Skip empty rows or header rows
            if (not program_name or 
                program_name in ['Program', 'Programs', 'nan'] or
                not camps_str or 
                camps_str in ['Camp', 'Camps', 'nan', 'Camp(s)', 'Camps Offered']):
                continue
            
            # Skip if program name looks like a header or contains trek codes
            if re.match(r'^\d+-\d+', program_name) or 'itinerary' in program_name.lower():
                continue
            
            # Parse camp names (may be comma-separated)
            camp_names = [c.strip() for c in camps_str.split(',')]
            
            for camp_name in camp_names:
                if camp_name and len(camp_name) > 1 and camp_name != 'nan':
                    # Clean up camp name
                    camp_name = camp_name.strip()
                    
                    # Special handling for compound names
                    if "COPE Course / RMSC" in camp_name:
                        camp_name = "RMSC"
                    
                    # Verify program exists in database - try exact match first
                    cursor.execute("SELECT id FROM programs WHERE name = ?", (program_name,))
                    program_result = cursor.fetchone()
                    
                    # If program not found, try partial match
                    if not program_result:
                        # Try matching just the core program name (before any itinerary codes)
                        clean_program = re.sub(r'\s+[NS]-?\d+[AB]?.*$', '', program_name).strip()
                        cursor.execute("SELECT id, name FROM programs WHERE name LIKE ?", (clean_program + '%',))
                        program_result = cursor.fetchone()
                        if program_result:
                            # Update to use the actual program name from database
                            program_name = program_result[1]
                    
                    # Still not found? Try fuzzy matching for known variations
                    if not program_result:
                        if "Archaeology" in program_name:
                            cursor.execute("SELECT id, name FROM programs WHERE name LIKE 'STEM: Archeology%'")
                            program_result = cursor.fetchone()
                        elif "Astronomy & Space Science" in program_name:
                            cursor.execute("SELECT id, name FROM programs WHERE name = 'STEM: Astronomy'")
                            program_result = cursor.fetchone()
                        
                        if program_result:
                            program_name = program_result[1]
                    
                    if not program_result:
                        programs_not_found.add(program_name)
                        continue
                    
                    program_id = program_result[0]
                    
                    # Verify camp exists in database - try exact match first
                    cursor.execute("SELECT id FROM camps WHERE name = ?", (camp_name,))
                    camp_result = cursor.fetchone()
                    
                    # If not found, try partial match (for truncated names)
                    if not camp_result:
                        cursor.execute("SELECT id, name FROM camps WHERE name LIKE ?", (camp_name + '%',))
                        camp_result = cursor.fetchone()
                        if camp_result:
                            # Use the full camp name from database
                            camp_name = camp_result[1]
                    
                    if not camp_result:
                        camps_not_found.add(camp_name)
                        continue
                    
                    camp_id = camp_result[0]
                    
                    # Check if this relationship already exists in our data
                    relationship = (program_id, camp_id, program_name, camp_name)
                    if relationship not in [(r['program_id'], r['camp_id'], r['program_name'], r['camp_name']) for r in camp_programs_data]:
                        camp_programs_data.append({
                            'program_id': program_id,
                            'camp_id': camp_id,
                            'program_name': program_name,
                            'camp_name': camp_name
                        })

print(f"\n{'='*80}")
print("DRY RUN SUMMARY")
print('='*80)

print(f"\nTotal camp-program relationships to insert: {len(camp_programs_data)}")

# Check for existing relationships in database
cursor.execute("SELECT COUNT(*) FROM camp_programs")
existing_count = cursor.fetchone()[0]
print(f"Existing camp_programs records: {existing_count}")

# Count how many would be duplicates
duplicate_count = 0
for data in camp_programs_data:
    cursor.execute("""
        SELECT COUNT(*) FROM camp_programs 
        WHERE program_id = ? AND camp_id = ?
    """, (data['program_id'], data['camp_id']))
    if cursor.fetchone()[0] > 0:
        duplicate_count += 1

print(f"Relationships that already exist (would be skipped): {duplicate_count}")
print(f"New relationships that would be inserted: {len(camp_programs_data) - duplicate_count}")

if programs_not_found:
    print(f"\nPrograms not found in database ({len(programs_not_found)}):")
    for prog in sorted(programs_not_found)[:20]:
        print(f"  - {prog}")
    if len(programs_not_found) > 20:
        print(f"  ... and {len(programs_not_found) - 20} more")

if camps_not_found:
    print(f"\nCamps not found in database ({len(camps_not_found)}):")
    for camp in sorted(camps_not_found)[:20]:
        print(f"  - {camp}")
    if len(camps_not_found) > 20:
        print(f"  ... and {len(camps_not_found) - 20} more")

# Show sample of what would be inserted
print(f"\nSample of new relationships (first 20):")
shown = 0
for data in camp_programs_data[:50]:
    cursor.execute("""
        SELECT COUNT(*) FROM camp_programs 
        WHERE program_id = ? AND camp_id = ?
    """, (data['program_id'], data['camp_id']))
    if cursor.fetchone()[0] == 0:
        print(f"  {data['program_name']} -> {data['camp_name']}")
        shown += 1
        if shown >= 20:
            break

print(f"\n{'='*80}")
print("INSERTING DATA")
print('='*80)

# Insert the new relationships
inserted_count = 0
skipped_count = 0

for data in camp_programs_data:
    # Check if relationship already exists
    cursor.execute("""
        SELECT COUNT(*) FROM camp_programs 
        WHERE program_id = ? AND camp_id = ?
    """, (data['program_id'], data['camp_id']))
    
    if cursor.fetchone()[0] == 0:
        # Insert new relationship
        cursor.execute("""
            INSERT INTO camp_programs (program_id, camp_id)
            VALUES (?, ?)
        """, (data['program_id'], data['camp_id']))
        inserted_count += 1
    else:
        skipped_count += 1

conn.commit()

print(f"\nInserted: {inserted_count} new relationships")
print(f"Skipped: {skipped_count} existing relationships")
print(f"Total processed: {len(camp_programs_data)}")

# Verify final count
cursor.execute("SELECT COUNT(*) FROM camp_programs")
final_count = cursor.fetchone()[0]
print(f"\nTotal camp_programs records in database: {final_count}")

conn.close()
print("\nInsert complete!")
