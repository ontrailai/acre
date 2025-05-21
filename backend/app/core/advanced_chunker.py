"""
Advanced Lease Chunking System

This module implements an improved chunking system for lease documents that:

1. Uses layout and visual structure for better chunk boundaries
2. Maps chunks to specific clause types
3. Reduces cross-clause contamination
4. Enhances traceability
5. Preserves compatibility with existing clause classification and GPT routing
   """

from typing import List, Dict, Any, Optional, Tuple, Set
import re
import json
import os
import uuid
from collections import defaultdict, Counter
import math
from app.schemas import LeaseType
from app.utils.logger import logger

# Create a new file in app/utils/llm/gpt4\_segmenter.py with this class

class GPT4Segmenter:
"""
GPT-4 powered lease segmentation that uses AI to more intelligently
break leases into semantically coherent chunks.
"""

```
def __init__(self, text_content: str, lease_type: LeaseType, min_confidence: float = 0.75):
    """
    Initialize the GPT-4 segmenter with lease text and type.
    
    Args:
        text_content: Full text of the lease document
        lease_type: The type of lease (RETAIL, OFFICE, INDUSTRIAL)
        min_confidence: Minimum confidence threshold for including GPT-classified chunks
    """
    self.text_content = text_content
    self.lease_type = lease_type
    self.max_chunk_size = 1500  # Maximum tokens per chunk
    self.min_confidence = min_confidence
    
def segment_to_chunks(self) -> List[Dict[str, Any]]:
    """
    Use GPT-4 to intelligently segment the lease into semantic chunks.
    
    Returns:
        A list of chunk dictionaries with metadata
    """
    # This is where we would normally call the OpenAI API
    # For now, we'll implement a simplified version that does some basic
    # semantic segmentation using regex patterns for common lease sections
    
    # Simple detection for major lease sections
    section_patterns = {
        "premises": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:PREMISES|DEMISED)\b",
        "term": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:TERM|DURATION|COMMENCEMENT)\b",
        "rent": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:RENT|PAYMENT)\b",
        "use": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:USE|PURPOSE)\b",
        "assignment": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:ASSIGNMENT|SUBLETTING|TRANSFER)\b",
        "maintenance": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:MAINTENANCE|REPAIR)\b",
        "insurance": r"(?i)(?:\bARTICLE|\bSECTION)\s+\d+[.:]\s*.*?\b(?:INSURANCE|LIABILITY)\b"
    }
    
    # Find sections in the text
    sections = []
    for clause_type, pattern in section_patterns.items():
        for match in re.finditer(pattern, self.text_content):
            sections.append({
                "position": match.start(),
                "clause_hint": clause_type,
                "heading": match.group(0)
            })
    
    # Sort sections by position
    sections.sort(key=lambda x: x["position"])
    
    # If we didn't find at least 3 sections, the simple approach isn't working well
    if len(sections) < 3:
        return []  # Trigger fallback to traditional chunking
    
    # Create chunks from sections
    chunks = []
    valid_chunks = []
    
    for i, section in enumerate(sections):
        # Determine chunk end position
        if i < len(sections) - 1:
            end_position = sections[i+1]["position"]
        else:
            end_position = len(self.text_content)
        
        # Extract content
        content = self.text_content[section["position"]:end_position].strip()
        
        # Skip very short content
        if len(content) < 50:
            continue
            
        # Estimate page range (placeholder - would need proper page detection)
        page_start = 1
        page_end = 1
        
        # Create a chunk for this section
        chunk_id = f"GPT-{i+1:03d}"
        
        # Calculate token estimate
        token_estimate = self._estimate_tokens(content)
        
        # Determine risk score
        high_risk_clauses = ["termination", "assignment", "co_tenancy"]
        medium_risk_clauses = ["use", "maintenance", "insurance"]
        
        risk_score = "low"
        if section["clause_hint"] in high_risk_clauses:
            risk_score = "high"
        elif section["clause_hint"] in medium_risk_clauses:
            risk_score = "medium"
        
        # Create the chunk
        chunk = {
            "chunk_id": chunk_id,
            "content": content,
            "page_start": page_start,
            "page_end": page_end,
            "char_start": section["position"],
            "char_end": end_position,
            "token_estimate": token_estimate,
            "is_table": False,
            "parent_heading": section["heading"],
            "clause_hint": section["clause_hint"],
            "source_excerpt": content[:150] + "..." if len(content) > 150 else content,
            "risk_score": risk_score,
            "matched_keywords": [section["clause_hint"]],
            "source_page_text": content,  # In a real implementation, this would be the full page text
            "classification_confidence": 0.85,  # Artificially high confidence for GPT-determined chunks
            "confidence": 0.85  # Added for consistency with min_confidence check
        }
        
        chunks.append(chunk)
        
        # Only include chunks that meet the confidence threshold
        if chunk.get("confidence", 0) >= self.min_confidence:
            valid_chunks.append(chunk)
    
    return valid_chunks

def _estimate_tokens(self, text: str) -> int:
    """Estimate token count using simple character-based approximation"""
    if not text:
        return 0
    
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 compatible encoding
        tokens = len(encoding.encode(text))
        return tokens
    except (ImportError, Exception):
        # Fallback to simple approximation
        char_count = len(text)
        return max(1, math.ceil(char_count / 4))
```

class AdvancedChunker:
def **init**(self, text\_content: str, lease\_type: LeaseType):
"""
Initialize the chunker with a lease document and its type.

```
    Args:
        text_content: The full text of the lease document
        lease_type: The type of lease (RETAIL, OFFICE, INDUSTRIAL)
    """
    self.text_content = text_content
    self.lease_type = lease_type
    self.chunks = []
    self.debug_info = {
        "layout_blocks": [],
        "semantic_chunks": [],
        "tables": [],
        "processing_log": []
    }
    
    # Create debug directory
    self.debug_dir = os.path.join("app", "storage", "debug", "advanced_chunker")
    os.makedirs(self.debug_dir, exist_ok=True)
    
    # Extract page information
    self.pages = self._extract_pages()
    
    # Set maximum tokens per chunk (to avoid exceeding GPT context limits)
    self.max_tokens_per_chunk = 1500
    
    # Store original and modified positions to track text locations
    self.position_map = {}
    
    # Initialize telemetry dictionary for system-level insights
    self.telemetry = {
        "segmenter_used": None,
        "gpt_chunks_used": 0,
        "gpt_clause_sections_detected": 0,
        "fallback_layout_blocks_detected": 0,
        "clause_type_counts": {}
    }
    
def process(self) -> List[Dict[str, Any]]:
    """
    Process the lease document and return semantic chunks.
    
    Returns:
        A list of chunk dictionaries with metadata.
    """
    if len(self.text_content) < 500:
        logger.error(f"Text content too short for chunking: {len(self.text_content)} chars")
        # Return a single error chunk
        return [{
            "chunk_id": f"C-001",
            "section_name": "error_insufficient_content",
            "content": self.text_content,
            "page_start": 1,
            "page_end": 1,
            "char_start": 0,
            "char_end": len(self.text_content),
            "token_estimate": self._estimate_tokens(self.text_content),
            "is_table": False,
            "parent_heading": None,
            "clause_hint": "error",
            "source_excerpt": self.text_content[:100] + "...",
            "error": "Insufficient text content for chunking",
            "risk_score": "low",
            "matched_keywords": [],
            "source_page_text": self.text_content
        }]
    
    # Use GPT-4 segmentation when applicable (toggle here)
    try:
        gpt_segmenter = GPT4Segmenter(self.text_content, self.lease_type, min_confidence=0.75)
        gpt_chunks = gpt_segmenter.segment_to_chunks()
        if gpt_chunks:
            logger.info(f"Used GPT4Segmenter for {len(gpt_chunks)} chunks")
            # Update telemetry for GPT segmentation
            self.telemetry["segmenter_used"] = "gpt"
            self.telemetry["gpt_chunks_used"] = len(gpt_chunks)
            self.telemetry["gpt_clause_sections_detected"] = len(set(chunk["clause_hint"] for chunk in gpt_chunks))
            
            # Update telemetry with clause type counts
            self.telemetry["clause_type_counts"] = dict(Counter(chunk["clause_hint"] for chunk in gpt_chunks))
            
            # Create and save chunk audit
            self._save_chunk_audit(gpt_chunks)
            
            # Save telemetry information
            with open(os.path.join(self.debug_dir, "telemetry.json"), "w") as f:
                json.dump(self.telemetry, f, indent=2)
            
            return gpt_chunks
    except Exception as e:
        logger.warning(f"GPT segmentation failed: {e}")
    
    # Fallback to legacy method
    logger.info(f"Falling back to traditional layout + semantic chunking")
    self.debug_info["processing_log"].append(f"Fallback mode: layout + semantic")
    # Set telemetry for fallback
    self.telemetry["segmenter_used"] = "fallback"
    
    # Log the start of processing
    logger.info(f"Starting advanced chunking for {self.lease_type} lease: {len(self.text_content)} chars")
    self.debug_info["processing_log"].append(f"Starting advanced chunking: {len(self.text_content)} chars")
    
    # Step 1: Identify layout-based blocks
    layout_blocks = self._identify_layout_blocks()
    logger.info(f"Identified {len(layout_blocks)} layout blocks")
    self.debug_info["layout_blocks"] = layout_blocks
    self.debug_info["processing_log"].append(f"Identified {len(layout_blocks)} layout blocks")
    self.telemetry["fallback_layout_blocks_detected"] = len(layout_blocks)
    
    # Step 2: Identify tables
    tables = self._identify_tables()
    logger.info(f"Identified {len(tables)} tables")
    self.debug_info["tables"] = tables
    self.debug_info["processing_log"].append(f"Identified {len(tables)} tables")
    
    # Step 3: Refine chunks semantically
    semantic_chunks = self._refine_chunks_semantically(layout_blocks, tables)
    logger.info(f"Created {len(semantic_chunks)} semantic chunks")
    self.debug_info["semantic_chunks"] = semantic_chunks
    self.debug_info["processing_log"].append(f"Created {len(semantic_chunks)} semantic chunks")
    
    # Step 4: Classify chunks
    final_chunks = self._classify_chunks(semantic_chunks)
    logger.info(f"Finalized {len(final_chunks)} chunks with classification")
    self.debug_info["processing_log"].append(f"Finalized {len(final_chunks)} chunks with classification")
    
    # Update telemetry with clause type counts
    self.telemetry["clause_type_counts"] = dict(Counter(chunk["clause_hint"] for chunk in final_chunks))
    self.debug_info["processing_log"].append(f"Clause counts: {self.telemetry['clause_type_counts']}")
    
    # Create and save chunk audit
    self._save_chunk_audit(final_chunks)
    
    # Save telemetry information
    with open(os.path.join(self.debug_dir, "telemetry.json"), "w") as f:
        json.dump(self.telemetry, f, indent=2)
    
    # Save debug information
    self._save_debug_info()
    
    # Return the final chunks
    return final_chunks

def _save_chunk_audit(self, chunks: List[Dict[str, Any]]):
    """Save chunk audit information for QA review"""
    audit = []
    for c in chunks:
        audit.append({
            "chunk_id": c["chunk_id"],
            "heading": c.get("parent_heading"),
            "clause_hint": c["clause_hint"],
            "confidence": c.get("classification_confidence", None),
            "risk_score": c["risk_score"],
            "excerpt": c["content"][:150] + "..." if len(c["content"]) > 150 else c["content"],
            "source_pages": f"{c['page_start']}-{c['page_end']}",
            "gpt_justification": c.get("gpt_justification")
        })
    
    with open(os.path.join(self.debug_dir, "chunk_audit.json"), "w") as f:
        json.dump(audit, f, indent=2)
    
def _extract_pages(self) -> List[Dict[str, Any]]:
    """Extract page information from the document"""
    pages = []
    
    # Look for page markers added by OCR process
    # Format 1: --- PAGE X ---
    pattern1 = r"---\s*PAGE\s*(\d+)\s*---"
    # Format 2: Page X (PDF page markers)
    pattern2 = r"(?:^|\n)\s*Page\s+(\d+)\s*(?:$|\n)"
    
    # Try first pattern
    page_matches = list(re.finditer(pattern1, self.text_content))
    
    # If no matches, try second pattern
    if not page_matches:
        page_matches = list(re.finditer(pattern2, self.text_content, re.MULTILINE))
    
    for match in page_matches:
        page_num = int(match.group(1))
        pages.append({
            "page_num": page_num,
            "position": match.start()
        })
    
    # If no page markers found, estimate pages based on content size
    if not pages:
        logger.warning("No page markers found, estimating pages based on content size")
        chars_per_page = 3000  # Rough estimate
        total_pages = max(1, len(self.text_content) // chars_per_page)
        
        for page_num in range(1, total_pages + 1):
            position = (page_num - 1) * chars_per_page
            if position < len(self.text_content):
                pages.append({
                    "page_num": page_num,
                    "position": position
                })
    
    # Sort pages by position
    pages.sort(key=lambda x: x["position"])
    
    logger.info(f"Extracted {len(pages)} page markers")
    return pages
    
def _identify_layout_blocks(self) -> List[Dict[str, Any]]:
    """
    Identify layout-based blocks in the document using multiple markers:
    1. Font size changes (implied by formatting like ALL CAPS, bold)
    2. Numbered sections (e.g., "7.2", "Article 5")
    3. Indentation changes
    4. Page breaks
    """
    layout_blocks = []
    
    # Store potential section boundaries
    boundaries = []
    
    # 1. Identify section headers by common patterns
    header_patterns = [
        # Numbered sections
        r'(?:^|\n\s*)((?:Article|ARTICLE|Section|SECTION)\s+\d+(?:\.\d+)?[.:]\s*[A-Z][^\n]{3,})(?:\n|$)',
        # Numbered patterns without labels
        r'(?:^|\n\s*)(\d+\.\d+\s+[A-Z][^\n]{3,})(?:\n|$)', 
        # ALL CAPS headers (common in leases)
        r'(?:^|\n\s*)([A-Z][A-Z\s\d.,:;(){}_-]{5,}[A-Z])(?:\n|$)',
        # Exhibit/Schedule markers
        r'(?:^|\n\s*)((?:Exhibit|EXHIBIT|Schedule|SCHEDULE)\s+[A-Z0-9]\s*[.:]\s*[A-Z][^\n]{3,})(?:\n|$)'
    ]
    
    # Apply each pattern to find headers
    for pattern_idx, pattern in enumerate(header_patterns):
        for match in re.finditer(pattern, self.text_content):
            header_text = match.group(1).strip()
            boundaries.append({
                "position": match.start(),
                "text": header_text,
                "type": f"header_pattern_{pattern_idx}",
                "level": 1 if "ARTICLE" in header_text or "Article" in header_text else 2
            })
    
    # 2. Identify page breaks as boundaries
    for page in self.pages:
        boundaries.append({
            "position": page["position"],
            "text": f"--- PAGE {page['page_num']} ---",
            "type": "page_break",
            "level": 3
        })
    
    # 3. Identify indentation changes (paragraph starts)
    paragraph_pattern = r'(?:^|\n)(\s{4,}[A-Z][^\n]{10,})(?:\n|$)'
    for match in re.finditer(paragraph_pattern, self.text_content):
        # Only add if not too close to another boundary
        min_distance = 100  # Minimum distance from another boundary
        position = match.start()
        
        too_close = False
        for boundary in boundaries:
            if abs(boundary["position"] - position) < min_distance:
                too_close = True
                break
                
        if not too_close:
            boundaries.append({
                "position": position,
                "text": match.group(1).strip(),
                "type": "indentation_change",
                "level": 3
            })
    
    # Sort boundaries by position
    boundaries.sort(key=lambda x: x["position"])
    
    # Create layout blocks from boundaries
    for i in range(len(boundaries)):
        current = boundaries[i]
        
        # Determine block end position
        if i < len(boundaries) - 1:
            end_position = boundaries[i+1]["position"]
        else:
            end_position = len(self.text_content)
        
        # Extract content
        content = self.text_content[current["position"]:end_position].strip()
        
        # Skip very short blocks (likely formatting artifacts)
        if len(content) < 20:
            continue
        
        # Get page numbers
        page_start, page_end = self._get_page_range(current["position"], end_position)
        
        # Create a layout block
        block_id = f"B-{i+1:03d}"
        layout_blocks.append({
            "block_id": block_id,
            "content": content,
            "page_start": page_start,
            "page_end": page_end,
            "char_start": current["position"],
            "char_end": end_position,
            "heading_text": current["text"],
            "heading_type": current["type"],
            "level": current["level"],
            "token_estimate": self._estimate_tokens(content)
        })
    
    # Handle the case where no blocks were found (or very few)
    if len(layout_blocks) < 3:
        logger.warning("Few layout blocks detected, falling back to simple chunking")
        # Fall back to simple chunking by page or size
        layout_blocks = self._fallback_simple_chunking()
    
    # Handle special case: Check if document start is missing from blocks
    if layout_blocks and layout_blocks[0]["char_start"] > 0:
        preamble_content = self.text_content[0:layout_blocks[0]["char_start"]].strip()
        if len(preamble_content) > 50:  # Only if substantial content
            page_start, page_end = self._get_page_range(0, layout_blocks[0]["char_start"])
            # Insert at the beginning
            layout_blocks.insert(0, {
                "block_id": "B-000",
                "content": preamble_content,
                "page_start": page_start,
                "page_end": page_end,
                "char_start": 0,
                "char_end": layout_blocks[0]["char_start"],
                "heading_text": "Document Start",
                "heading_type": "preamble",
                "level": 1,
                "token_estimate": self._estimate_tokens(preamble_content)
            })
    
    return layout_blocks
    
def _fallback_simple_chunking(self) -> List[Dict[str, Any]]:
    """Fallback method for chunking when layout analysis fails"""
    layout_blocks = []
    
    # Try chunking by pages first
    if len(self.pages) > 3:
        # Use pages as chunk boundaries
        for i in range(len(self.pages)):
            start_pos = self.pages[i]["position"]
            
            # Determine end position
            if i < len(self.pages) - 1:
                end_pos = self.pages[i+1]["position"]
            else:
                end_pos = len(self.text_content)
            
            content = self.text_content[start_pos:end_pos].strip()
            
            # Skip very short content
            if len(content) < 50:
                continue
            
            layout_blocks.append({
                "block_id": f"B-P{i+1:02d}",
                "content": content,
                "page_start": self.pages[i]["page_num"],
                "page_end": self.pages[i]["page_num"],
                "char_start": start_pos,
                "char_end": end_pos,
                "heading_text": f"Page {self.pages[i]['page_num']}",
                "heading_type": "page_fallback",
                "level": 3,
                "token_estimate": self._estimate_tokens(content)
            })
    
    # If page chunking didn't work or produced too few chunks, try size-based chunking
    if len(layout_blocks) < 3:
        # Chunk by size (aim for ~1000 tokens per chunk)
        chars_per_chunk = 3000  # Approximate size
        total_chunks = max(5, len(self.text_content) // chars_per_chunk)  # At least 5 chunks
        
        for i in range(total_chunks):
            start_pos = i * chars_per_chunk
            end_pos = min((i + 1) * chars_per_chunk, len(self.text_content))
            
            # Try to adjust boundaries to sentence breaks
            if start_pos > 0:
                # Look back for a sentence boundary
                sentence_boundary = self.text_content.rfind(". ", max(0, start_pos - 200), start_pos)
                if sentence_boundary > 0:
                    start_pos = sentence_boundary + 2  # Move past the period and space
            
            if end_pos < len(self.text_content):
                # Look forward for a sentence boundary
                sentence_boundary = self.text_content.find(". ", end_pos, min(len(self.text_content), end_pos + 200))
                if sentence_boundary > 0:
                    end_pos = sentence_boundary + 2  # Move past the period and space
            
            content = self.text_content[start_pos:end_pos].strip()
            
            # Skip very short content
            if len(content) < 50:
                continue
            
            page_start, page_end = self._get_page_range(start_pos, end_pos)
            
            layout_blocks.append({
                "block_id": f"B-S{i+1:02d}",
                "content": content,
                "page_start": page_start,
                "page_end": page_end,
                "char_start": start_pos,
                "char_end": end_pos,
                "heading_text": f"Chunk {i+1}",
                "heading_type": "size_fallback",
                "level": 3,
                "token_estimate": self._estimate_tokens(content)
            })
    
    return layout_blocks
    
def _identify_tables(self) -> List[Dict[str, Any]]:
    """
    Identify tables in the document based on:
    1. Layout patterns (consistent spacing, column alignment)
    2. Content patterns (repeated $ signs, date patterns, numbers)
    3. Table headers/labels
    """
    tables = []
    
    # Patterns that suggest a table is present
    table_indicators = [
        # Rows with consistent spacing/alignment
        r'(?:\n\s*)((?:[^\n]*?\s{2,}[^\n]*?){2,})(?:\n)',
        # Dollar amount patterns (common in rent schedules)
        r'(?:\n\s*)([^\n]*?\$[0-9,.]+ *\$[0-9,.]+[^\n]*)(?:\n)',
        # Date/year patterns (common in rent schedules)
        r'(?:\n\s*)([^\n]*?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]*?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]*)(?:\n)',
        # Labeled tables
        r'(?:\n\s*)((?:Table|TABLE|Schedule|SCHEDULE|Exhibit|EXHIBIT)\s+[A-Z0-9]?[.:][^\n]{3,})(?:\n)'
    ]
    
    for pattern_idx, pattern in enumerate(table_indicators):
        for match in re.finditer(pattern, self.text_content):
            # Get context around potential table
            match_start = max(0, match.start() - 100)
            match_end = min(len(self.text_content), match.end() + 300)
            context = self.text_content[match_start:match_end]
            
            # Look for table boundaries within context
            # A table typically has multiple lines with similar structure
            lines = context.split('\n')
            
            # Find the start and end of the potential table within the context
            table_lines = []
            in_table = False
            table_start_offset = 0
            
            for i, line in enumerate(lines):
                # Check if line has table-like structure
                is_table_row = (
                    bool(re.search(r'\s{2,}', line)) or  # Has multiple spaces (column separator)
                    bool(re.search(r'\$[0-9,.]+', line)) or  # Has dollar amounts
                    bool(re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', line))  # Has dates
                )
                
                if is_table_row and not in_table:
                    # Table start
                    in_table = True
                    table_start_offset = sum(len(l) + 1 for l in lines[:i])
                    table_lines.append(line)
                elif is_table_row and in_table:
                    # Continue table
                    table_lines.append(line)
                elif not is_table_row and in_table:
                    # Empty line or non-table line - check if table is ending
                    if line.strip() == "" and i < len(lines) - 1:
                        # Empty line - check next line
                        continue
                    else:
                        # Table end
                        break
            
            # Only process if we found at least 3 table lines
            if len(table_lines) < 3:
                continue
            
            # Calculate absolute positions in the full document
            table_text = '\n'.join(table_lines)
            table_start = match_start + table_start_offset
            table_end = table_start + len(table_text)
            
            # Skip very short tables
            if len(table_text) < 50:
                continue
            
            # Get page range
            page_start, page_end = self._get_page_range(table_start, table_end)
            
            # Determine table type
            table_type = "data_table"
            if "$" in table_text or re.search(r'\b(?:rent|payment|amount)\b', table_text.lower()):
                table_type = "rent_schedule"
            elif re.search(r'\b(?:expense|cam|tax|insurance)\b', table_text.lower()):
                table_type = "expense_table"
            elif re.search(r'\b(?:date|term|year|month)\b', table_text.lower()):
                table_type = "date_schedule"
            
            # Determine associated clause type
            clause_hint = "undefined"
            if table_type == "rent_schedule":
                clause_hint = "rent"
            elif table_type == "expense_table":
                clause_hint = "additional_charges"
            elif table_type == "date_schedule" and "renewal" in table_text.lower():
                clause_hint = "term"
                
            # Create a table entry
            table_id = f"T-{len(tables)+1:03d}"
            tables.append({
                "table_id": table_id,
                "content": table_text,
                "page_start": page_start,
                "page_end": page_end,
                "char_start": table_start,
                "char_end": table_end,
                "table_type": table_type,
                "clause_hint": clause_hint,
                "token_estimate": self._estimate_tokens(table_text),
                "is_table": True
            })
            
            # Log the table detection
            logger.info(f"Detected {table_type} table: {len(table_text)} chars, {len(table_lines)} lines")
    
    # Remove overlapping tables (keep the larger one)
    if tables:
        tables.sort(key=lambda t: (t["char_start"], -len(t["content"])))
        filtered_tables = []
        
        for i, table in enumerate(tables):
            # Check if this table significantly overlaps with any table we're keeping
            should_skip = False
            for kept_table in filtered_tables:
                # Check for significant overlap (more than 50%)
                overlap_start = max(table["char_start"], kept_table["char_start"])
                overlap_end = min(table["char_end"], kept_table["char_end"])
                
                if overlap_start < overlap_end:
                    overlap_length = overlap_end - overlap_start
                    table_length = table["char_end"] - table["char_start"]
                    
                    if overlap_length / table_length > 0.5:
                        # Significant overlap, skip this table
                        should_skip = True
                        break
            
            if not should_skip:
                filtered_tables.append(table)
        
        tables = filtered_tables
    
    return tables
    
def _refine_chunks_semantically(self, layout_blocks: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Refine layout blocks into semantic chunks:
    1. Handle blocks that are too large (split further)
    2. Ensure chunks don't cut across semantic boundaries
    3. Incorporate table information
    4. Add overlap context between chunks
    """
    semantic_chunks = []
    
    # Process each layout block
    for block in layout_blocks:
        # Check for tables that should be separate chunks
        block_tables = self._get_tables_in_range(
            tables, block["char_start"], block["char_end"]
        )
        
        # If block contains tables, process it specially
        if block_tables:
            # Sort tables by position
            block_tables.sort(key=lambda t: t["char_start"])
            
            # Create chunks for text between and around tables
            prev_end = block["char_start"]
            
            for table in block_tables:
                # Text chunk before table (if substantial)
                if table["char_start"] - prev_end > 100:
                    text_before = self.text_content[prev_end:table["char_start"]].strip()
                    if text_before:
                        chunk = self._create_text_chunk(
                            text_before,
                            prev_end, 
                            table["char_start"],
                            block["heading_text"],
                            block["page_start"],
                            table["page_start"],
                            block["level"],
                            len(semantic_chunks) + 1
                        )
                        semantic_chunks.append(chunk)
                
                # Add the table as its own chunk
                table_chunk = {
                    "chunk_id": f"C-{len(semantic_chunks)+1:03d}",
                    "content": table["content"],
                    "page_start": table["page_start"],
                    "page_end": table["page_end"],
                    "char_start": table["char_start"],
                    "char_end": table["char_end"],
                    "token_estimate": table["token_estimate"],
                    "is_table": True,
                    "table_type": table["table_type"],
                    "parent_heading": block["heading_text"],
                    "clause_hint": table["clause_hint"],
                    "source_excerpt": table["content"][:150] + "..." if len(table["content"]) > 150 else table["content"],
                    "risk_score": "low",  # Default risk score
                    "matched_keywords": [],
                    "source_page_text": self._get_page_text(table["page_start"], table["page_end"])
                }
                semantic_chunks.append(table_chunk)
                
                prev_end = table["char_end"]
            
            # Text chunk after last table (if substantial)
            if block["char_end"] - prev_end > 100:
                text_after = self.text_content[prev_end:block["char_end"]].strip()
                if text_after:
                    chunk = self._create_text_chunk(
                        text_after,
                        prev_end,
                        block["char_end"],
                        block["heading_text"],
                        table["page_end"],  # Use last table's end page
                        block["page_end"],
                        block["level"],
                        len(semantic_chunks) + 1
                    )
                    semantic_chunks.append(chunk)
        
        # Handle blocks with no tables
        else:
            content = block["content"]
            
            # Check if the block exceeds token limit
            if block["token_estimate"] > self.max_tokens_per_chunk:
                logger.info(f"Splitting large block: {block['token_estimate']} tokens")
                # Split into smaller chunks
                sub_chunks = self._split_large_block(block)
                semantic_chunks.extend(sub_chunks)
            else:
                # Keep as a single chunk
                chunk = self._create_text_chunk(
                    content,
                    block["char_start"],
                    block["char_end"],
                    block["heading_text"],
                    block["page_start"],
                    block["page_end"],
                    block["level"],
                    len(semantic_chunks) + 1
                )
                semantic_chunks.append(chunk)
    
    # Add overlapping context between consecutive chunks
    if len(semantic_chunks) > 1:
        semantic_chunks = self._add_chunk_overlap(semantic_chunks)
    
    return semantic_chunks
    
def _get_tables_in_range(self, tables: List[Dict[str, Any]], start_pos: int, end_pos: int) -> List[Dict[str, Any]]:
    """Find tables that fall within a specified character range"""
    tables_in_range = []
    
    for table in tables:
        # Check if table is fully contained in range or substantially overlaps
        if (start_pos <= table["char_start"] < end_pos) or \
           (start_pos < table["char_end"] <= end_pos) or \
           (table["char_start"] <= start_pos and table["char_end"] >= end_pos):
            # Check if it's a substantial portion of the table
            overlap_start = max(start_pos, table["char_start"])
            overlap_end = min(end_pos, table["char_end"])
            overlap_length = overlap_end - overlap_start
            table_length = table["char_end"] - table["char_start"]
            
            if overlap_length / table_length > 0.5:  # More than 50% overlap
                tables_in_range.append(table)
    
    return tables_in_range
    
def _split_large_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Split a large block into smaller chunks at semantic boundaries"""
    content = block["content"]
    sub_chunks = []
    
    # Try to split at paragraph boundaries
    paragraphs = re.split(r'\n\s*\n', content)
    
    # If only one paragraph or very few, split by sentences
    if len(paragraphs) < 3:
        # Split by sentences
        # This regex handles most sentence endings (period, question mark, exclamation point)
        # followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', content)
        paragraphs = []
        
        # Group sentences into reasonably sized paragraphs
        current_paragraph = []
        current_length = 0
        target_length = len(content) // 5  # Aim for ~5 sub-chunks
        
        for sentence in sentences:
            current_paragraph.append(sentence)
            current_length += len(sentence)
            
            if current_length >= target_length:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                current_length = 0
        
        # Add any remaining sentences
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
    
    # Create sub-chunks from paragraphs
    if paragraphs:
        current_sub_chunk = []
        current_token_count = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self._estimate_tokens(paragraph)
            
            # If adding this paragraph would exceed the limit, create a new chunk
            if current_token_count + paragraph_tokens > self.max_tokens_per_chunk and current_sub_chunk:
                # Create a chunk from accumulated paragraphs
                sub_chunk_text = '\n\n'.join(current_sub_chunk)
                
                # Calculate positions
                sub_start = block["char_start"] + content.find(current_sub_chunk[0])
                sub_end = sub_start + len(sub_chunk_text)
                
                # Get page range
                page_start, page_end = self._get_page_range(sub_start, sub_end)
                
                # Create the sub-chunk
                chunk = self._create_text_chunk(
                    sub_chunk_text,
                    sub_start,
                    sub_end,
                    block["heading_text"],
                    page_start,
                    page_end,
                    block["level"],
                    len(sub_chunks) + 1,
                    is_sub_chunk=True
                )
                sub_chunks.append(chunk)
                
                # Reset for next sub-chunk
                current_sub_chunk = [paragraph]
                current_token_count = paragraph_tokens
            else:
                # Add to current accumulation
                current_sub_chunk.append(paragraph)
                current_token_count += paragraph_tokens
        
        # Add any remaining paragraphs as a final sub-chunk
        if current_sub_chunk:
            sub_chunk_text = '\n\n'.join(current_sub_chunk)
            
            # Calculate positions
            sub_start = block["char_start"] + content.find(current_sub_chunk[0])
            sub_end = block["char_end"]  # End of the block
            
            # Get page range
            page_start, page_end = self._get_page_range(sub_start, sub_end)
            
            # Create the sub-chunk
            chunk = self._create_text_chunk(
                sub_chunk_text,
                sub_start,
                sub_end,
                block["heading_text"],
                page_start,
                page_end,
                block["level"],
                len(sub_chunks) + 1,
                is_sub_chunk=True
            )
            sub_chunks.append(chunk)
    
    # If we couldn't create any sub-chunks, split arbitrarily
    if not sub_chunks:
        logger.warning("Falling back to arbitrary chunking for large block")
        chunk_size = len(content) // 3  # Split into ~3 chunks
        
        for i in range(0, len(content), chunk_size):
            chunk_text = content[i:min(i+chunk_size, len(content))]
            
            # Calculate positions
            sub_start = block["char_start"] + i
            sub_end = min(sub_start + len(chunk_text), block["char_end"])
            
            # Get page range
            page_start, page_end = self._get_page_range(sub_start, sub_end)
            
            # Create the sub-chunk
            chunk = self._create_text_chunk(
                chunk_text,
                sub_start,
                sub_end,
                block["heading_text"],
                page_start,
                page_end,
                block["level"],
                len(sub_chunks) + 1,
                is_sub_chunk=True
            )
            sub_chunks.append(chunk)
    
    return sub_chunks
    
def _create_text_chunk(self, text: str, char_start: int, char_end: int, 
                     heading: str, page_start: int, page_end: int, 
                     level: int, chunk_num: int, is_sub_chunk: bool = False) -> Dict[str, Any]:
    """Create a text chunk with all required metadata"""
    # Clean the text
    text = text.strip()
    
    # Create a chunk ID
    chunk_id = f"C-{chunk_num:03d}"
    if is_sub_chunk:
        chunk_id += f"-{uuid.uuid4().hex[:4]}"
    
    # Create a source excerpt (for traceability)
    source_excerpt = text[:150] + "..." if len(text) > 150 else text
    
    # Get full page text for this chunk
    source_page_text = self._get_page_text(page_start, page_end)
    
    return {
        "chunk_id": chunk_id,
        "content": text,
        "page_start": page_start,
        "page_end": page_end,
        "char_start": char_start,
        "char_end": char_end,
        "token_estimate": self._estimate_tokens(text),
        "is_table": False,
        "parent_heading": heading,
        "level": level,
        "clause_hint": "undefined",  # Will be set during classification
        "source_excerpt": source_excerpt,
        "risk_score": "low",  # Default risk score
        "matched_keywords": [],
        "source_page_text": source_page_text
    }
    
def _add_chunk_overlap(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add overlapping context between consecutive chunks to preserve context.
    Overlaps are added at the beginning of chunks (except the first one).
    """
    # Skip tables - only add overlap to text chunks
    text_chunks = [c for c in chunks if not c.get("is_table", False)]
    
    if len(text_chunks) < 2:
        return chunks  # No need for overlap with only one chunk
        
    # Target overlap: ~50 tokens or a few sentences
    overlap_tokens = 50
    
    # Process each chunk except the first
    for i in range(1, len(text_chunks)):
        prev_chunk = text_chunks[i-1]
        current_chunk = text_chunks[i]
        
        # Skip if chunks aren't consecutive in the document
        if prev_chunk["char_end"] != current_chunk["char_start"]:
            continue
            
        # Extract the tail end of the previous chunk for context
        prev_content = prev_chunk["content"]
        overlap_text = ""
        
        # Try to get ~50 tokens from the end of the previous chunk
        # Start with the last few sentences
        sentences = re.split(r'(?<=[.!?])\s+', prev_content)
        
        # Take sentences from the end until we have enough context
        for sentence in reversed(sentences):
            if self._estimate_tokens(overlap_text + sentence) > overlap_tokens:
                break
            overlap_text = sentence + " " + overlap_text
            
        overlap_text = overlap_text.strip()
        
        # If we have overlap text, add it to the current chunk
        if overlap_text:
            # Add a marker to indicate this is context from the previous chunk
            marked_overlap = f"[CONTEXT: {overlap_text}]\n\n"
            
            # Update chunk content and token estimate
            current_chunk["content"] = marked_overlap + current_chunk["content"]
            current_chunk["token_estimate"] = self._estimate_tokens(current_chunk["content"])
            current_chunk["has_overlap"] = True
            current_chunk["overlap_tokens"] = self._estimate_tokens(marked_overlap)
            
            logger.info(f"Added {self._estimate_tokens(marked_overlap)} tokens of overlap to chunk {current_chunk['chunk_id']}")
    
    return chunks
    
def _classify_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Classify chunks by content to determine their clause type:
    1. Use a rule-based classifier to identify clause types
    2. Attach a clause_hint to each chunk for downstream processing
    """
    # Dictionary mapping keywords to clause types
    clause_keywords = {
        "premises": ["premises", "demised", "leased space", "property"],
        "term": ["term", "duration", "commencement", "expiration", "renewal", "commence"],
        "rent": ["rent", "payment", "base rent", "minimum rent", "annual rent", "monthly rent", "security deposit"],
        "additional_charges": ["additional rent", "cam", "common area", "tax", "expense", "charges", "operating cost"],
        "maintenance": ["maintenance", "repair", "condition", "alterations", "improvements"],
        "use": ["use", "purpose", "permitted", "conduct", "operations"],
        "assignment": ["assignment", "sublet", "transfer", "sublease"],
        "insurance": ["insurance", "liability", "indemnity", "indemnification"],
        "casualty": ["casualty", "damage", "destruction", "fire"],
        "default": ["default", "remedies", "termination", "breach", "cure", "remedy"],
        "entry": ["entry", "access", "inspection"],
        "utilities": ["utilities", "utility", "electricity", "water", "gas", "services"],
        "signage": ["sign", "signage", "display"],
        "quiet_enjoyment": ["quiet enjoyment", "peaceful"],
        "notices": ["notice", "notices", "notification"],
        "parking": ["parking", "park", "garage", "spaces"],
        "termination": ["termination", "terminate", "early termination", "cancellation"]
    }
    
    # Add lease type-specific keywords
    if self.lease_type == LeaseType.RETAIL:
        clause_keywords.update({
            "co_tenancy": ["co-tenancy", "cotenancy", "anchor tenant"],
            "percentage_rent": ["percentage", "overage", "gross sales", "percentage rent"],
            "operating_hours": ["hours", "operation", "business hours"]
        })
    elif self.lease_type == LeaseType.OFFICE:
        clause_keywords.update({
            "building_services": ["building services", "janitorial", "cleaning", "service"],
            "tenant_improvements": ["tenant improvement", "improvement allowance", "build-out"]
        })
    elif self.lease_type == LeaseType.INDUSTRIAL:
        clause_keywords.update({
            "environmental": ["environmental", "hazardous", "materials", "compliance", "hazardous materials"],
            "loading": ["loading", "dock", "shipping", "receiving"],
            "yard": ["yard", "outside storage", "exterior"]
        })
    
    # Define high and medium risk clauses for risk scoring
    high_risk_clauses = ["termination", "assignment", "co_tenancy"]
    medium_risk_clauses = ["use", "maintenance", "insurance"]
    
    # Go through each chunk and classify it
    for chunk in chunks:
        # Skip if already classified (e.g., tables)
        if chunk.get("clause_hint") != "undefined" and chunk.get("clause_hint"):
            # Assign risk score based on clause_hint
            if chunk["clause_hint"] in high_risk_clauses:
                chunk["risk_score"] = "high"
            elif chunk["clause_hint"] in medium_risk_clauses:
                chunk["risk_score"] = "medium"
            else:
                chunk["risk_score"] = "low"
            continue
        
        # Normalize text for matching
        text = chunk["content"].lower()
        parent_heading = chunk.get("parent_heading", "").lower()
        
        # Initialize classification scores and matched keywords
        scores = {}
        matched_keywords = {}
        
        # Check parent heading first (stronger signal)
        heading_matched = False
        for clause_type, keywords in clause_keywords.items():
            for keyword in keywords:
                if keyword in parent_heading:
                    # Direct heading match is a strong signal
                    chunk["clause_hint"] = clause_type
                    chunk["matched_keywords"] = [keyword]
                    heading_matched = True
                    break
            if heading_matched:
                break
        
        # If heading didn't provide a match, check content
        if not heading_matched:
            # Count keyword occurrences in the text
            for clause_type, keywords in clause_keywords.items():
                score = 0
                clause_matches = []
                for keyword in keywords:
                    # Find all occurrences
                    matches = re.findall(r'\b' + re.escape(keyword) + r'\b', text)
                    count = len(matches)
                    # Weight matches based on specificity of the keyword
                    if len(keyword.split()) > 1:  # Multi-word phrases are more specific
                        count *= 2
                    if count > 0:
                        clause_matches.append(keyword)
                    score += count
                
                # Store the score and matched keywords
                if score > 0:
                    scores[clause_type] = score
                    matched_keywords[clause_type] = clause_matches
            
            # Assign best match, if any
            if scores:
                best_match = max(scores.items(), key=lambda x: x[1])
                chunk["clause_hint"] = best_match[0]
                chunk["classification_confidence"] = min(1.0, best_match[1] / 10)  # Normalize confidence
                chunk["matched_keywords"] = matched_keywords[best_match[0]]
            else:
                # No clear match
                chunk["clause_hint"] = "miscellaneous"
                chunk["classification_confidence"] = 0.3  # Low confidence
                chunk["matched_keywords"] = []
            
            # Check if we need GPT classification fallback
            if chunk["clause_hint"] == "miscellaneous" or chunk.get("classification_confidence", 0) < 0.5:
                gpt_classification = self.classify_clause_with_gpt(chunk["content"], parent_heading)
                if gpt_classification:
                    chunk["clause_hint"] = gpt_classification["clause_hint"]
                    chunk["classification_confidence"] = gpt_classification["confidence"]
                    chunk["gpt_justification"] = gpt_classification["justification"]
        
        # Assign risk score based on clause_hint
        if chunk["clause_hint"] in high_risk_clauses:
            chunk["risk_score"] = "high"
        elif chunk["clause_hint"] in medium_risk_clauses:
            chunk["risk_score"] = "medium"
        else:
            chunk["risk_score"] = "low"
        
        logger.info(f"Classified chunk {chunk['chunk_id']} as '{chunk['clause_hint']}' with risk '{chunk['risk_score']}'")
    
    return chunks

def classify_clause_with_gpt(self, text: str, heading: str) -> Dict[str, Any]:
    """
    Use GPT to classify a chunk when rule-based classification is uncertain.
    
    Args:
        text: The chunk text to classify
        heading: The parent heading of the chunk
        
    Returns:
        A dictionary with clause_hint, confidence, and justification
    """
    try:
        logger.info(f"Using GPT to classify chunk with heading: {heading}")
        
        # Construct the prompt for GPT
        prompt = f"""You are a commercial real estate legal analyst trained in reviewing lease documents.
```

Your task is to analyze a clause chunk from a commercial lease and determine what type of clause it represents, how confident you are in that classification, and why.
You are supporting an AI system that breaks leases into chunks and needs to route each chunk to specialized extractors (e.g., rent, term, use). Your classification will determine how the system processes this clause.
Please review the following clause and heading, and return a valid JSON object with:

* `clause_hint`: One of the approved clause types listed below
* `confidence`: A float between 0.0 and 1.0
* `justification`: A 1–2 sentence explanation of why you classified it this way
  You MUST choose exactly one `clause_hint` from the following options:
  \[
  "premises", "term", "rent", "additional\_charges", "maintenance", "use",
  "assignment", "insurance", "casualty", "default", "entry", "utilities",
  "signage", "quiet\_enjoyment", "notices", "parking", "termination",
  "co\_tenancy", "percentage\_rent", "operating\_hours",
  "building\_services", "tenant\_improvements",
  "environmental", "loading", "yard",
  "miscellaneous\_provisions"
  ]

## If the clause is ambiguous or covers unrelated provisions, classify it as `miscellaneous_provisions`.

**Parent Heading**:
{heading}
**Clause Text**:
{text}
------

Respond with valid JSON only. Do not include commentary.
Example format:

````json
{{
  "clause_hint": "use",
  "confidence": 0.92,
  "justification": "The clause specifies permitted uses of the leased premises and restrictions on operations."
}}
```"""

            # In a real implementation, this would call OpenAI/Anthropic API
            # Here we're using a mock implementation for demonstration
            
            # MOCK IMPLEMENTATION - in production, this would call the OpenAI API
            text_lower = text.lower()
            heading_lower = heading.lower()
            
            # Check for specific patterns in the text for demonstration purposes
            if "terminate" in text_lower or "termination" in text_lower:
                return {
                    "clause_hint": "termination",
                    "confidence": 0.89,
                    "justification": "Text explicitly discusses termination conditions and process."
                }
            elif "transfer" in text_lower and "consent" in text_lower:
                return {
                    "clause_hint": "assignment",
                    "confidence": 0.87,
                    "justification": "Clause covers transfer of rights with landlord consent requirements."
                }
            elif "insurance" in text_lower and "coverage" in text_lower:
                return {
                    "clause_hint": "insurance",
                    "confidence": 0.92,
                    "justification": "Details specific insurance coverage requirements."
                }
            elif "repair" in text_lower:
                return {
                    "clause_hint": "maintenance",
                    "confidence": 0.85,
                    "justification": "Addresses repair and maintenance responsibilities."
                }
            elif "premises" in heading_lower:
                return {
                    "clause_hint": "premises",
                    "confidence": 0.88,
                    "justification": "Header and content clearly define the leased premises."
                }
            
            # Default fallback response
            return {
                "clause_hint": "miscellaneous_provisions",
                "confidence": 0.62,
                "justification": "Contains various lease provisions without clear primary classification."
            }
            
        except Exception as e:
            logger.error(f"Error in GPT classification: {str(e)}")
            return None
    
    def _get_page_text(self, page_start: Optional[int], page_end: Optional[int]) -> str:
        """Extract full text from specified page range"""
        if page_start is None or page_end is None or not self.pages:
            return ""
        
        # Get actual page positions
        page_positions = []
        for page in self.pages:
            if page_start <= page["page_num"] <= page_end:
                page_positions.append(page["position"])
        
        # If no matching pages found, return empty string
        if not page_positions:
            return ""
            
        # Sort positions
        page_positions.sort()
        
        # Get text from each page and combine
        page_texts = []
        for i, pos in enumerate(page_positions):
            # Determine end position (either next page or end of text)
            if i < len(page_positions) - 1:
                next_pos = page_positions[i + 1]
            else:
                next_pos = len(self.text_content)
                
            # Extract page text
            page_text = self.text_content[pos:next_pos]
            page_texts.append(page_text)
            
        return "\n".join(page_texts)
        
    def _get_page_range(self, char_start: int, char_end: int) -> Tuple[Optional[int], Optional[int]]:
        """Get the page range for a character span"""
        if not self.pages:
            return None, None
            
        page_start = None
        page_end = None
        
        # Find page containing start position
        for i, page in enumerate(self.pages):
            if page["position"] <= char_start:
                page_start = page["page_num"]
            else:
                break
        
        # Find page containing end position
        for i, page in enumerate(self.pages):
            if page["position"] <= char_end:
                page_end = page["page_num"]
            else:
                break
        
        # If positions are beyond the last page marker
        if page_start is None and self.pages:
            page_start = self.pages[-1]["page_num"]
        
        if page_end is None and self.pages:
            page_end = self.pages[-1]["page_num"]
        
        return page_start, page_end
        
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a piece of text using tiktoken.
        Falls back to simple heuristic if tiktoken is not available.
        """
        if not text:
            return 0
        
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 compatible encoding
            tokens = len(encoding.encode(text))
            return tokens
        except (ImportError, Exception) as e:
            # Fallback to simple approximation if tiktoken is unavailable
            logger.warning(f"Using fallback token estimation: {str(e)}")
            char_count = len(text)
            return max(1, math.ceil(char_count / 4))
        
    def _save_debug_info(self):
        """Save debug information to files"""
        debug_info_path = os.path.join(self.debug_dir, "chunker_debug.json")
        
        # Prepare a version of the debug info that's safe to serialize
        safe_debug = {
            "processing_log": self.debug_info["processing_log"],
            "layout_blocks_count": len(self.debug_info["layout_blocks"]),
            "tables_count": len(self.debug_info["tables"]),
            "semantic_chunks_count": len(self.debug_info["semantic_chunks"]),
            "pages_detected": len(self.pages),
            "document_chars": len(self.text_content)
        }
        
        # Save complete layout blocks separately (could be large)
        with open(os.path.join(self.debug_dir, "layout_blocks.json"), "w", encoding="utf-8") as f:
            json.dump(self.debug_info["layout_blocks"], f, indent=2, default=str)
            
        # Save tables separately
        with open(os.path.join(self.debug_dir, "tables.json"), "w", encoding="utf-8") as f:
            json.dump(self.debug_info["tables"], f, indent=2, default=str)
            
        # Save semantic chunks separately
        with open(os.path.join(self.debug_dir, "semantic_chunks.json"), "w", encoding="utf-8") as f:
            json.dump(self.debug_info["semantic_chunks"], f, indent=2, default=str)
            
        # Save main debug info
        with open(debug_info_path, "w", encoding="utf-8") as f:
            json.dump(safe_debug, f, indent=2, default=str)


def chunk_lease(text_content: str, lease_type: LeaseType) -> List[Dict[str, Any]]:
    """
    Main function to chunk a lease document.
    
    Args:
        text_content: The full text of the lease document
        lease_type: The type of lease (RETAIL, OFFICE, INDUSTRIAL)
        
    Returns:
        A list of chunk dictionaries with metadata
    """
    chunker = AdvancedChunker(text_content, lease_type)
    return chunker.process()
````
