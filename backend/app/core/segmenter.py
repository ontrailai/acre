from app.schemas import LeaseType
from typing import Dict, List, Any, Optional, Tuple
import re
import json
import os
from app.utils.logger import logger
from app.core.advanced_chunker import chunk_lease

def segment_lease(text_content: str, lease_type: LeaseType) -> List[Dict[str, Any]]:
    """
    Segment a lease document into logical sections using the advanced chunking system.
    Returns a list of dictionaries, each containing:
    - section_name: The name of the section (as determined by clause classification)
    - content: The text content of the section
    - page_start: Start page number
    - page_end: End page number
    - Additional metadata for improved traceability and processing
    """
    # Check for minimum content length
    if len(text_content) < 500:
        logger.error(f"Text content too short for segmentation: {len(text_content)} chars")
        logger.error(f"Text preview: {text_content[:100]}...")
        return [{
            "section_name": "error_insufficient_content",
            "content": text_content,
            "page_start": None,
            "page_end": None,
            "error": "Insufficient text content for segmentation"
        }]
    
    # Create debug directory
    debug_dir = os.path.join("app", "storage", "debug")
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save full text content for debugging
    with open(os.path.join(debug_dir, "segmenter_input.txt"), "w", encoding="utf-8") as f:
        f.write(text_content)
    
    # Use the advanced chunking system
    try:
        logger.info(f"Starting advanced chunking for {lease_type} lease")
        chunks = chunk_lease(text_content, lease_type)
        logger.info(f"Advanced chunking complete: {len(chunks)} chunks created")
        
        # Save raw chunks for debugging
        with open(os.path.join(debug_dir, "advanced_chunks.json"), "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, default=str)
        
        # Now convert chunks to segments for compatibility with existing pipeline
        segments = []
        for chunk in chunks:
            # Skip chunks with errors
            if "error" in chunk:
                logger.warning(f"Skipping chunk with error: {chunk.get('error')}")
                continue
                
            # Create a segment from this chunk
            segment = {
                "section_name": chunk.get("clause_hint", "miscellaneous"),
                "content": chunk.get("content", ""),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                # Add additional metadata from chunks
                "chunk_id": chunk.get("chunk_id"),
                "char_start": chunk.get("char_start"),
                "char_end": chunk.get("char_end"),
                "token_estimate": chunk.get("token_estimate"),
                "is_table": chunk.get("is_table", False),
                "parent_heading": chunk.get("parent_heading"),
                "source_excerpt": chunk.get("source_excerpt", "")
            }
            
            segments.append(segment)
            
        # If no valid segments were created, fall back to legacy segmentation
        if not segments:
            logger.warning("Advanced chunking produced no valid segments, falling back to legacy segmentation")
            return legacy_segment_lease(text_content, lease_type)
            
        # Log segment statistics
        logger.info(f"Lease segmentation complete. Found {len(segments)} segments")
        for i, segment in enumerate(segments):
            logger.info(f"Segment {i+1}: {segment['section_name']} - {len(segment['content'])} chars")
        
        # Check if any critical sections are very short
        critical_sections = ["premises", "term", "rent", "use", "assignment"]
        short_critical = [s["section_name"] for s in segments 
                         if s["section_name"] in critical_sections and len(s["content"]) < 100]
        
        if short_critical:
            logger.warning(f"Critical sections with very short content: {short_critical}")
        
        return segments
        
    except Exception as e:
        logger.error(f"Error in advanced chunking: {str(e)}", exc_info=True)
        logger.warning("Falling back to legacy segmentation")
        return legacy_segment_lease(text_content, lease_type)


def legacy_segment_lease(text_content: str, lease_type: LeaseType) -> List[Dict[str, Any]]:
    """
    Legacy lease segmentation method. Used as fallback if advanced chunking fails.
    """
    # Initialize segments
    segments = []
    
    # Extract page information from OCR results
    pages = extract_pages(text_content)
    logger.info(f"Page information extracted: {len(pages)} page markers found")
    
    # Get section patterns based on lease type
    section_patterns = get_section_patterns(lease_type)
    logger.info(f"Using {len(section_patterns)} section patterns for {lease_type} lease type")
    
    # Debug info: Check for common headings
    heading_check = check_for_common_headings(text_content)
    if heading_check:
        logger.info(f"Common lease headings found: {heading_check}")
    else:
        logger.warning("No common lease headings detected in text - possible format issue")
    
    # Find all section boundaries
    section_boundaries = []
    pattern_matches = {}  # Track which patterns matched
    
    for section_name, patterns in section_patterns.items():
        pattern_matches[section_name] = []
        for i, pattern in enumerate(patterns):
            for match in re.finditer(pattern, text_content, re.IGNORECASE | re.MULTILINE):
                match_text = match.group(0)
                position = match.start()
                context = get_context_around_match(text_content, position, 40)
                
                section_boundaries.append({
                    "section_name": section_name,
                    "position": position,
                    "match_text": match_text,
                    "pattern_index": i
                })
                
                pattern_matches[section_name].append({
                    "pattern": pattern,
                    "match_text": match_text,
                    "position": position,
                    "context": context
                })
    
    # Log pattern matches
    logger.info(f"Found {len(section_boundaries)} section boundaries")
    
    # Sort boundaries by position
    section_boundaries.sort(key=lambda x: x["position"])
    
    # If no sections found, create a single segment with the entire content
    if not section_boundaries:
        logger.warning("No lease sections detected, attempting fallback segmentation")
        fallback_segments = fallback_segmentation(text_content, lease_type)
        
        if fallback_segments:
            logger.info(f"Fallback segmentation successful: {len(fallback_segments)} segments")
            return fallback_segments
        
        logger.error("Fallback segmentation also failed, creating single segment")
        segments.append({
            "section_name": "entire_lease",
            "content": text_content,
            "page_start": 1 if pages else None,
            "page_end": len(pages) if pages else None,
            "segmentation_error": "No sections detected"
        })
        return segments
    
    # Create segments from boundaries
    for i in range(len(section_boundaries)):
        current = section_boundaries[i]
        
        # Determine segment end position
        if i < len(section_boundaries) - 1:
            end_position = section_boundaries[i+1]["position"]
        else:
            end_position = len(text_content)
        
        # Extract content
        content = text_content[current["position"]:end_position].strip()
        
        # Check if content is too short
        if len(content) < 50:
            logger.warning(f"Segment '{current['section_name']}' has very short content ({len(content)} chars)")
        
        # Estimate page numbers
        page_start, page_end = estimate_page_numbers(current["position"], end_position, pages)
        
        # Add segment
        segments.append({
            "section_name": current["section_name"],
            "content": content,
            "page_start": page_start,
            "page_end": page_end,
            "match_text": current["match_text"],
            "char_count": len(content),
            "non_ws_count": len(re.sub(r'\s', '', content)),
            "line_count": len(content.splitlines()) if content else 0
        })
    
    # Check if the document start is missing
    if section_boundaries[0]["position"] > 0:
        preamble_content = text_content[:section_boundaries[0]["position"]].strip()
        if preamble_content:
            page_start, page_end = estimate_page_numbers(0, section_boundaries[0]["position"], pages)
            segments.insert(0, {
                "section_name": "preamble",
                "content": preamble_content,
                "page_start": page_start,
                "page_end": page_end,
                "match_text": "",
                "char_count": len(preamble_content),
                "non_ws_count": len(re.sub(r'\s', '', preamble_content)),
                "line_count": len(preamble_content.splitlines()) if preamble_content else 0
            })
    
    return segments


def extract_pages(text_content: str) -> List[Dict[str, Any]]:
    """Extract page information from OCR results"""
    pages = []
    
    # Look for page markers added by OCR process
    # Format 1: --- PAGE X ---
    pattern1 = r"---\s*PAGE\s*(\d+)\s*---"
    # Format 2: Page X (PDF page markers)
    pattern2 = r"(?:^|\n)\s*Page\s+(\d+)\s*(?:$|\n)"
    
    # Try first pattern
    page_matches = list(re.finditer(pattern1, text_content))
    
    # If no matches, try second pattern
    if not page_matches:
        page_matches = list(re.finditer(pattern2, text_content, re.MULTILINE))
        logger.info(f"First page pattern failed, trying alternate pattern: found {len(page_matches)} matches")
    
    for match in page_matches:
        page_num = int(match.group(1))
        pages.append({
            "page_num": page_num,
            "position": match.start()
        })
    
    # If still no page markers, try to estimate based on content size
    if not pages:
        logger.warning("No page markers found in text, estimating pages based on content size")
        # Rough estimate: ~3000 chars per page
        chars_per_page = 3000
        total_pages = max(1, len(text_content) // chars_per_page)
        
        for page_num in range(1, total_pages + 1):
            position = (page_num - 1) * chars_per_page
            if position < len(text_content):
                pages.append({
                    "page_num": page_num,
                    "position": position
                })
    
    return pages


def estimate_page_numbers(start_pos: int, end_pos: int, pages: List[Dict[str, Any]]) -> tuple:
    """Estimate page numbers based on positions in text"""
    if not pages:
        return None, None
        
    start_page = None
    end_page = None
    
    # Find page containing start position
    for i, page in enumerate(pages):
        if page["position"] <= start_pos:
            start_page = page["page_num"]
        else:
            break
    
    # Find page containing end position
    for i, page in enumerate(pages):
        if page["position"] <= end_pos:
            end_page = page["page_num"]
        else:
            break
    
    # If no pages were found (due to position being after all page markers)
    # use the last page
    if start_page is None and pages:
        start_page = pages[-1]["page_num"]
    
    if end_page is None and pages:
        end_page = pages[-1]["page_num"]
    
    return start_page, end_page


def get_context_around_match(text: str, position: int, context_chars: int = 40) -> str:
    """Get context around a match position for better debugging"""
    start = max(0, position - context_chars)
    end = min(len(text), position + context_chars)
    
    # Get the context
    context = text[start:end].replace('\n', ' ')
    
    # Add markers to show the match position
    match_pos_in_context = position - start
    marked_context = context[:match_pos_in_context] + ">>>" + context[match_pos_in_context:]
    
    return marked_context


def check_for_common_headings(text: str) -> List[str]:
    """Check for common lease headings to validate text extraction"""
    common_headings = [
        r"\b(?:ARTICLE|SECTION)\s+\d+", # Article or Section numbering
        r"\bWITNESSETH\b", # Common in lease preambles
        r"\bWHEREAS\b", # Common in lease preambles
        r"\bPREMISES\b",
        r"\bTERM\b",
        r"\bRENT\b",
        r"\bMAINTENANCE\b",
        r"\bINSURANCE\b",
        r"\bDEFAULT\b",
        r"\bASSIGNMENT\b",
        r"\bUSE\b",
        r"\bIN WITNESS WHEREOF\b" # Common closing in leases
    ]
    
    found_headings = []
    for heading in common_headings:
        if re.search(heading, text, re.IGNORECASE):
            found_headings.append(heading)
    
    return found_headings


def fallback_segmentation(text_content: str, lease_type: LeaseType) -> List[Dict[str, Any]]:
    """Attempt fallback segmentation when standard method fails"""
    logger.info("Attempting fallback segmentation with simpler patterns")
    
    # Try splitting by ALL CAPS HEADINGS (common in leases)
    segments = []
    
    # Simple pattern for all-caps headings with some flexibility
    heading_pattern = r"(?:^|\n)\s*([A-Z][A-Z\s\d.,:;(){}_-]{10,})(?:\n|$)"
    
    headings = list(re.finditer(heading_pattern, text_content, re.MULTILINE))
    
    if len(headings) >= 3:  # Need at least a few headings for this to be useful
        logger.info(f"Fallback: Found {len(headings)} potential headings with all-caps pattern")
        
        # Create segments based on these headings
        for i, match in enumerate(headings):
            heading_text = match.group(1).strip()
            start_pos = match.end()  # Start after the heading
            
            # Determine end position
            if i < len(headings) - 1:
                end_pos = headings[i+1].start()
            else:
                end_pos = len(text_content)
            
            content = text_content[start_pos:end_pos].strip()
            
            # Skip very short segments
            if len(content) < 50:
                continue
                
            # Guess section type based on heading text
            section_name = guess_section_name(heading_text, lease_type)
            
            segments.append({
                "section_name": section_name,
                "content": content,
                "page_start": None, # We don't have page info in fallback mode
                "page_end": None,
                "match_text": heading_text,
                "char_count": len(content),
                "non_ws_count": len(re.sub(r'\s', '', content)),
                "line_count": len(content.splitlines()),
                "fallback_method": "all_caps_headings"
            })
            
        return segments
    
    # If above method failed, try a secondary method: paragraph numbering
    numbered_para_pattern = r"(?:^|\n)\s*(\d+\.\d+|\d+\.)\s+([^\n]{5,})(?:\n|$)"
    
    numbered_paras = list(re.finditer(numbered_para_pattern, text_content, re.MULTILINE))
    
    if len(numbered_paras) >= 5:  # Need several numbered paragraphs
        logger.info(f"Fallback: Found {len(numbered_paras)} potential numbered paragraphs")
        
        # Group similar paragraphs into sections
        current_section = None
        section_content = ""
        section_start = 0
        
        for i, match in enumerate(numbered_paras):
            number = match.group(1)
            para_text = match.group(2).strip()
            
            # Check if this paragraph starts a new section based on numbering
            is_new_section = False
            
            # If it's a whole number like "1." or "2."
            if re.match(r"^\d+\.$", number):
                is_new_section = True
            
            # New first subsection like "1.1" after "1.9"
            elif i > 0 and "." in number and "." in numbered_paras[i-1].group(1):
                prev_parts = numbered_paras[i-1].group(1).split(".")
                this_parts = number.split(".")
                
                if len(prev_parts) >= 2 and len(this_parts) >= 2:
                    if this_parts[0] != prev_parts[0]:
                        is_new_section = True
            
            # If we're starting a new section and had content in the previous one
            if is_new_section and current_section and section_content:
                # Add the previous section
                segments.append({
                    "section_name": current_section,
                    "content": section_content,
                    "page_start": None,
                    "page_end": None,
                    "match_text": f"Numbered paragraph {number}",
                    "char_count": len(section_content),
                    "non_ws_count": len(re.sub(r'\s', '', section_content)),
                    "line_count": len(section_content.splitlines()),
                    "fallback_method": "numbered_paragraphs"
                })
                
                # Reset for new section
                section_content = ""
            
            # Add content to current section
            if is_new_section:
                # Guess section name from paragraph text
                current_section = guess_section_name(para_text, lease_type)
                section_start = match.start()
            
            # Get content until next paragraph or end
            if i < len(numbered_paras) - 1:
                para_content = text_content[match.end():numbered_paras[i+1].start()]
            else:
                para_content = text_content[match.end():]
            
            section_content += para_text + "\n" + para_content
        
        # Add the last section if we have one
        if current_section and section_content:
            segments.append({
                "section_name": current_section,
                "content": section_content,
                "page_start": None,
                "page_end": None,
                "match_text": "Last numbered section",
                "char_count": len(section_content),
                "non_ws_count": len(re.sub(r'\s', '', section_content)),
                "line_count": len(section_content.splitlines()),
                "fallback_method": "numbered_paragraphs"
            })
        
        return segments
    
    # If all fallback methods failed
    return []


def guess_section_name(heading_text: str, lease_type: LeaseType) -> str:
    """Guess the section name based on heading text"""
    heading_lower = heading_text.lower()
    
    # Map of keywords to section names
    section_map = {
        "premises": ["premises", "demised", "leased space", "property"],
        "term": ["term", "duration", "commencement", "expiration"],
        "rent": ["rent", "payment", "base rent", "minimum rent", "annual rent", "monthly rent"],
        "additional_charges": ["additional rent", "cam", "common area", "tax", "expense", "charges"],
        "maintenance": ["maintenance", "repair", "condition"],
        "use": ["use", "purpose", "permitted", "conduct"],
        "assignment": ["assignment", "sublet", "transfer"],
        "insurance": ["insurance", "liability", "indemnity"],
        "casualty": ["casualty", "damage", "destruction"],
        "default": ["default", "remedies", "termination", "breach"],
        "entry": ["entry", "access"],
        "miscellaneous": ["miscellaneous", "general", "other", "notices"]
    }
    
    # Additional sections for retail
    if lease_type == LeaseType.RETAIL:
        section_map.update({
            "co_tenancy": ["co-tenancy", "cotenancy"],
            "percentage_rent": ["percentage", "overage", "gross sales"],
            "operating_hours": ["hours", "operation"]
        })
    
    # Match heading to a section
    for section_name, keywords in section_map.items():
        for keyword in keywords:
            if keyword in heading_lower:
                return section_name
    
    # If no match, return "misc" with partial heading
    words = heading_lower.split()
    if words:
        short_heading = words[0]
        if len(words) > 1 and len(short_heading) < 4:  # For short first words like "of" or "and"
            short_heading += "_" + words[1]
        return f"misc_{short_heading}"
    
    return "misc_section"


def get_section_patterns(lease_type: LeaseType) -> Dict[str, List[str]]:
    """Get regex patterns for identifying lease sections based on lease type"""
    # Common patterns for all lease types
    common_patterns = {
        "premises": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:DEMISED\s+)?PREMISES\b",
            r"^\s*(?:DEMISED\s+)?PREMISES\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*LEASED\s+PREMISES\b",
            r"^\s*LEASED\s+PREMISES\s*$"
        ],
        "term": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:LEASE\s+)?TERM\b",
            r"^\s*(?:LEASE\s+)?TERM\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*TERM\s+OF\s+LEASE\b"
        ],
        "rent": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:BASE\s+)?RENT\b",
            r"^\s*(?:BASE\s+)?RENT\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*MINIMUM\s+RENT\b",
            r"^\s*MINIMUM\s+RENT\s*$"
        ],
        "additional_charges": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*ADDITIONAL\s+(?:RENT|CHARGES)\b",
            r"^\s*ADDITIONAL\s+(?:RENT|CHARGES)\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:COMMON\s+AREA|CAM)\s+(?:MAINTENANCE|CHARGES)\b"
        ],
        "maintenance": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*MAINTENANCE\b",
            r"^\s*MAINTENANCE\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*REPAIRS\s+AND\s+MAINTENANCE\b"
        ],
        "use": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*USE\s+(?:OF\s+PREMISES)?\b",
            r"^\s*USE\s+(?:OF\s+PREMISES)?\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*PERMITTED\s+USE\b"
        ],
        "assignment": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*ASSIGNMENT\s+AND\s+SUBLETTING\b",
            r"^\s*ASSIGNMENT\s+AND\s+SUBLETTING\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*ASSIGNMENT\b"
        ],
        "insurance": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*INSURANCE\b",
            r"^\s*INSURANCE\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*TENANT'S\s+INSURANCE\b"
        ],
        "casualty": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:DAMAGE|CASUALTY)\b",
            r"^\s*(?:DAMAGE|CASUALTY)\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*DAMAGE\s+OR\s+DESTRUCTION\b"
        ],
        "eminent_domain": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:EMINENT\s+DOMAIN|CONDEMNATION)\b",
            r"^\s*(?:EMINENT\s+DOMAIN|CONDEMNATION)\s*$"
        ],
        "default": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*DEFAULT\b",
            r"^\s*DEFAULT\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*DEFAULT\s+AND\s+REMEDIES\b"
        ],
        "entry": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:RIGHT\s+OF\s+)?ENTRY\b",
            r"^\s*(?:RIGHT\s+OF\s+)?ENTRY\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*LANDLORD'S\s+ACCESS\b"
        ],
        "miscellaneous": [
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*MISCELLANEOUS\b",
            r"^\s*MISCELLANEOUS\s*$",
            r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*GENERAL\s+PROVISIONS\b"
        ]
    }
    
    # Lease type specific patterns
    if lease_type == LeaseType.RETAIL:
        # Add retail-specific patterns
        retail_patterns = {
            "co_tenancy": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*CO[\-\s]TENANCY\b",
                r"^\s*CO[\-\s]TENANCY\s*$"
            ],
            "percentage_rent": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*PERCENTAGE\s+RENT\b",
                r"^\s*PERCENTAGE\s+RENT\s*$"
            ],
            "operating_hours": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*(?:OPERATING|BUSINESS)\s+HOURS\b",
                r"^\s*(?:OPERATING|BUSINESS)\s+HOURS\s*$"
            ]
        }
        common_patterns.update(retail_patterns)
        
    elif lease_type == LeaseType.OFFICE:
        # Add office-specific patterns
        office_patterns = {
            "building_services": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*BUILDING\s+SERVICES\b",
                r"^\s*BUILDING\s+SERVICES\s*$"
            ],
            "tenant_improvements": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*TENANT\s+IMPROVEMENTS\b",
                r"^\s*TENANT\s+IMPROVEMENTS\s*$",
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*IMPROVEMENTS\s+BY\s+TENANT\b"
            ]
        }
        common_patterns.update(office_patterns)
        
    elif lease_type == LeaseType.INDUSTRIAL:
        # Add industrial-specific patterns
        industrial_patterns = {
            "environmental": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*ENVIRONMENTAL\b",
                r"^\s*ENVIRONMENTAL\s*$",
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*ENVIRONMENTAL\s+MATTERS\b"
            ],
            "hazardous_materials": [
                r"\b(?:ARTICLE|SECTION|PARAGRAPH)\s+\d+\s*[.:]\s*HAZARDOUS\s+MATERIALS\b",
                r"^\s*HAZARDOUS\s+MATERIALS\s*$"
            ]
        }
        common_patterns.update(industrial_patterns)
    
    return common_patterns
