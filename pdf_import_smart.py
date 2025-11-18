#!/usr/bin/env python3
"""
Philmont Trek Data Importer

This script extracts trek information from Philmont Itinerary Guidebook PDFs
and imports them into the database. It handles multiple years and formats.

The script looks for tables containing:
- Trek codes (12-1, 9-15, 7-3, 1A-N, etc.)
- Difficulty ratings (C, R, S, SS)
- Distance in miles
- Number of trail camps, dry camps
- Program information

Usage:
    python pdf_import_smart.py --pdf legacy_files/2024-Itinerary-Guidebook.pdf --year 2024
    python pdf_import_smart.py --pdf legacy_files/2025-Itinerary-Guidebook.pdf --year 2025
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import camelot
import pandas as pd


class PhilmontTrekImporter:
    """Imports trek data from Philmont Itinerary Guidebook PDFs"""

    def __init__(self, db_path: str = "philmont_selection.db"):
        self.db_path = db_path
        self.trek_patterns = {
            "12-day": re.compile(r"^12-(\d{1,2})$"),  # 12-1 through 12-99 (covers 12-34)
            "9-day": re.compile(r"^9-(\d{1,2})$"),  # 9-1 through 9-99
            "7-day": re.compile(r"^7-(\d{1,2})$"),  # 7-1 through 7-99
            "cavalcade": re.compile(
                r"^(\d+[A-Z]{1,2}-[NS]|[NS]-\d+[A-Z]{1,2})$"
            ),  # 1A-N, 1A-S, 10A-N, N-1A, N-10B, etc.
        }
        self.difficulty_map = {
            "C": "Challenging",
            "R": "Rugged",
            "S": "Strenuous",
            "SS": "Super Strenuous",
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

    def identify_trek_type(self, trek_code: str) -> Optional[str]:
        """Identify the type of trek from its code"""
        for trek_type, pattern in self.trek_patterns.items():
            if pattern.match(trek_code):
                return trek_type
        return None

    def find_trek_tables(self, pdf_path: str) -> List[Tuple[int, Dict]]:
        """
        Find pages containing trek data tables using Camelot.

        Returns list of (page_number, table_data) tuples
        """
        tables_found = []

        # Define specific pages that contain trek summary tables
        target_pages = self._find_summary_table_pages(pdf_path)

        if not target_pages:
            print("No summary table pages found")
            return tables_found

        print(f"Analyzing PDF: {pdf_path}")
        print(f"Found {len(target_pages)} pages with potential trek tables")

        for page_num in target_pages:
            print(f"Extracting tables from page {page_num}")
            
            try:
                # Use Camelot to extract tables from this specific page
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(page_num),
                    flavor='lattice',  # Use lattice for tables with clear borders
                    strip_text='\n'
                )
                
                if len(tables) == 0:
                    # Try stream flavor if lattice didn't find tables
                    tables = camelot.read_pdf(
                        pdf_path,
                        pages=str(page_num),
                        flavor='stream',
                        strip_text='\n'
                    )
                
                print(f"  Found {len(tables)} table(s) on page {page_num}")
                
                for table in tables:
                    # Convert to list of lists for processing
                    df = table.df
                    table_data = df.values.tolist()
                    
                    processed_table = self._process_summary_table(table_data, page_num)
                    if processed_table:
                        tables_found.append((page_num, processed_table))
                        print(f"  - Extracted {len(processed_table)} trek entries")
            
            except Exception as e:
                print(f"  Error extracting from page {page_num}: {e}")
                continue

        return tables_found

    def _find_summary_table_pages(self, pdf_path: str) -> List[int]:
        """
        Find pages containing summary tables by searching for specific headers using Camelot.

        Returns list of page numbers
        """
        target_pages = []
        
        # For now, use known page numbers for common guidebook formats
        # Trek summary tables often span multiple pages, so we include all relevant pages
        # These are typical pages for different trek types
        known_pages = {
            # 12-day programs (34 treks across multiple pages)
            19: "12-day programs (page 1)",
            20: "12-day programs (page 2)",
            21: "12-day programs (page 3)",
            22: "12-day programs (page 4)",
            # 9-day programs
            94: "9-day programs", 
            # 7-day programs
            131: "7-day programs",
            # Cavalcade programs (19 treks across multiple pages)
            168: "cavalcade programs (page 1)",
            169: "cavalcade programs (page 2)"
        }
        
        for page_num, description in known_pages.items():
            try:
                # Try to read a table from this page to verify it exists
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(page_num),
                    flavor='lattice'
                )
                
                if len(tables) > 0:
                    target_pages.append(page_num)
                    print(f"Found {description} table on page {page_num}")
            except Exception:
                # Page doesn't exist or no tables found, skip it
                pass
        
        return target_pages

    def _process_summary_table(
        self, table: List[List[str]], page_num: int
    ) -> Optional[Dict[str, Dict]]:
        """
        Process a summary table where trek codes are columns and data are rows.

        Returns dict mapping trek codes to their data
        """
        if (
            not table or len(table) < 4
        ):  # Need at least header + difficulty + distance + trail camps
            return None

        # First row should contain trek codes
        header_row = table[0]
        if not header_row or len(header_row) < 2:
            return None

        # Extract trek codes from header (skip first column which is the row label)
        trek_codes = []

        # Handle special case for 12-day treks where the prefix and numbers are in separate columns
        if len(header_row) > 2 and str(header_row[1]).strip() == "12-":
            # 12-day format: column 1 is "12-", remaining columns are numbers
            for i in range(2, len(header_row)):
                number = str(header_row[i]).strip() if header_row[i] else ""
                if number and number.isdigit():
                    code = f"12-{number}"
                    if self.identify_trek_type(code):
                        trek_codes.append(code)
        else:
            # Standard format: each column contains a complete trek code
            # For page 19, numbers without prefix should be assumed to be 12-day
            for i in range(1, len(header_row)):
                code = str(header_row[i]).strip() if header_row[i] else ""
                if code:
                    # If it's just a number, assume it's a 12-day trek
                    if code.isdigit():
                        code = f"12-{code}"
                    
                    if self.identify_trek_type(code):
                        trek_codes.append(code)

        if not trek_codes:
            print("    No valid trek codes found in header row")
            return None

        print(
            f"    Found {len(trek_codes)} trek codes: {trek_codes}"
        )

        # Process data rows
        trek_data = {}

        # Initialize trek data for each code
        for code in trek_codes:
            trek_type = self.identify_trek_type(code)
            trek_data[code] = {"trek_type": trek_type}

        # Determine column offset based on table format
        is_12_day_format = len(header_row) > 2 and str(header_row[1]).strip() == "12-"
        column_offset = 2 if is_12_day_format else 1

        # Process each data row
        for row_idx, row in enumerate(table[1:], 1):
            if not row or len(row) < column_offset + 1:
                continue

            row_label = str(row[0]).strip().lower() if row[0] else ""

            # Map row labels to our data fields
            if "difficulty" in row_label:
                for i, code in enumerate(trek_codes, column_offset):
                    if i < len(row) and row[i]:
                        difficulty = str(row[i]).strip().upper()
                        trek_data[code]["difficulty"] = self.difficulty_map.get(
                            difficulty, difficulty
                        )

            elif "distance" in row_label:
                for i, code in enumerate(trek_codes, column_offset):
                    if i < len(row) and row[i]:
                        distance = self._parse_number(str(row[i]))
                        if distance:
                            trek_data[code]["distance"] = distance

            elif "trail" in row_label and "camp" in row_label:
                for i, code in enumerate(trek_codes, column_offset):
                    if i < len(row) and row[i]:
                        trail_camps = self._parse_number(str(row[i]))
                        if trail_camps is not None:
                            trek_data[code]["trail_camps"] = trail_camps

            elif "dry" in row_label and "camp" in row_label:
                for i, code in enumerate(trek_codes, column_offset):
                    if i < len(row) and row[i]:
                        dry_camps = self._parse_number(str(row[i]))
                        if dry_camps is not None:
                            trek_data[code]["dry_camps"] = dry_camps

        # Filter out treks with insufficient data and calculate staffed_camps
        valid_treks = {}
        for code, data in trek_data.items():
            if len(data) > 1:  # More than just trek_type
                # Calculate staffed_camps: days - 2 - trail_camps
                # Determine number of days based on trek type
                trek_type = data.get('trek_type', '')
                trail_camps = data.get('trail_camps', 0)
                
                if trek_type == '12-day':
                    days = 12
                elif trek_type == '9-day':
                    days = 9
                elif trek_type == '7-day':
                    days = 7
                elif trek_type == 'cavalcade':
                    days = 7  # Cavalcade treks are typically 7 days
                else:
                    days = 0
                
                if days > 0 and trail_camps is not None:
                    staffed_camps = days - 2 - trail_camps
                    # Make sure it's not negative
                    if staffed_camps >= 0:
                        data['staffed_camps'] = staffed_camps
                
                valid_treks[code] = data
                print(
                    f"    Found: {code} ({data.get('trek_type', 'unknown')}) - {data.get('difficulty', 'N/A')} - {data.get('distance', 'N/A')} mi - Trail: {trail_camps}, Staffed: {data.get('staffed_camps', 'N/A')}"
                )

        return valid_treks if valid_treks else None

    def _parse_number(self, text: str) -> Optional[int]:
        """Parse a number from text, handling various formats"""
        if not text:
            return None

        # Extract first number found
        match = re.search(r"\d+", str(text))
        if match:
            return int(match.group())
        return None

    def extract_program_data(self, pdf_path: str) -> Dict[str, List[str]]:
        """
        Extract program data using Camelot from pages that contain trek summary tables.

        Returns dict mapping program names to lists of itinerary codes that offer them.
        """
        program_data = {}

        # Pages that contain program grids
        program_pages = {
            19: "12-day",
            94: "9-day",
            131: "7-day",
            168: "cavalcade",
        }

        for page_num, trek_type in program_pages.items():
            print(f"Extracting program data from page {page_num} ({trek_type})")
            
            try:
                # Use Camelot to extract tables
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(page_num),
                    flavor='lattice',
                    strip_text='\n'
                )
                
                if len(tables) == 0:
                    # Try stream flavor
                    tables = camelot.read_pdf(
                        pdf_path,
                        pages=str(page_num),
                        flavor='stream',
                        strip_text='\n'
                    )
                
                for table in tables:
                    # Convert to list of lists
                    df = table.df
                    table_data = df.values.tolist()
                    
                    page_programs = self._process_program_table(
                        table_data, trek_type, page_num
                    )
                    if page_programs:
                        # Merge programs from this page
                        for program_name, itineraries in page_programs.items():
                            if program_name not in program_data:
                                program_data[program_name] = []
                            program_data[program_name].extend(itineraries)
            
            except Exception as e:
                print(f"  Error extracting program data from page {page_num}: {e}")
                continue

        return program_data

    def _process_program_table(
        self, table: List[List[str]], trek_type: str, page_num: int
    ) -> Optional[Dict[str, List[str]]]:
        """
        Process a program table where itinerary codes are columns and programs are rows.

        Returns dict mapping program names to lists of itinerary codes.
        """
        if not table or len(table) < 6:  # Need header + data rows
            return None

        # First row should contain itinerary codes
        header_row = table[0]
        if not header_row or len(header_row) < 2:
            return None

        # Extract itinerary codes from header
        itinerary_codes = []

        # Handle different header formats
        if (
            trek_type == "12-day"
            and len(header_row) > 2
            and str(header_row[1]).strip() == "12-"
        ):
            # 12-day format: column 1 is "12-", remaining columns are numbers
            for i in range(2, len(header_row)):
                number = str(header_row[i]).strip() if header_row[i] else ""
                if number and number.isdigit():
                    code = f"12-{number}"
                    itinerary_codes.append(code)
        else:
            # Standard format: each column contains a complete itinerary code
            # For 12-day treks, numbers without prefix should be assumed to be 12-day
            for i in range(1, len(header_row)):
                code = str(header_row[i]).strip() if header_row[i] else ""
                if code:
                    # If it's just a number and we're processing 12-day data, add prefix
                    if code.isdigit() and trek_type == "12-day":
                        code = f"12-{code}"
                    
                    if self.identify_trek_type(code):
                        itinerary_codes.append(code)

        if not itinerary_codes:
            print(
                f"    No valid itinerary codes found in header row on page {page_num}"
            )
            return None

        print(
            f"    Found {len(itinerary_codes)} itinerary codes: {itinerary_codes}"
        )

        # Determine column offset based on table format
        is_12_day_format = (
            trek_type == "12-day"
            and len(header_row) > 2
            and str(header_row[1]).strip() == "12-"
        )
        column_offset = 2 if is_12_day_format else 1

        # Process program rows (skip first 5 rows: header, difficulty, distance, trail camps, dry camps)
        program_data = {}

        for row_idx, row in enumerate(
            table[5:], 5
        ):  # Start from row 5 (programs start there)
            if not row or len(row) < column_offset + 1:
                continue

            program_name = str(row[0]).strip() if row[0] else ""
            if not program_name:
                continue

            # Clean up program name
            program_name = self._normalize_program_name(program_name)
            if not program_name:
                continue

            # Check which itineraries have this program (marked with 'X')
            program_itineraries = []
            for i, code in enumerate(itinerary_codes, column_offset):
                if i < len(row) and row[i]:
                    cell_value = str(row[i]).strip().upper()
                    if cell_value == "X":
                        program_itineraries.append(code)

            if program_itineraries:
                program_data[program_name] = program_itineraries
                if len(program_itineraries) <= 5:
                    print(f"    {program_name}: {program_itineraries}")
                else:
                    print(f"    {program_name}: {len(program_itineraries)} itineraries")

        return program_data if program_data else None

    def _normalize_program_name(self, raw_name: str) -> Optional[str]:
        """
        Normalize program names to match database entries.
        """
        if not raw_name:
            return None

        # Remove extra whitespace
        name = raw_name.strip()
        if not name:
            return None

        # Skip non-program rows
        skip_patterns = [
            "itinerary numbers",
            "hiking difficulty",
            "distance ",
            "trail camps",
            "dry camps",
        ]

        for pattern in skip_patterns:
            if pattern in name.lower():
                return None

        # Some basic name mapping for common variations
        name_mappings = {
            "Archery - 3 Dimensional": "Range Sports: 3D Archery",
            "Atlatl (Dart-Throwing)": "Range Sports: Atlatl Throwing",
            "Baldy Mountain Hike": "Landmarks: Baldy Mountain",
            "Blacksmithing": "Historical: Blacksmithing",
            "Rock Climbing": "Climbing: Rock Climbing",
            "Astronomy": "STEM: Astronomy",
            "Archaeology": "STEM: Archeology",
            "Tomahawk Throwing": "Range Sports: Tomahawk Throwing",
            "Conservation Project": "Low Impact Camping",
        }

        # Check for exact match first
        if name in name_mappings:
            return name_mappings[name]

        # Return original name for database lookup
        return name

    def extract_camp_data(self, pdf_path: str) -> Dict[str, List[str]]:
        """
        Extract camp data from "Itinerary Rendezvous Locations" pages using Camelot.

        Returns dict mapping itinerary codes to lists of camp names.
        """
        camp_data = {}

        # Pages that contain "Itinerary Rendezvous Locations" sections
        rendezvous_pages = {
            24: "12-day",
            25: "12-day",
            97: "9-day",
            134: "7-day",
            171: "cavalcade",
        }

        for page_num, trek_type in rendezvous_pages.items():
            print(f"Extracting camp data from page {page_num} ({trek_type})")
            
            try:
                # Use Camelot to extract tables
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(page_num),
                    flavor='lattice',
                    strip_text='\n'
                )
                
                if len(tables) == 0:
                    # Try stream flavor
                    tables = camelot.read_pdf(
                        pdf_path,
                        pages=str(page_num),
                        flavor='stream',
                        strip_text='\n'
                    )
                
                for table in tables:
                    # Convert to list of lists
                    df = table.df
                    table_data = df.values.tolist()
                    
                    # Convert table to text for processing
                    text_lines = []
                    for row in table_data:
                        line = ' '.join(str(cell) if cell else '' for cell in row).strip()
                        if line:
                            text_lines.append(line)
                    
                    text = '\n'.join(text_lines)
                    
                    page_camps = self._process_rendezvous_locations(
                        text, trek_type, page_num
                    )

                    if page_camps:
                        # Merge camps from this page
                        for itinerary_code, camps in page_camps.items():
                            if itinerary_code not in camp_data:
                                camp_data[itinerary_code] = []
                            camp_data[itinerary_code].extend(camps)
            
            except Exception as e:
                print(f"  Error extracting camp data from page {page_num}: {e}")
                continue

        return camp_data

    def _process_camp_text(
        self, text: str, trek_type: str, page_num: int
    ) -> Optional[Dict[str, List[str]]]:
        """
        Process camp text from "Itineraries at a Glance" sections.

        Format:
        12-16 - 65 Mi. - R 12-17 - 65 Mi. - R 12-18 - 66 Mi. - S 12-19 - 66 Mi. - S 12-20 - 66 Mi. - S
        House Canyon Magpie House Canyon Heck Meadow Herradura
        Metcalf Station Urraca Chase Cow Cimarroncito Miners Park
        Dan Beard Crater Lake Coyote Howl Cyphers Mine Clarks Fork
        ...

        Returns dict mapping itinerary codes to lists of camp names.
        """
        if not text:
            return None

        lines = text.split("\n")

        # Find header lines with itinerary codes and subsequent camp data lines
        header_lines = []
        current_section = None
        camp_data = {}

        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check if line contains itinerary codes (header line)
            if re.search(r"\d+-\d+\s*-\s*\d+\s*Mi\.\s*-\s*[CRSS]+", line) or re.search(
                r"[1-9][A-Z]-[NS]\s*-\s*\d+\s*Mi\.\s*-\s*C", line
            ):
                # Extract itinerary codes from this header line
                codes = self._extract_itinerary_codes_from_line(line)
                if codes:
                    current_section = {
                        "codes": codes,
                        "line_idx": line_idx,
                        "header_line": line,
                    }
                    header_lines.append(current_section)
                    print(f"    Found header with codes: {codes}")

                    # Initialize camp data for these codes
                    for code in codes:
                        if code not in camp_data:
                            camp_data[code] = []

            # If we have a current section, check if this looks like a camp data line
            elif current_section and self._looks_like_camp_data_line(line):
                # Parse camps from this line for the current section
                camps_in_line = self._parse_camp_line_by_position(
                    line, current_section["codes"]
                )

                # Add camps to the appropriate itineraries
                for i, code in enumerate(current_section["codes"]):
                    if i < len(camps_in_line) and camps_in_line[i]:
                        cleaned_camp = self._normalize_camp_name(camps_in_line[i])
                        if cleaned_camp:
                            camp_data[code].append(cleaned_camp)

        if not camp_data:
            print(f"    No camp data found on page {page_num}")
            return None

        # Apply limits but keep duplicates (they will be marked as layovers)
        valid_camp_data = {}
        for code, camps in camp_data.items():
            if camps:
                # Keep all camps including duplicates, but limit total count
                max_camps = self._get_max_camps_for_itinerary(code)
                if len(camps) > max_camps:
                    camps = camps[:max_camps]

                if camps:
                    valid_camp_data[code] = camps
                    print(f"    {code}: {camps}")

        return valid_camp_data if valid_camp_data else None

    def _process_rendezvous_locations(
        self, text: str, trek_type: str, page_num: int
    ) -> Optional[Dict[str, List[str]]]:
        """
        Process camp text from "Itinerary Rendezvous Locations" pages.

        Format:
        Itin Day 1 Day 2 Day 3 Day 4 Day 5 Day 6 Day 7 Day 8 Day 9 Day 10 Day 11 Day 12
        12-1 Camping HQ Toothache Springs URRACA Stockade Ridge MINERS PARK BLACK BEAUBIEN Porcupine Divide CLEAR CREEK Tolby Headwaters Camping HQ

        Returns dict mapping itinerary codes to lists of camp names.
        """
        if not text:
            return None

        lines = text.split("\n")
        camp_data = {}

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Look for lines that start with itinerary codes
            itinerary_match = None
            if trek_type == "12-day":
                itinerary_match = re.match(r"^(12-\d+)\s+(.*)", line)
            elif trek_type == "9-day":
                itinerary_match = re.match(r"^(9-\d+)\s+(.*)", line)
            elif trek_type == "7-day":
                itinerary_match = re.match(r"^(7-\d+)\s+(.*)", line)
            elif trek_type == "cavalcade":
                itinerary_match = re.match(r"^([1-9][A-Z]-[NS])\s+(.*)", line)

            if itinerary_match:
                itinerary_code = itinerary_match.group(1)
                camps_text = itinerary_match.group(2)

                # Check for specific known continuation patterns
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Look for specific camp name continuations
                    if next_line == "WRITINGS":
                        # Replace "INDIAN" with "INDIAN WRITINGS" anywhere it appears
                        camps_text = re.sub(
                            r"INDIAN(?=\s)", "INDIAN WRITINGS", camps_text
                        )
                        i += 1
                    elif next_line.startswith("WRITINGS"):
                        # Handle "INDIAN" + "WRITINGS" = "Indian Writings"
                        camps_text = re.sub(
                            r"INDIAN(?=\s)", "INDIAN WRITINGS", camps_text
                        )
                        remaining = next_line[8:].strip()
                        if remaining:
                            camps_text += " " + remaining
                        i += 1
                    elif next_line == "STATION":
                        # Handle "METCALF" + "STATION" = "Metcalf Station"
                        camps_text = re.sub(
                            r"METCALF(?=\s|$)", "METCALF STATION", camps_text
                        )
                        i += 1

                # Parse the camps from this combined text
                camps = self._parse_rendezvous_camps(camps_text)

                if camps:
                    # Apply limits
                    max_camps = self._get_max_camps_for_itinerary(itinerary_code)
                    if len(camps) > max_camps:
                        camps = camps[:max_camps]

                    camp_data[itinerary_code] = camps
                    print(f"    {itinerary_code}: {camps}")

            i += 1

        return camp_data if camp_data else None

    def _parse_rendezvous_camps(self, camps_text: str) -> List[str]:
        """
        Parse camp names from a rendezvous locations line.

        Input: "Camping HQ Lovers Leap MINERS PARK Lower Bonito Lost Cabins CROOKED Wild Horse Mount Phillips CYPHERS MINE Hunting Lodge CLARKS FORK Camping HQ"
        Output: ["Lovers Leap", "Miners Park", "Lower Bonito", "Lost Cabins", "Crooked", "Wild Horse", "Mount Phillips", "Cyphers Mine", "Hunting Lodge", "Clarks Fork"]
        """
        if not camps_text:
            return []

        # Split into potential camp segments
        segments = camps_text.split()

        camps = []
        i = 0

        while i < len(segments):
            segment = segments[i]

            # Skip "Camping HQ" at start and end
            if (
                segment == "Camping"
                and i + 1 < len(segments)
                and segments[i + 1] == "HQ"
            ):
                i += 2
                continue
            elif segment == "HQ" and i > 0 and segments[i - 1] == "Camping":
                i += 1
                continue

            # Try to form camp names using known patterns
            camp_name, words_consumed = self._extract_next_camp_name(segments, i)

            if camp_name and words_consumed > 0:
                # Normalize the camp name (but keep original casing patterns)
                normalized = camp_name
                # Handle all-caps camp names by converting to title case
                if normalized.isupper() and len(normalized) > 3:
                    normalized = normalized.title()
                camps.append(normalized)
                i += words_consumed
            else:
                # Single word camp - handle all-caps
                camp = segment
                if camp.isupper() and len(camp) > 3:
                    camp = camp.title()
                camps.append(camp)
                i += 1

        return camps

    def _extract_itinerary_codes_from_line(self, line: str) -> List[str]:
        """Extract itinerary codes from a header line."""
        codes = []

        # Pattern for regular itineraries: 12-1, 9-2, 7-3, etc.
        regular_pattern = r"(\d+-\d+)\s*-\s*\d+\s*Mi\.\s*-\s*[CRSS]+"
        matches = re.finditer(regular_pattern, line)
        for match in matches:
            codes.append(match.group(1))

        # Pattern for cavalcade itineraries: 1A-N, 2B-S, etc.
        cavalcade_pattern = r"([1-9][A-Z]-[NS])\s*-\s*\d+\s*Mi\.\s*-\s*C"
        matches = re.finditer(cavalcade_pattern, line)
        for match in matches:
            codes.append(match.group(1))

        return codes

    def _looks_like_camp_data_line(self, line: str) -> bool:
        """
        Check if a line looks like it contains camp data.
        """
        if not line or len(line) < 10:
            return False

        # Skip lines that are clearly headers or other content
        if re.search(r"\d+-\d+\s*-\s*\d+\s*Mi\.", line):
            return False

        # Skip lines that contain non-backcountry locations
        if "camping hq" in line.lower():
            return False

        # Look for camp-like words
        camp_indicators = [
            "canyon",
            "creek",
            "mountain",
            "lake",
            "springs",
            "park",
            "ridge",
            "mine",
            "town",
            "cabin",
            "camp",
            "beard",
            "dean",
            "ponil",
            "abreu",
            "miranda",
            "baldy",
            "beaubien",
            "valley",
            "meadow",
            "peak",
            "divide",
            "pass",
            "ranch",
            "ruins",
            "station",
            "skyline",
            "metcalf",
            "ring",
            "iris",
            "upper",
            "greenwood",
            "herradura",
            "miners",
            "clarks",
            "deer",
            "cimarroncita",
            "ringtail",
            "placer",
            "pueblano",
        ]

        line_lower = line.lower()
        return any(indicator in line_lower for indicator in camp_indicators)

    def _parse_camp_line_by_position(self, line: str, codes: List[str]) -> List[str]:
        """
        Parse a camp line using approximate character positions based on equal column widths.
        This is more reliable than word-based parsing for the PDF column format.
        """
        camps = []

        if not line.strip():
            return [""] * len(codes)

        # Calculate approximate column width
        total_width = len(line)
        column_width = total_width / len(codes)

        for i in range(len(codes)):
            # Calculate start and end positions for this column
            start_pos = int(i * column_width)
            end_pos = int((i + 1) * column_width) if i < len(codes) - 1 else len(line)

            # Extract text from this column
            column_text = line[start_pos:end_pos].strip()

            if column_text:
                # Clean up the column text to get the camp name
                camp_name = self._extract_camp_from_column_text(column_text)
                camps.append(camp_name)
            else:
                camps.append("")

        return camps

    def _parse_camp_sequence(self, words: List[str], expected_count: int) -> List[str]:
        """
        Parse a sequence of words into camp names by identifying boundaries.
        Uses a smarter approach that tries different parsing strategies.
        """
        if not words:
            return []

        # Strategy 1: Try to parse assuming most camps are 2 words
        camps_strategy1 = self._parse_assuming_two_words(words, expected_count)
        if len(camps_strategy1) == expected_count:
            return camps_strategy1

        # Strategy 2: Use the pattern matching approach
        camps = []
        i = 0

        while i < len(words) and len(camps) < expected_count:
            # Try to extract the next camp name starting at position i
            camp_name, words_consumed = self._extract_next_camp_name(words, i)

            if camp_name:
                camps.append(camp_name)
                i += words_consumed
            else:
                # If we can't identify a camp, take one word and move on
                camps.append(words[i])
                i += 1

        return camps

    def _parse_assuming_two_words(
        self, words: List[str], expected_count: int
    ) -> List[str]:
        """
        Parse camp names using intelligent boundary detection.
        """
        camps = []

        # Special case: If we have exactly expected_count * 2 words, assume each camp is 2 words
        if len(words) == expected_count * 2:
            for i in range(0, len(words), 2):
                if i + 1 < len(words):
                    camp_name = f"{words[i]} {words[i + 1]}"
                    camps.append(camp_name)
                else:
                    camps.append(words[i])
            return camps

        # For other cases, use intelligent parsing by trying to identify camp boundaries
        camps = self._parse_with_intelligent_boundaries(words, expected_count)
        return camps

    def _extract_camp_from_column_text(self, column_text: str) -> str:
        """
        Extract a clean camp name from column text.
        """
        if not column_text:
            return ""

        # Split into words and try to form a meaningful camp name
        words = column_text.split()

        if not words:
            return ""

        if len(words) == 1:
            return words[0]

        # Try to form a 2-word camp name using known patterns
        if len(words) >= 2:
            # Check if the first two words form a known camp pattern
            two_word = f"{words[0]} {words[1]}".lower()

            known_two_word_camps = {
                "toothache springs",
                "lovers leap",
                "stockade ridge",
                "miners park",
                "black mountain",
                "wild horse",
                "mount phillips",
                "cyphers mine",
                "hunting lodge",
                "tolby headwaters",
                "clarks fork",
                "lower bonito",
                "lost cabins",
                "crooked creek",
                "lamberts mine",
                "house canyon",
                "indian writings",
                "horse canyon",
                "comanche creek",
                "black horse",
                "head of",
                "new dean",
                "shaefers pass",
                "bear creek",
                "apache springs",
                "porcupine canyon",
                "clear creek",
                "copper park",
                "deer lake",
                "pueblano ruins",
                "upper greenwood",
                "baldy town",
                "baldy skyline",
                "ring place",
                "iris park",
                "metcalf station",
                "dan beard",
            }

            if two_word.lower() in known_two_word_camps:
                return f"{words[0]} {words[1]}"

        # Check for common camp name endings that indicate 2-word names
        if len(words) >= 2:
            second_word_lower = words[1].lower()
            if second_word_lower in [
                "springs",
                "leap",
                "ridge",
                "park",
                "mountain",
                "horse",
                "phillips",
                "mine",
                "lodge",
                "headwaters",
                "fork",
                "bonito",
                "cabins",
                "creek",
                "canyon",
                "writings",
                "dean",
                "pass",
                "greenwood",
                "town",
                "skyline",
                "place",
                "station",
                "beard",
                "ruins",
                "lake",
            ]:
                return f"{words[0]} {words[1]}"

        # Default to first word if no good pattern found
        return words[0]

    def _extract_next_camp_name(
        self, words: List[str], start_idx: int
    ) -> tuple[str, int]:
        """
        Extract the next camp name starting at start_idx.
        Returns (camp_name, words_consumed).
        """
        if start_idx >= len(words):
            return "", 0

        # Known two-word camp names that should be kept together
        two_word_camps = {
            "house canyon",
            "horse canyon",
            "metcalf station",
            "dan beard",
            "ring place",
            "iris park",
            "upper greenwood",
            "baldy town",
            "baldy skyline",
            "miners park",
            "clarks fork",
            "deer lake",
            "pueblano ruins",
            "black mountain",
            "wild horse",
            "lost cabins",
            "crater lake",
            "french henry",
            "flume canyon",
            "heck meadow",
            "toothache springs",
            "indian writings",
            "bear creek",
            "mount phillips",
            "porcupine canyon",
            "clear creek",
            "thunder ridge",
            "crooked creek",
            "hunting lodge",
            "copper park",
            "trail canyon",
            "rich cabins",
            "whistle punk",
            "rimrock park",
            "apache springs",
            "new dean",
            "stockade ridge",
            "sawmill canyon",
            "head of",
            "chase cow",
            "coyote howl",
            "cyphers mine",
            "comanche creek",
            "buck creek",
            "lower bonito",
            "ewells park",
            "shaefers pass",
            "lovers leap",
            "tolby headwaters",
            "lamberts mine",
            "comanche peak",
            "devil's wash",
            "red hills",
            "bear caves",
            "rabbit ear",
            "little costilla",
            "black jacks",
            "touch-me-not creek",
            "dean skyline",
            "fish camp",
            "black horse",
            "agua fria",
            "cimarron river",
            "little twin",
        }

        # Check for three-word camps first (before two-word to avoid partial matches)
        if start_idx + 2 < len(words):
            if (
                words[start_idx].lower() == "head"
                and words[start_idx + 1].lower() == "of"
            ):
                return (
                    f"{words[start_idx]} {words[start_idx + 1]} {words[start_idx + 2]}",
                    3,
                )
            elif (
                words[start_idx].lower() == "black"
                and words[start_idx + 1].lower() == "horse"
                and words[start_idx + 2].lower() == "creek"
            ):
                return (
                    f"{words[start_idx]} {words[start_idx + 1]} {words[start_idx + 2]}",
                    3,
                )
            elif (
                words[start_idx].lower() == "black"
                and words[start_idx + 1].lower() == "horse"
                and words[start_idx + 2].lower() == "mine"
            ):
                return (
                    f"{words[start_idx]} {words[start_idx + 1]} {words[start_idx + 2]}",
                    3,
                )

        # Check for two-word camps
        if start_idx + 1 < len(words):
            two_word = f"{words[start_idx]} {words[start_idx + 1]}".lower()
            if two_word in two_word_camps:
                return f"{words[start_idx]} {words[start_idx + 1]}", 2

        # Check if the next word looks like it could be part of a camp name
        if start_idx + 1 < len(words):
            second_word = words[start_idx + 1].lower()
            if second_word in [
                "canyon",
                "station",
                "place",
                "park",
                "town",
                "skyline",
                "mountain",
                "creek",
                "lake",
                "ruins",
                "springs",
                "ridge",
                "lodge",
                "cabins",
                "mine",
                "fork",
                "meadow",
                "writings",
                "horse",
                "beard",
                "pass",
                "cow",
                "howl",
            ]:
                return f"{words[start_idx]} {words[start_idx + 1]}", 2

        # Handle specific single words that should be expanded to known camp names
        current_word = words[start_idx].lower()
        if current_word == "apache":
            return "Apache Springs", 1
        elif current_word == "crooked":
            return "Crooked Creek", 1

        # Single word camp
        return words[start_idx], 1

    def _extract_best_camp_name(self, words: List[str]) -> str:
        """
        Extract the best camp name from a list of words.
        Handles common multi-word camp name patterns.
        """
        if not words:
            return ""

        if len(words) == 1:
            return words[0]

        # Common two-word patterns
        two_word_patterns = [
            ("House", "Canyon"),
            ("Metcalf", "Station"),
            ("Dan", "Beard"),
            ("Ring", "Place"),
            ("Iris", "Park"),
            ("Upper", "Greenwood"),
            ("Baldy", "Town"),
            ("Baldy", "Skyline"),
            ("Miners", "Park"),
            ("Clarks", "Fork"),
            ("Deer", "Lake"),
            ("Pueblano", "Ruins"),
            ("Black", "Mountain"),
            ("Wild", "Horse"),
            ("Lost", "Cabins"),
            ("Crater", "Lake"),
            ("French", "Henry"),
            ("Head", "of"),
            ("Flume", "Canyon"),
            ("Heck", "Meadow"),
            ("Toothache", "Springs"),
            ("Indian", "Writings"),
            ("Bear", "Creek"),
            ("Mount", "Phillips"),
            ("Porcupine", "Canyon"),
            ("Clear", "Creek"),
            ("Thunder", "Ridge"),
            ("Crooked", "Creek"),
            ("Hunting", "Lodge"),
            ("Copper", "Park"),
            ("Trail", "Canyon"),
            ("Rich", "Cabins"),
            ("Whistle", "Punk"),
            ("Touch-Me-Not", "Creek"),
            ("Rimrock", "Park"),
            ("Apache", "Springs"),
            ("New", "Dean"),
            ("Stockade", "Ridge"),
            ("Sawmill", "Canyon"),
        ]

        # Check for exact two-word matches
        if len(words) >= 2:
            first_two = (words[0], words[1])
            for pattern in two_word_patterns:
                if first_two == pattern:
                    return f"{words[0]} {words[1]}"

        # Check for three-word patterns like "Head of Dean"
        if len(words) >= 3 and words[0] == "Head" and words[1] == "of":
            return f"{words[0]} {words[1]} {words[2]}"

        # Check for compound names that might be run together
        first_word = words[0]
        if len(first_word) > 8:  # Might be two words run together
            # Try to split known compound words
            compound_splits = {
                "HouseCanyon": "House Canyon",
                "MetcalfStation": "Metcalf Station",
                "RingPlace": "Ring Place",
                "IrisPark": "Iris Park",
                "UpperGreenwood": "Upper Greenwood",
                "BaldyTown": "Baldy Town",
                "BaldySkyline": "Baldy Skyline",
                "Minerspark": "Miners Park",
                "ClarksFork": "Clarks Fork",
                "DeerLake": "Deer Lake",
                "PueblanoRuins": "Pueblano Ruins",
            }

            if first_word in compound_splits:
                return compound_splits[first_word]

        # Look for common second words that indicate multi-word names
        if len(words) >= 2:
            second_word = words[1].lower()
            if second_word in [
                "canyon",
                "station",
                "place",
                "park",
                "town",
                "skyline",
                "mountain",
                "creek",
                "lake",
                "ruins",
                "springs",
                "ridge",
                "lodge",
                "cabins",
                "mine",
                "fork",
                "meadow",
                "writings",
                "horse",
                "beard",
            ]:
                return f"{words[0]} {words[1]}"

        # Default to first word if no patterns match
        return words[0]

    def _looks_like_camp_name(self, text: str) -> bool:
        """
        Check if a text string looks like a camp name.
        """
        if not text or len(text) < 4:
            return False

        # Must start with a capital letter (proper noun)
        if not text[0].isupper():
            return False

        # Must contain mostly letters
        letter_count = sum(1 for c in text if c.isalpha())
        if letter_count < len(text) * 0.6:  # At least 60% letters
            return False

        # Common camp name patterns/keywords
        camp_keywords = [
            "camp",
            "canyon",
            "creek",
            "mountain",
            "lake",
            "springs",
            "park",
            "ridge",
            "mine",
            "town",
            "cabin",
            "beard",
            "dean",
            "ponil",
            "abreu",
            "miranda",
            "baldy",
            "beaubien",
            "valley",
            "meadow",
            "peak",
            "divide",
            "pass",
            "ranch",
            "ruins",
            "station",
            "skyline",
            "lodge",
            "cow",
        ]

        text_lower = text.lower()
        contains_keyword = any(keyword in text_lower for keyword in camp_keywords)

        # Accept if it contains a camp keyword or looks like a proper noun
        return contains_keyword or (text[0].isupper() and len(text) >= 5)

    def _normalize_camp_name(self, raw_name: str) -> Optional[str]:
        """
        Normalize camp names to match database entries.
        """
        if not raw_name:
            return None

        # Clean up the name
        name = raw_name.strip()
        if not name:
            return None

        # Remove common suffixes/prefixes that might be artifacts
        name = re.sub(r"^(Day\s*\d+|Camp\s*)", "", name, flags=re.IGNORECASE).strip()

        # Skip very short names that are likely artifacts or text fragments
        if len(name) < 4:
            return None

        # Skip numeric-only names
        if name.isdigit():
            return None

        # Skip common non-camp words that might appear
        skip_words = {
            "the",
            "and",
            "or",
            "at",
            "in",
            "on",
            "of",
            "to",
            "for",
            "with",
            "by",
            "day",
            "night",
            "camp",
            "trail",
            "mile",
            "miles",
            "mi",
            "from",
            "base",
            "are",
            "is",
            "was",
            "were",
            "has",
            "have",
            "had",
            "will",
            "would",
            "could",
        }

        # Skip specific non-backcountry locations
        skip_locations = {"camping hq"}

        if name.lower() in skip_words or name.lower() in skip_locations:
            return None

        # Only accept names that look like proper camp names
        # (contain letters and possibly spaces, numbers, or common camp name patterns)
        if not re.match(r"^[A-Za-z][A-Za-z\s\-\'0-9]*$", name):
            return None

        return name

    def _get_max_camps_for_itinerary(self, itinerary_code: str) -> int:
        """
        Get the maximum number of camps for an itinerary based on its type.
        """
        trek_type = self.identify_trek_type(itinerary_code)

        if trek_type == "12-day":
            return 10
        elif trek_type == "9-day":
            return 7
        elif trek_type == "7-day":
            return 5
        elif trek_type == "cavalcade":
            return 6
        else:
            return 8  # Default fallback

    def import_trek_data(self, pdf_path: str, year: int, dry_run: bool = False) -> int:
        """
        Import trek data from PDF into database.

        Returns number of treks imported.
        """
        if not Path(pdf_path).exists():
            print(f"Error: PDF file not found: {pdf_path}")
            sys.exit(1)

        # Find and extract trek tables
        tables = self.find_trek_tables(pdf_path)
        if not tables:
            print("No trek tables found in PDF")
            return 0

        # Consolidate all trek data
        all_treks = {}
        for page_num, table_data in tables:
            all_treks.update(table_data)

        if not all_treks:
            print("No trek data extracted from tables")
            return 0

        print(f"\nFound {len(all_treks)} treks total")

        # Extract program data from the same PDF
        program_data = self.extract_program_data(pdf_path)
        if program_data:
            print(
                f"Found program data for {sum(len(itins) for itins in program_data.values())} program-itinerary relationships"
            )

        # Extract camp data from "Itineraries at a Glance" sections
        camp_data = self.extract_camp_data(pdf_path)
        if camp_data:
            print(
                f"Found camp data for {sum(len(camps) for camps in camp_data.values())} itinerary-camp relationships"
            )

        if dry_run:
            print("\n=== DRY RUN - No database changes will be made ===")
            for code, data in all_treks.items():
                print(f"{code}: {data}")
            if program_data:
                print("\nProgram Data:")
                for program_name in program_data.keys():
                    itineraries = program_data[program_name]
                    print(f"  {program_name}: {len(itineraries)} itineraries")
            if camp_data:
                print("\nCamp Data:")
                for itinerary_code in camp_data.keys():
                    camps = camp_data[itinerary_code]
                    print(f"  {itinerary_code}: {len(camps)} camps")
            return len(all_treks)

        # Clean up existing data for this year before import
        self._cleanup_existing_data(year)

        # Import into database
        imported_count = self._import_to_database(all_treks, year)

        # Import program data
        if program_data:
            self._import_program_data(program_data, year)

        # Import camp data
        if camp_data:
            self._import_camp_data(camp_data, year)

        return imported_count

    def _cleanup_existing_data(self, year: int) -> int:
        """Remove all existing data for the specified year before import"""
        conn = self.connect_db()
        removed_count = 0

        try:
            cursor = conn.cursor()

            print(f"Removing existing {year} data...")

            # First, get count of existing entries
            cursor.execute("SELECT COUNT(*) FROM itineraries WHERE year = ?", (year,))
            existing_count = cursor.fetchone()[0]

            if existing_count == 0:
                print(f"No existing {year} data found.")
                return 0

            print(f"Found {existing_count} existing {year} entries to remove")

            # Delete from related tables first (foreign key constraints)
            # Delete from itinerary_programs
            cursor.execute(
                """
                DELETE FROM itinerary_programs 
                WHERE itinerary_id IN (
                    SELECT id FROM itineraries WHERE year = ?
                )
            """,
                (year,),
            )
            programs_removed = cursor.rowcount

            # Delete from itinerary_camps
            cursor.execute(
                """
                DELETE FROM itinerary_camps 
                WHERE itinerary_id IN (
                    SELECT id FROM itineraries WHERE year = ?
                )
            """,
                (year,),
            )
            camps_removed = cursor.rowcount

            # Finally delete from itineraries
            cursor.execute("DELETE FROM itineraries WHERE year = ?", (year,))
            removed_count = cursor.rowcount

            conn.commit()

            print(
                f"Removed {removed_count} itineraries, {programs_removed} program associations, {camps_removed} camp associations for year {year}"
            )

        except sqlite3.Error as e:
            print(f"Error cleaning up existing data: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

        return removed_count

    def _import_to_database(self, trek_data: Dict[str, Dict], year: int) -> int:
        """Import trek data into the database"""
        conn = self.connect_db()
        imported_count = 0

        try:
            cursor = conn.cursor()

            for trek_code, data in trek_data.items():
                try:
                    # Check if itinerary already exists for this year
                    cursor.execute(
                        "SELECT id FROM itineraries WHERE itinerary_code = ? AND year = ?",
                        (trek_code, year),
                    )
                    existing = cursor.fetchone()

                    if existing:
                        print(f"Updating existing trek: {trek_code} (year {year})")
                        self._update_itinerary(cursor, existing["id"], data)
                    else:
                        # Check if there's an entry with the same code but different year
                        cursor.execute(
                            "SELECT id, year FROM itineraries WHERE itinerary_code = ?",
                            (trek_code,),
                        )
                        existing_other_year = cursor.fetchone()

                        if existing_other_year:
                            print(
                                f"Found {trek_code} for year {existing_other_year['year']}, inserting for year {year}"
                            )
                        else:
                            print(f"Inserting new trek: {trek_code} (year {year})")

                        self._insert_itinerary(cursor, trek_code, data, year)

                    imported_count += 1

                except sqlite3.Error as e:
                    print(f"Error importing {trek_code} (year {year}): {e}")
                    continue

            conn.commit()
            print(f"\nSuccessfully imported/updated {imported_count} treks")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            conn.rollback()
        finally:
            conn.close()

        return imported_count

    def _insert_itinerary(
        self, cursor: sqlite3.Cursor, trek_code: str, data: Dict, year: int
    ):
        """Insert a new itinerary record"""
        cursor.execute(
            """
            INSERT INTO itineraries (
                itinerary_code, trek_type, difficulty, distance, 
                trail_camps, staffed_camps, dry_camps, year, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                trek_code,
                data.get("trek_type", "12-day"),
                data.get("difficulty"),
                data.get("distance"),
                data.get("trail_camps"),
                data.get("staffed_camps"),
                data.get("dry_camps"),
                year,
            ),
        )

    def _update_itinerary(self, cursor: sqlite3.Cursor, itinerary_id: int, data: Dict):
        """Update an existing itinerary record"""
        cursor.execute(
            """
            UPDATE itineraries SET
                difficulty = COALESCE(?, difficulty),
                distance = COALESCE(?, distance),
                trail_camps = COALESCE(?, trail_camps),
                staffed_camps = COALESCE(?, staffed_camps),
                dry_camps = COALESCE(?, dry_camps),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (
                data.get("difficulty"),
                data.get("distance"),
                data.get("trail_camps"),
                data.get("staffed_camps"),
                data.get("dry_camps"),
                itinerary_id,
            ),
        )

    def _import_program_data(
        self, program_data: Dict[str, List[str]], year: int
    ) -> int:
        """
        Import program data into the itinerary_programs table.

        Returns number of program-itinerary relationships imported.
        """
        conn = self.connect_db()
        imported_count = 0

        try:
            cursor = conn.cursor()

            print(f"\nImporting program data for year {year}")

            # First, get all program IDs and names from database
            cursor.execute("SELECT id, name, code FROM programs")
            db_programs = {row[1]: row[0] for row in cursor.fetchall()}  # name -> id

            # Get all itinerary IDs for this year
            cursor.execute(
                "SELECT id, itinerary_code, trek_type FROM itineraries WHERE year = ?",
                (year,),
            )
            db_itineraries = {
                row[1]: (row[0], row[2]) for row in cursor.fetchall()
            }  # code -> (id, trek_type)

            programs_found = 0
            programs_not_found = []

            for program_name, itinerary_codes in program_data.items():
                program_id = None

                # Try to find program by exact name match
                if program_name in db_programs:
                    program_id = db_programs[program_name]
                    programs_found += 1
                else:
                    # Try fuzzy matching for common variations
                    program_id = self._find_program_by_fuzzy_match(
                        program_name, db_programs
                    )
                    if program_id:
                        programs_found += 1
                    else:
                        programs_not_found.append(program_name)
                        continue

                # Import itinerary-program relationships
                for itinerary_code in itinerary_codes:
                    if itinerary_code in db_itineraries:
                        itinerary_id, trek_type = db_itineraries[itinerary_code]

                        try:
                            # Insert or update itinerary_programs relationship
                            cursor.execute(
                                """
                                INSERT OR REPLACE INTO itinerary_programs 
                                (itinerary_id, program_id, trek_type, is_available, year)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                                (itinerary_id, program_id, trek_type, True, year),
                            )

                            imported_count += 1

                        except sqlite3.Error as e:
                            print(
                                f"Error importing program relationship {program_name} -> {itinerary_code}: {e}"
                            )
                            continue

            conn.commit()

            print(
                f"Successfully imported {imported_count} program-itinerary relationships"
            )
            print(f"Programs found in database: {programs_found}")

            if programs_not_found:
                print(f"Programs not found in database ({len(programs_not_found)}):")
                for prog in programs_not_found[:10]:  # Show first 10
                    print(f"  - {prog}")
                if len(programs_not_found) > 10:
                    print(f"  ... and {len(programs_not_found) - 10} more")

        except sqlite3.Error as e:
            print(f"Database error during program import: {e}")
            conn.rollback()
        finally:
            conn.close()

        return imported_count

    def _find_program_by_fuzzy_match(
        self, program_name: str, db_programs: Dict[str, int]
    ) -> Optional[int]:
        """
        Try to find a program by fuzzy name matching.
        """
        program_lower = program_name.lower()

        # Try partial matches
        for db_name, program_id in db_programs.items():
            db_name_lower = db_name.lower()

            # Check if the extracted program name is contained in a database program name
            if program_lower in db_name_lower or db_name_lower in program_lower:
                return program_id

            # Check for key word matches
            program_words = set(program_lower.split())
            db_words = set(db_name_lower.split())

            # If there's significant word overlap, consider it a match
            if len(program_words & db_words) >= min(2, len(program_words)):
                return program_id

        return None

    def _import_camp_data(self, camp_data: Dict[str, List[str]], year: int) -> int:
        """
        Import camp data into the itinerary_camps table.

        Returns number of camp-itinerary relationships imported.
        """
        conn = self.connect_db()
        imported_count = 0

        try:
            cursor = conn.cursor()

            print(f"\nImporting camp data for year {year}")

            # Get all camp IDs and names from database
            cursor.execute("SELECT id, name FROM camps")
            db_camps = {row[1]: row[0] for row in cursor.fetchall()}  # name -> id

            # Get all itinerary IDs for this year
            cursor.execute(
                "SELECT id, itinerary_code FROM itineraries WHERE year = ?", (year,)
            )
            db_itineraries = {row[1]: row[0] for row in cursor.fetchall()}  # code -> id

            camps_found = 0
            camps_not_found = []
            itinerary_layover_counts = {}  # Track layover count per itinerary

            for itinerary_code, camp_names in camp_data.items():
                if itinerary_code not in db_itineraries:
                    print(f"Warning: Itinerary {itinerary_code} not found in database")
                    continue

                itinerary_id = db_itineraries[itinerary_code]

                # Track camps visited in this itinerary to identify layovers
                visited_camps = set()
                layover_count = 0

                # Import each camp for this itinerary
                for day_number, camp_name in enumerate(
                    camp_names, 2
                ):  # Start from day 2 (day 1 is base camp)
                    camp_id = None

                    # Try to find camp by exact name match
                    if camp_name in db_camps:
                        camp_id = db_camps[camp_name]
                        camps_found += 1
                    else:
                        # Try fuzzy matching for common variations
                        camp_id = self._find_camp_by_fuzzy_match(camp_name, db_camps)
                        if camp_id:
                            camps_found += 1
                        else:
                            camps_not_found.append(camp_name)
                            continue

                    # Determine if this is a layover (revisiting a camp)
                    is_layover = camp_id in visited_camps
                    if is_layover:
                        layover_count += 1
                    visited_camps.add(camp_id)

                    try:
                        # Insert or update itinerary_camps relationship
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO itinerary_camps 
                            (itinerary_id, day_number, camp_id, is_layover, year)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (itinerary_id, day_number, camp_id, is_layover, year),
                        )

                        imported_count += 1

                        # Log layovers for verification
                        if is_layover:
                            print(
                                f"    Layover detected: {itinerary_code} day {day_number} at {camp_name}"
                            )

                    except sqlite3.Error as e:
                        print(
                            f"Error importing camp relationship {camp_name} -> {itinerary_code}: {e}"
                        )
                        continue
                
                # Store layover count for this itinerary
                if layover_count > 0:
                    itinerary_layover_counts[itinerary_id] = layover_count

            # Update itineraries table with layover counts
            for itinerary_id, layover_count in itinerary_layover_counts.items():
                try:
                    cursor.execute(
                        """
                        UPDATE itineraries 
                        SET layovers = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                        """,
                        (layover_count, itinerary_id)
                    )
                except sqlite3.Error as e:
                    print(f"Error updating layover count for itinerary {itinerary_id}: {e}")

            conn.commit()

            print(
                f"Successfully imported {imported_count} camp-itinerary relationships"
            )
            print(f"Camps found in database: {camps_found}")
            print(f"Itineraries with layovers: {len(itinerary_layover_counts)}")

            if camps_not_found:
                # Remove duplicates and show unique camp names not found
                unique_not_found = list(set(camps_not_found))
                print(f"Camps not found in database ({len(unique_not_found)}):")
                for camp in unique_not_found[:15]:  # Show first 15
                    print(f"  - {camp}")
                if len(unique_not_found) > 15:
                    print(f"  ... and {len(unique_not_found) - 15} more")

        except sqlite3.Error as e:
            print(f"Database error during camp import: {e}")
            conn.rollback()
        finally:
            conn.close()

        return imported_count

    def _find_camp_by_fuzzy_match(
        self, camp_name: str, db_camps: Dict[str, int]
    ) -> Optional[int]:
        """
        Try to find a camp by fuzzy name matching.
        """
        camp_lower = camp_name.lower()

        # Try partial matches
        for db_name, camp_id in db_camps.items():
            db_name_lower = db_name.lower()

            # Check if the extracted camp name is contained in a database camp name
            if camp_lower in db_name_lower or db_name_lower in camp_lower:
                return camp_id

            # Check for key word matches (for compound names)
            camp_words = set(camp_lower.split())
            db_words = set(db_name_lower.split())

            # If there's significant word overlap, consider it a match
            if len(camp_words & db_words) >= min(2, len(camp_words)):
                return camp_id

        return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Import Philmont trek data from PDF guidebooks"
    )
    parser.add_argument("--pdf", required=True, help="Path to the PDF file to import")
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year for the trek data (e.g., 2024, 2025)",
    )
    parser.add_argument(
        "--database",
        default="philmont_selection.db",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without making changes",
    )

    args = parser.parse_args()

    importer = PhilmontTrekImporter(args.database)

    print(f"Importing trek data from {args.pdf} for year {args.year}")
    if args.dry_run:
        print("(DRY RUN MODE)")

    count = importer.import_trek_data(args.pdf, args.year, args.dry_run)

    if count > 0:
        print(f"\nImport completed: {count} treks processed")
    else:
        print("\nNo treks were imported")


if __name__ == "__main__":
    main()
