#!/usr/bin/env python3
"""
Parse elevation data from detailed itinerary pages in Philmont Guidebook PDFs.

Extracts:
- Minimum elevation from "Campsite Elevations: X' Minimum, Y' Maximum"
- Maximum elevation from the same line
- Average daily elevation change from itinerary details

Usage:
    python parse_elevation_data.py --pdf legacy_files/2026_Itinerary-Guidebook_12.15.25.pdf --year 2026 --start-page 24
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import camelot
from pypdf import PdfReader


class ElevationDataParser:
    """Parser for elevation data from Philmont itinerary detail pages"""

    def __init__(self, db_path: str = "philmont_selection.db"):
        self.db_path = db_path
        # Pattern to match itinerary codes
        self.trek_patterns = {
            "12-day": re.compile(r"^12-(\d{1,2})$"),
            "9-day": re.compile(r"^9-(\d{1,2})$"),
            "7-day": re.compile(r"^7-(\d{1,2})$"),
            "cavalcade": re.compile(r"^(\d+[A-Z]{1,2}-[NS]|[NS]-\d+[A-Z]{1,2})$"),
        }

    def connect_db(self) -> sqlite3.Connection:
        """Connect to the SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            sys.exit(1)

    def identify_trek_code(self, text: str) -> Optional[str]:
        """Extract trek code from text"""
        # Look for patterns like "Trek 12-1", "Itinerary 9-15", etc.
        patterns = [
            r"Trek\s+(\d+[A-Z]*-\d+[A-Z]*)",
            r"Itinerary\s+(\d+[A-Z]*-\d+[A-Z]*)",
            r"^(\d+[A-Z]*-\d+[A-Z]*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                code = match.group(1)
                # Validate it's a known trek type
                for trek_pattern in self.trek_patterns.values():
                    if trek_pattern.match(code):
                        return code
        return None

    def parse_elevation_range(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract min and max elevations from text like:
        "Campsite Elevations: 6,729' Minimum, 9,343' Maximum"
        """
        pattern = r"Campsite\s+Elevations?:\s*([0-9,]+)'\s*Minimum,?\s*([0-9,]+)'\s*Maximum"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            min_elev = int(match.group(1).replace(',', ''))
            max_elev = int(match.group(2).replace(',', ''))
            return min_elev, max_elev
        
        return None, None

    def parse_elevation_gains_from_text(self, text: str) -> Tuple[Optional[float], Optional[int]]:
        """
        Extract elevation gain data by parsing the text directly.
        Look for lines with the pattern: Day Camp Miles Gain Loss Program Features
        Example: "2Olympia    2.6520'300'Ranger Training; Trail Camp"
        Note: Day number and camp name are often concatenated (e.g., "2Olympia")
        
        Returns: (average_daily_gain, total_gain)
        """
        if not text:
            return None, None
        
        lines = text.split('\n')
        gains = []
        
        # Look for lines that start with a day number (2-12 typically)
        # Day and camp name are often concatenated, so check first character
        for line in lines:
            # Skip header lines and empty lines
            if not line.strip() or 'Day Camp Miles' in line or 'Camping HQ' in line:
                continue
            
            # Check if line starts with a single digit (day number 1-12)
            if not line[0].isdigit():
                continue
            
            # Try to extract the day number (could be 1-2 digits)
            day_match = re.match(r'^(\d{1,2})', line)
            if not day_match:
                continue
            
            try:
                day_num = int(day_match.group(1))
                if not (2 <= day_num <= 12):  # Days 2-12 (skip day 1 which is Camping HQ)
                    continue
            except:
                continue
            
            # Extract all numbers - they're often concatenated like "2.6520'300'"
            # Split on apostrophes and periods to separate the numbers
            numbers = []
            # Use regex to find all sequences of digits (with optional commas)
            number_pattern = re.findall(r'[\d,]+', line)
            for num_str in number_pattern:
                try:
                    num = int(num_str.replace(',', ''))
                    numbers.append(num)
                except ValueError:
                    continue
            
            # We need at least: day number, miles, gain, loss (4 numbers)
            # Pattern: Day(0) Miles(1) Gain(2) Loss(3)
            if len(numbers) >= 4:
                # Day is numbers[0], miles typically numbers[1], but could have decimal
                # Look for the mileage value (usually 0-15 with decimal)
                # Then gain and loss follow
                
                day = numbers[0]
                # The second number should be miles (but might be like 26 from 2.6)
                # Gain values are typically 100-8000
                # Find the first number in range 100-8000 as gain
                for i in range(1, len(numbers) - 1):
                    if 100 <= numbers[i] <= 8000:
                        gain = numbers[i]
                        gains.append(gain)
                        break
        
        if gains and len(gains) >= 3:  # Need at least 3 days of data
            total = sum(gains)
            avg = total / len(gains)
            return round(avg, 2), total
        
        return None, None
    
    def parse_avg_elevation_change(self, pdf_path: str, page_num: int) -> Optional[float]:
        """
        Extract average daily elevation change by parsing the itinerary table
        with columns: Day, camp, Miles, Gain, Loss, Program Features, Food Pickup
        
        Returns the average of the Gain column values.
        """
        try:
            # Try multiple extraction methods
            tables = []
            
            # Try lattice first (for tables with borders)
            try:
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(page_num + 1),  # Convert to 1-indexed
                    flavor='lattice',
                    strip_text='\n'
                )
            except:
                pass
            
            # If no tables found, try stream
            if len(tables) == 0:
                try:
                    tables = camelot.read_pdf(
                        pdf_path,
                        pages=str(page_num + 1),
                        flavor='stream',
                        strip_text='\n',
                        edge_tol=100
                    )
                except:
                    pass
            
            # Look through tables for the itinerary table with Day/Camp/Miles/Gain/Loss columns
            for table in tables:
                df = table.df
                
                if len(df) < 2:  # Need at least header + 1 data row
                    continue
                
                # Check multiple rows for headers (sometimes header spans multiple rows)
                for header_row_idx in range(min(3, len(df))):
                    header_row = df.iloc[header_row_idx]
                    header_text = ' '.join(str(cell).lower() for cell in header_row.values)
                    
                    if 'gain' in header_text and 'loss' in header_text:
                        # Find the Gain column index
                        gain_col = None
                        for idx, cell in enumerate(header_row.values):
                            cell_lower = str(cell).lower().strip()
                            if 'gain' in cell_lower:  # Match 'gain' anywhere in cell
                                gain_col = idx
                                break
                        
                        if gain_col is not None:
                            # Extract gain values from all data rows after the header
                            gains = []
                            for row_idx in range(header_row_idx + 1, len(df)):
                                gain_val = df.iloc[row_idx, gain_col]
                                if gain_val and str(gain_val).strip():
                                    # Parse the number (remove commas, handle different formats)
                                    gain_str = str(gain_val).replace(',', '').strip()
                                    try:
                                        gain = int(gain_str)
                                        if gain > 0:  # Only include positive values (skip zeros)
                                            gains.append(gain)
                                    except (ValueError, AttributeError):
                                        # Skip rows with non-numeric values
                                        continue
                            
                            # Calculate average
                            if gains and len(gains) >= 3:  # Need at least 3 days of data
                                avg = sum(gains) / len(gains)
                                return round(avg, 2)
            
            return None
            
        except Exception as e:
            # If table extraction fails, return None
            return None

    def extract_text_from_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from a specific PDF page"""
        try:
            reader = PdfReader(pdf_path)
            if page_num < len(reader.pages):
                page = reader.pages[page_num]
                return page.extract_text()
            return ""
        except Exception as e:
            print(f"Error reading page {page_num}: {e}")
            return ""

    def parse_itinerary_page(self, pdf_path: str, page_num: int) -> Optional[Dict]:
        """
        Parse a single itinerary detail page (typically the 2nd page of each itinerary).
        
        Returns dict with: {
            'itinerary_code': str,
            'min_altitude': int,
            'max_altitude': int,
            'avg_daily_elevation_change': float
        }
        """
        text = self.extract_text_from_page(pdf_path, page_num)
        if not text:
            return None
        
        # Try to identify the trek code from the page
        lines = text.split('\n')
        trek_code = None
        
        # Look for trek code in first few lines
        for line in lines[:10]:
            trek_code = self.identify_trek_code(line)
            if trek_code:
                break
        
        if not trek_code:
            return None
        
        # Parse elevation data from this page (2nd page has the elevation range)
        min_alt, max_alt = self.parse_elevation_range(text)
        
        # Try parsing elevation gains from text first (faster and more reliable)
        avg_elev_change, total_elev_gain = self.parse_elevation_gains_from_text(text)
        
        # If text parsing didn't work, try table extraction
        if avg_elev_change is None:
            avg_elev_change = self.parse_avg_elevation_change(pdf_path, page_num)
        
        if min_alt is None and max_alt is None and avg_elev_change is None and total_elev_gain is None:
            return None
        
        result = {'itinerary_code': trek_code}
        if min_alt is not None:
            result['min_altitude'] = min_alt
        if max_alt is not None:
            result['max_altitude'] = max_alt
        if avg_elev_change is not None:
            result['avg_daily_elevation_change'] = avg_elev_change
        if total_elev_gain is not None:
            result['total_elevation_gain'] = total_elev_gain
        
        return result

    def parse_all_itineraries(self, pdf_path: str, start_page: int, year: int) -> Dict[str, Dict]:
        """
        Parse all itinerary detail pages starting from start_page.
        Each itinerary typically has 2 pages, so we check the 2nd page of each.
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        print(f"Parsing elevation data from {pdf_path}")
        print(f"Total pages in PDF: {total_pages}")
        print(f"Starting from page {start_page}")
        
        elevation_data = {}
        
        # Get list of itineraries from database for this year
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT itinerary_code FROM itineraries WHERE year = ? ORDER BY itinerary_code",
            (year,)
        )
        itineraries = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"Found {len(itineraries)} itineraries in database for year {year}")
        
        # Parse pages looking for elevation data
        # Start from the given page and check every page
        for page_num in range(start_page - 1, total_pages):  # PDF pages are 0-indexed
            data = self.parse_itinerary_page(pdf_path, page_num)
            if data:
                trek_code = data['itinerary_code']
                elevation_data[trek_code] = data
                print(f"Page {page_num + 1}: Found data for {trek_code}")
                print(f"  Min: {data.get('min_altitude', 'N/A')}', "
                      f"Max: {data.get('max_altitude', 'N/A')}', "
                      f"Avg Daily Change: {data.get('avg_daily_elevation_change', 'N/A')}'")
        
        return elevation_data

    def update_database(self, elevation_data: Dict[str, Dict], year: int, dry_run: bool = False):
        """Update the database with parsed elevation data"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        updated_count = 0
        not_found_count = 0
        
        for trek_code, data in elevation_data.items():
            # Check if itinerary exists
            cursor.execute(
                "SELECT id FROM itineraries WHERE itinerary_code = ? AND year = ?",
                (trek_code, year)
            )
            row = cursor.fetchone()
            
            if not row:
                print(f"Warning: Itinerary {trek_code} not found in database for year {year}")
                not_found_count += 1
                continue
            
            # Build UPDATE query dynamically based on available data
            update_fields = []
            values = []
            
            if 'min_altitude' in data:
                update_fields.append("min_altitude = ?")
                values.append(data['min_altitude'])
            
            if 'max_altitude' in data:
                update_fields.append("max_altitude = ?")
                values.append(data['max_altitude'])
            
            if 'avg_daily_elevation_change' in data:
                update_fields.append("avg_daily_elevation_change = ?")
                values.append(data['avg_daily_elevation_change'])
            
            if 'total_elevation_gain' in data:
                update_fields.append("total_elevation_gain = ?")
                values.append(data['total_elevation_gain'])
            
            if not update_fields:
                continue
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.extend([trek_code, year])
            
            query = f"""
                UPDATE itineraries 
                SET {', '.join(update_fields)}
                WHERE itinerary_code = ? AND year = ?
            """
            
            if dry_run:
                print(f"[DRY RUN] Would update {trek_code}: {data}")
            else:
                cursor.execute(query, values)
                updated_count += 1
        
        if not dry_run:
            conn.commit()
            print(f"\nUpdated {updated_count} itineraries")
        else:
            print(f"\n[DRY RUN] Would update {updated_count} itineraries")
        
        if not_found_count > 0:
            print(f"Warning: {not_found_count} itineraries not found in database")
        
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Parse elevation data from Philmont itinerary detail pages"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the Philmont Itinerary Guidebook PDF"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year of the itineraries (e.g., 2026)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=24,
        help="Page number where detailed itineraries start (default: 24)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse data but don't update the database"
    )
    parser.add_argument(
        "--db",
        default="philmont_selection.db",
        help="Path to the database file"
    )
    
    args = parser.parse_args()
    
    if not Path(args.pdf).exists():
        print(f"Error: PDF file not found: {args.pdf}")
        sys.exit(1)
    
    parser = ElevationDataParser(args.db)
    
    # Parse elevation data
    elevation_data = parser.parse_all_itineraries(args.pdf, args.start_page, args.year)
    
    if not elevation_data:
        print("No elevation data found in PDF")
        sys.exit(1)
    
    print(f"\nParsed elevation data for {len(elevation_data)} itineraries")
    
    # Update database
    parser.update_database(elevation_data, args.year, args.dry_run)
    
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - No changes made to database ===")


if __name__ == "__main__":
    main()
