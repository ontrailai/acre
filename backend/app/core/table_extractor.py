"""
Enhanced Table Extraction System - Conservative Version

This module provides specialized extraction for tables commonly found in
real estate documents including rent schedules, CAM allocations, and tenant rosters.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import pandas as pd
from dataclasses import dataclass
import json
from app.utils.logger import logger


@dataclass
class TableData:
    """Represents extracted table data"""
    table_type: str
    headers: List[str]
    rows: List[List[Any]]
    metadata: Dict[str, Any]
    confidence: float
    source_format: str  # 'structured', 'semi_structured', 'unstructured'
    

class TableTypeDetector:
    """Detects the type of table based on headers and content"""
    
    def __init__(self):
        self.table_patterns = {
            "rent_schedule": {
                "headers": ["year", "month", "rent", "base rent", "annual", "psf"],
                "content": ["$", "per", "square foot", "escalation"]
            },
            "cam_allocation": {
                "headers": ["expense", "category", "allocation", "pro rata", "share"],
                "content": ["maintenance", "insurance", "utilities", "management"]
            },
            "tenant_roster": {
                "headers": ["tenant", "suite", "square feet", "expiration", "rental rate"],
                "content": ["lease", "term", "options"]
            },
            "expense_breakdown": {
                "headers": ["item", "cost", "frequency", "responsibility"],
                "content": ["landlord", "tenant", "monthly", "annual"]
            },
            "option_schedule": {
                "headers": ["option", "term", "notice", "exercise", "deadline"],
                "content": ["renewal", "extension", "days", "months"]
            }
        }
        
    def detect_table_type(self, headers: List[str], sample_content: str) -> Tuple[str, float]:
        """Detect table type based on headers and content"""
        headers_lower = [h.lower() for h in headers]
        content_lower = sample_content.lower()
        
        best_match = "unknown"
        best_score = 0.0
        
        for table_type, patterns in self.table_patterns.items():
            score = 0.0
            
            # Check header matches
            header_matches = sum(1 for h in patterns["headers"] if any(h in header for header in headers_lower))
            header_score = header_matches / len(patterns["headers"]) if patterns["headers"] else 0
            
            # Check content matches
            content_matches = sum(1 for c in patterns["content"] if c in content_lower)
            content_score = content_matches / len(patterns["content"]) if patterns["content"] else 0
            
            # Combined score
            total_score = (header_score * 0.6) + (content_score * 0.4)
            
            if total_score > best_score:
                best_score = total_score
                best_match = table_type
                
        # Require higher confidence threshold
        confidence = best_score if best_score > 0.5 else 0.2
        
        return best_match, confidence


class TableExtractor:
    """
    Conservative table extraction that only extracts clear, well-formatted tables
    """
    
    def __init__(self):
        self.type_detector = TableTypeDetector()
        self.min_table_rows = 3  # Increased from 2
        self.min_table_cols = 2
        self.max_tables_per_doc = 10  # Reasonable limit
        
    def extract_tables_from_text(self, text: str) -> List[TableData]:
        """Extract only clear, well-formatted tables from text"""
        tables = []
        
        # Only try extraction methods that have clear table indicators
        tables.extend(self._extract_markdown_tables(text))
        tables.extend(self._extract_clear_delimiter_tables(text))
        
        # Strict deduplication
        tables = self._deduplicate_tables(tables)
        
        # Validate and filter tables
        valid_tables = []
        for table in tables:
            if self._validate_table(table):
                self._enhance_table_data(table)
                valid_tables.append(table)
                
        # Limit total tables
        if len(valid_tables) > self.max_tables_per_doc:
            logger.warning(f"Found {len(valid_tables)} tables, limiting to {self.max_tables_per_doc}")
            # Sort by confidence and take top N
            valid_tables.sort(key=lambda t: t.confidence, reverse=True)
            valid_tables = valid_tables[:self.max_tables_per_doc]
            
        return valid_tables
        
    def _extract_markdown_tables(self, text: str) -> List[TableData]:
        """Extract only clear markdown-style tables"""
        tables = []
        
        # Strict pattern for markdown tables - must have header separator
        table_pattern = r'(\|[^\n]+\|\n\|[\s\-:\|]+\|\n(?:\|[^\n]+\|\n)+)'
        
        for match in re.finditer(table_pattern, text, re.MULTILINE):
            table_text = match.group(1)
            table_data = self._parse_markdown_table(table_text)
            if table_data and table_data.confidence > 0.5:
                tables.append(table_data)
                
        return tables
        
    def _extract_clear_delimiter_tables(self, text: str) -> List[TableData]:
        """Extract only tables with very clear delimiters"""
        tables = []
        
        # Only check for clear delimiters
        delimiters = ['\t', '|']  # Only tab and pipe
        
        lines = text.split('\n')
        
        for delimiter in delimiters:
            # Group consecutive lines with same delimiter count
            groups = []
            current_group = []
            prev_delimiter_count = -1
            
            for line in lines:
                delimiter_count = line.count(delimiter)
                
                if delimiter_count >= self.min_table_cols - 1:
                    if prev_delimiter_count == -1 or delimiter_count == prev_delimiter_count:
                        current_group.append(line)
                        prev_delimiter_count = delimiter_count
                    else:
                        # Delimiter count changed - new table
                        if len(current_group) >= self.min_table_rows:
                            groups.append(current_group)
                        current_group = [line]
                        prev_delimiter_count = delimiter_count
                else:
                    # No delimiters - end current group
                    if len(current_group) >= self.min_table_rows:
                        groups.append(current_group)
                    current_group = []
                    prev_delimiter_count = -1
                    
            # Don't forget last group
            if len(current_group) >= self.min_table_rows:
                groups.append(current_group)
                
            # Process each group
            for group in groups:
                table_data = self._process_delimiter_table(group, delimiter)
                if table_data and table_data.confidence > 0.5:
                    tables.append(table_data)
                    
        return tables
        
    def _parse_markdown_table(self, table_text: str) -> Optional[TableData]:
        """Parse a markdown-style table"""
        lines = table_text.strip().split('\n')
        if len(lines) < 3:  # Header + separator + at least one row
            return None
            
        # Extract headers
        headers = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
        
        # Verify separator line
        separator = lines[1]
        if not re.match(r'^\|[\s\-:\|]+\|$', separator):
            return None
            
        # Extract rows (skip separator line)
        rows = []
        for line in lines[2:]:
            row = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(row) == len(headers):
                rows.append(row)
                
        if not rows:
            return None
            
        # Create sample content for type detection
        sample_content = ' '.join([' '.join(row) for row in rows[:3]])
        table_type, confidence = self.type_detector.detect_table_type(headers, sample_content)
        
        return TableData(
            table_type=table_type,
            headers=headers,
            rows=rows,
            metadata={"format": "markdown"},
            confidence=confidence,
            source_format="structured"
        )
        
    def _process_delimiter_table(self, lines: List[str], delimiter: str) -> Optional[TableData]:
        """Process a table with specific delimiter"""
        if not lines:
            return None
            
        # All lines must have same number of delimiters
        delimiter_counts = [line.count(delimiter) for line in lines]
        if len(set(delimiter_counts)) > 1:
            return None
            
        headers = [cell.strip() for cell in lines[0].split(delimiter)]
        
        rows = []
        for line in lines[1:]:
            row = [cell.strip() for cell in line.split(delimiter)]
            if len(row) == len(headers):
                rows.append(row)
                
        if not rows:
            return None
            
        sample_content = ' '.join([' '.join(row) for row in rows[:3]])
        table_type, confidence = self.type_detector.detect_table_type(headers, sample_content)
        
        # Boost confidence for clear delimiters
        if delimiter in ['|', '\t']:
            confidence = min(confidence * 1.2, 1.0)
            
        return TableData(
            table_type=table_type,
            headers=headers,
            rows=rows,
            metadata={"format": f"{delimiter}_delimited"},
            confidence=confidence,
            source_format="structured"
        )
        
    def _validate_table(self, table: TableData) -> bool:
        """Validate that this is actually a table"""
        # Must have reasonable number of rows and columns
        if len(table.rows) < 2 or len(table.headers) < 2:
            return False
            
        # Headers should be distinct
        unique_headers = set(table.headers)
        if len(unique_headers) < len(table.headers) * 0.8:
            return False
            
        # At least some cells should have content
        non_empty_cells = 0
        total_cells = len(table.rows) * len(table.headers)
        
        for row in table.rows:
            for cell in row:
                if cell and str(cell).strip():
                    non_empty_cells += 1
                    
        if non_empty_cells < total_cells * 0.3:
            return False
            
        # For numeric tables, should have some numbers
        if table.table_type in ["rent_schedule", "cam_allocation", "expense_breakdown"]:
            has_numbers = False
            for row in table.rows:
                for cell in row:
                    if re.search(r'\d+', str(cell)):
                        has_numbers = True
                        break
                if has_numbers:
                    break
            if not has_numbers:
                return False
                
        return True
        
    def _deduplicate_tables(self, tables: List[TableData]) -> List[TableData]:
        """Remove duplicate tables"""
        unique_tables = []
        seen_content = set()
        
        for table in tables:
            # Create a content signature
            signature = (
                tuple(table.headers),
                tuple(tuple(row) for row in table.rows)  # All rows
            )
            
            if signature not in seen_content:
                seen_content.add(signature)
                unique_tables.append(table)
            else:
                logger.debug("Skipping duplicate table")
                
        return unique_tables
        
    def _enhance_table_data(self, table: TableData):
        """Enhance table data with additional processing"""
        # Add specialized processing based on table type
        if table.table_type == "rent_schedule":
            self._enhance_rent_schedule(table)
        elif table.table_type == "cam_allocation":
            self._enhance_cam_allocation(table)
        elif table.table_type == "tenant_roster":
            self._enhance_tenant_roster(table)
            
    def _enhance_rent_schedule(self, table: TableData):
        """Enhance rent schedule with calculations"""
        # Add total rent calculation
        total_rent = 0
        count = 0
        
        for row in table.rows:
            for i, header in enumerate(table.headers):
                if 'rent' in header.lower() and i < len(row):
                    # Try to extract numeric value
                    value = self._extract_numeric(row[i])
                    if value and value > 0:
                        total_rent += value
                        count += 1
                        
        table.metadata["total_rent"] = total_rent
        table.metadata["average_rent"] = total_rent / count if count > 0 else 0
        
    def _enhance_cam_allocation(self, table: TableData):
        """Enhance CAM allocation with totals"""
        # Calculate total allocations
        total_allocation = 0
        
        for row in table.rows:
            for i, header in enumerate(table.headers):
                if 'allocation' in header.lower() or '%' in header and i < len(row):
                    value = self._extract_percentage(row[i])
                    if value:
                        total_allocation += value
                        
        table.metadata["total_allocation"] = total_allocation
        table.metadata["fully_allocated"] = abs(total_allocation - 100) < 0.01
        
    def _enhance_tenant_roster(self, table: TableData):
        """Enhance tenant roster with occupancy stats"""
        # Calculate occupancy metrics
        total_sf = 0
        occupied_sf = 0
        count = 0
        
        for row in table.rows:
            for i, header in enumerate(table.headers):
                if ('square' in header.lower() or 'sf' in header.lower() or 'sq' in header.lower()) and i < len(row):
                    value = self._extract_numeric(row[i])
                    if value and value > 0:
                        total_sf += value
                        count += 1
                        if self._is_occupied(row):
                            occupied_sf += value
                            
        table.metadata["total_square_feet"] = total_sf
        table.metadata["occupied_square_feet"] = occupied_sf
        table.metadata["occupancy_rate"] = (occupied_sf / total_sf * 100) if total_sf > 0 else 0
        
    def _extract_numeric(self, value: str) -> Optional[float]:
        """Extract numeric value from string"""
        if not value:
            return None
            
        # Remove common non-numeric characters
        cleaned = re.sub(r'[^\d.,\-]', '', str(value))
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
            
    def _extract_percentage(self, value: str) -> Optional[float]:
        """Extract percentage value from string"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', str(value))
        if match:
            return float(match.group(1))
        
        # Try without % sign
        try:
            num = float(str(value).strip())
            if 0 <= num <= 100:
                return num
        except ValueError:
            pass
            
        return None
        
    def _is_occupied(self, row: List[str]) -> bool:
        """Check if a tenant roster row represents an occupied space"""
        if row:
            tenant_info = ' '.join(str(cell) for cell in row).lower()
            vacant_keywords = ['vacant', 'available', 'empty', 'tbd', 'n/a']
            return not any(keyword in tenant_info for keyword in vacant_keywords)
        return False
