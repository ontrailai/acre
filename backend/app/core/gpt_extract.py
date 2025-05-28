from typing import List, Dict, Any, Tuple, Optional
import json
import os
import asyncio
import time
import openai
import re
from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger
from app.core.ast_extractor import build_lease_ast, extract_clauses_with_ast
from app.core.improved_prompts import get_optimized_lease_prompts, get_fallback_extraction_prompt
from app.core.ai_native_extractor import extract_with_ai_native

# Semantic indicators for clause inference across sections
CLAUSE_INDICATORS = {
    "entry": ["entry", "access", "landlord may enter", "right to enter", "inspection", "showing"],
    "casualty": ["damage", "destroyed", "fire", "casualty", "destruction", "rebuild", "repair"],
    "assignment": ["assign", "sublet", "transfer", "sublease", "assignment", "subletting"],
    "termination": ["terminate", "termination", "end lease", "notice to quit", "expiration"],
    "default": ["default", "breach", "violation", "fail to pay", "cure period"],
    "insurance": ["insurance", "liability", "coverage", "insured", "policy", "indemnify"],
    "maintenance": ["maintain", "repair", "upkeep", "responsible for", "tenant shall keep"],
    "rent": ["rent", "payment", "monthly", "due date", "amount due", "$"],
    "term": ["term", "commence", "expire", "duration", "lease period", "month-to-month"],
    "use": ["use", "purpose", "permitted use", "business", "residential only", "prohibited"],
    "utilities": ["utilities", "electric", "water", "gas", "tenant pays", "included in rent"],
    "security": ["security deposit", "deposit", "last month", "refundable", "damages"]
}

# Risk patterns to detect
RISK_PATTERNS = {
    "missing_entry_notice": r"(?i)landlord\s+may\s+enter(?!.*notice)",
    "no_grace_period": r"(?i)rent.*due.*(?!grace|period)",
    "unilateral_termination": r"(?i)landlord\s+may\s+terminate.*(?!cause|reason)",
    "no_renewal_option": r"(?i)term.*expire(?!.*renew|option)",
    "broad_assignment_restriction": r"(?i)no\s+assignment.*whatsoever|absolutely\s+no\s+sublet",
    "unlimited_rent_increase": r"(?i)rent.*increase.*(?!limit|cap|maximum)",
    "tenant_pays_all": r"(?i)tenant.*responsible.*all.*repairs|tenant.*pays.*everything",
    "no_habitability_warranty": r"(?i)as\s+is.*condition|no.*warrant.*habitability",
    "placeholder_value": r"\$?\[.*?\]|\{\{.*?\}\}|TBD|to\s+be\s+determined",
    "ambiguous_late_fee": r"(?i)late\s+fee.*(?!amount|percent|\$|\d)"
}

def is_template_lease(text):
    """Check if the lease appears to be a template with placeholders"""
    placeholder_patterns = [r'\[.+?\]', r'\{\{.+?\}\}', r'\$\[#\]']
    placeholder_count = 0
    for pattern in placeholder_patterns:
        placeholder_count += len(re.findall(pattern, text))
    return placeholder_count > 5

def detect_risk_tags(text: str, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect risk tags based on text patterns and extracted data"""
    risk_tags = []
    
    # Check for risk patterns in text
    for risk_name, pattern in RISK_PATTERNS.items():
        if re.search(pattern, text):
            risk_tags.append({
                "type": risk_name,
                "description": f"Risk pattern '{risk_name}' detected in text"
            })
    
    # Check for placeholders in extracted data
    for key, value in extracted_data.items():
        if isinstance(value, str):
            if re.search(r"\[.*?\]|\{\{.*?\}\}", value):
                risk_tags.append({
                    "type": f"placeholder_{key}",
                    "description": f"Placeholder value found in {key}: {value}"
                })
    
    # Remove duplicates based on type
    seen_types = set()
    unique_tags = []
    for tag in risk_tags:
        if tag["type"] not in seen_types:
            seen_types.add(tag["type"])
            unique_tags.append(tag)
    
    return unique_tags

def infer_clause_type(text: str) -> Optional[str]:
    """Infer clause type based on semantic indicators in text"""
    text_lower = text.lower()
    scores = {}
    
    for clause_type, indicators in CLAUSE_INDICATORS.items():
        score = sum(1 for indicator in indicators if indicator in text_lower)
        if score > 0:
            scores[clause_type] = score
    
    if scores:
        # Return the clause type with highest score
        return max(scores, key=scores.get)
    return None

def deduplicate_clauses(clauses: Dict[str, ClauseExtraction]) -> Dict[str, ClauseExtraction]:
    """Deduplicate clauses by type, keeping the most confident and complete version"""
    # Group clauses by their base type (remove _data suffix)
    clause_groups = {}
    
    for key, clause in clauses.items():
        # Extract base clause type
        base_type = key.replace("_data", "").replace("_clause", "")
        
        # Also check the clause hint from structured data
        if hasattr(clause, 'structured_data') and isinstance(clause.structured_data, dict):
            if 'clause_type' in clause.structured_data:
                base_type = clause.structured_data['clause_type']
        
        if base_type not in clause_groups:
            clause_groups[base_type] = []
        clause_groups[base_type].append((key, clause))
    
    # Select best clause from each group
    deduped_clauses = {}
    
    for base_type, clause_list in clause_groups.items():
        if len(clause_list) == 1:
            # Only one clause of this type, keep it
            deduped_clauses[clause_list[0][0]] = clause_list[0][1]
        else:
            # Multiple clauses of same type, select best one
            best_clause = None
            best_key = None
            best_score = -1
            
            for key, clause in clause_list:
                # Calculate quality score
                score = 0
                
                # Confidence is most important
                score += clause.confidence * 100
                
                # Penalize "no information found" content
                if "no information found" in clause.content.lower():
                    score -= 50
                
                # Reward structured data
                if clause.structured_data and len(clause.structured_data) > 0:
                    score += len(clause.structured_data) * 5
                
                # Reward longer, more detailed content
                score += min(len(clause.content) / 100, 10)
                
                # Penalize needs_review
                if clause.needs_review:
                    score -= 20
                
                if score > best_score:
                    best_score = score
                    best_clause = clause
                    best_key = key
            
            if best_clause:
                deduped_clauses[best_key] = best_clause
                
    logger.info(f"Deduplicated {len(clauses)} clauses to {len(deduped_clauses)} unique clauses")
    return deduped_clauses

async def extract_clauses(segments: List[Dict[str, Any]], lease_type: LeaseType, use_ast: bool = True) -> Dict[str, ClauseExtraction]:
    """
    Extract lease clauses from segmented lease text using AI-native approach.
    With higher rate limits, we can use the full AI-native extraction system.
    """
    # Use AI-native extraction for maximum intelligence
    logger.info("Using AI-native extraction - full intelligence mode")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
    
    # Temporarily disable AI-native extraction due to timeout issues
    # Use multi-pass extraction which is more stable
    if False:  # Disabled temporarily
        try:
            # Use the full AI-native extraction system
            logger.info("Attempting AI-native extraction")
            return await extract_with_ai_native(segments, lease_type, api_key)
        except Exception as e:
            logger.error(f"AI-native extraction failed: {e}")
            # Fallback to multi-pass extraction if needed
            logger.info("Falling back to multi-pass extraction")
            return await _extract_clauses_flat(segments, lease_type)
    else:
        # Go directly to multi-pass extraction
        logger.info("Using multi-pass extraction (AI-native disabled)")
        return await _extract_clauses_flat(segments, lease_type)


def _has_hierarchical_structure(segments: List[Dict[str, Any]]) -> bool:
    """
    Check if segments have hierarchical section numbering
    """
    section_pattern = re.compile(r'^\d+(\.\d+)*')
    hierarchical_sections = 0
    
    for segment in segments:
        section_name = segment.get("section_name", "")
        if section_pattern.match(section_name):
            hierarchical_sections += 1
    
    # Use AST if more than 30% of sections have hierarchical numbering
    return hierarchical_sections > len(segments) * 0.3


async def _extract_clauses_flat(segments: List[Dict[str, Any]], lease_type: LeaseType) -> Dict[str, ClauseExtraction]:
    """
    Extract lease clauses from segmented lease text using GPT-4-Turbo.
    Enhanced with deduplication, cross-section inference, and risk detection.
    """
    try:
        # Initialize result dictionary and diagnostics
        all_extracted_clauses = {}
        diagnostics = {
            "total_segments": len(segments),
            "successful_segments": 0,
            "failed_segments": 0,
            "empty_segments": 0,
            "inferred_clauses": 0,
            "risk_tags_found": 0,
            "segment_results": []
        }
        
        # Create debug directory
        debug_dir = os.path.join("app", "storage", "debug", "gpt")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Filter out empty segments and pure signature/certificate sections
        valid_segments = []
        skipped_segments = 0
        
        for s in segments:
            content = s.get("content", "")
            section_name = s.get("section_name", "").lower()
            
            # Skip empty segments
            if not content or len(content) < 20:
                skipped_segments += 1
                logger.info(f"Skipping empty segment: {section_name}")
                continue
                
            # Skip pure signature and certificate sections
            if section_name == "signature" or section_name == "certificate":
                # Check if this is ONLY a signature section (very short)
                if len(content) < 1500:  # Pure signature sections are usually short
                    skipped_segments += 1
                    logger.info(f"Skipping pure signature section: {section_name} ({len(content)} chars)")
                    continue
            
            # Keep all other sections, even if they contain signatures
            valid_segments.append(s)
        
        empty_segments = skipped_segments
        
        if empty_segments > 0:
            logger.warning(f"Skipping {empty_segments} segments with insufficient content")
            diagnostics["empty_segments"] = empty_segments
        
        if not valid_segments:
            logger.error("No valid segments to process")
            with open(os.path.join(debug_dir, "extraction_diagnostics.json"), "w", encoding="utf-8") as f:
                json.dump(diagnostics, f, indent=2)
            return {}
        
        # Process segments in parallel with higher concurrency
        tasks = []
        semaphore = asyncio.Semaphore(10)  # Back to full concurrency
        
        for segment in valid_segments:
            task = process_segment_enhanced(segment, lease_type, semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for i, result in enumerate(results):
            segment_name = valid_segments[i]["section_name"] if i < len(valid_segments) else "unknown"
            
            segment_result = {
                "section_name": segment_name,
                "success": False,
                "error": None,
                "clauses_extracted": 0,
                "inferred_clauses": 0,
                "risk_tags": 0
            }
            
            if isinstance(result, Exception):
                logger.error(f"Error processing segment {segment_name}: {str(result)}")
                segment_result["error"] = str(result)
                diagnostics["failed_segments"] += 1
            elif not result:
                logger.warning(f"No clauses extracted from segment {segment_name}")
                segment_result["error"] = "No clauses extracted"
                diagnostics["failed_segments"] += 1
            else:
                # Count statistics before adding to all_extracted_clauses
                for key, clause in result.items():
                    if hasattr(clause, 'inferred_from_section') and clause.inferred_from_section:
                        segment_result["inferred_clauses"] += 1
                        diagnostics["inferred_clauses"] += 1
                    if hasattr(clause, 'risk_tags') and clause.risk_tags:
                        segment_result["risk_tags"] += len(clause.risk_tags)
                        diagnostics["risk_tags_found"] += len(clause.risk_tags)
                
                all_extracted_clauses.update(result)
                segment_result["success"] = True
                segment_result["clauses_extracted"] = len(result)
                diagnostics["successful_segments"] += 1
            
            diagnostics["segment_results"].append(segment_result)
        
        # Deduplicate clauses to keep only the best version of each type
        extracted_clauses = deduplicate_clauses(all_extracted_clauses)
        
        # If no clauses extracted, try fallback extraction on full text
        if not extracted_clauses and valid_segments:
            logger.warning("No clauses extracted from segments, attempting fallback extraction")
            
            # Combine all segment content
            full_text = "\n\n".join(segment.get("content", "") for segment in valid_segments)
            
            # Try extracting from combined text
            system_prompt, user_prompt = get_fallback_extraction_prompt(full_text[:10000])  # First 10k chars
            
            response = await call_openai_api(system_prompt, user_prompt)
            if response:
                try:
                    fallback_data = json.loads(response)
                    if "detected_clauses" in fallback_data:
                        for clause in fallback_data.get("detected_clauses", []):
                            clause_type = clause.get("clause_type", "unknown")
                            clause_key = f"{clause_type}_fallback_data"
                            
                            extracted_clauses[clause_key] = ClauseExtraction(
                                content=json.dumps(clause.get("extracted_data", {}), indent=2),
                                raw_excerpt=clause.get("supporting_text", "")[:500],
                                confidence=clause.get("confidence", 0.6),
                                page_number=1,
                                risk_tags=detect_risk_tags(clause.get("supporting_text", ""), clause.get("extracted_data", {})),
                                summary_bullet=clause.get("summary", f"Extracted {clause_type} information"),
                                structured_data=clause.get("extracted_data", {}),
                                needs_review=True,
                                field_id=f"fallback.{clause_type}"
                            )
                            
                        logger.info(f"Fallback extraction found {len(extracted_clauses)} clauses")
                except Exception as e:
                    logger.error(f"Error processing fallback extraction: {e}")
        
        # Log extraction statistics
        logger.info(f"Extracted {len(all_extracted_clauses)} total clauses, deduplicated to {len(extracted_clauses)}")
        logger.info(f"Inferred {diagnostics['inferred_clauses']} clauses across sections")
        logger.info(f"Found {diagnostics['risk_tags_found']} risk tags")
        
        # Save diagnostics
        with open(os.path.join(debug_dir, "extraction_diagnostics.json"), "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
        
        return extracted_clauses
        
    except Exception as e:
        logger.error(f"Error extracting clauses: {str(e)}")
        raise

async def process_segment_enhanced(segment: Dict[str, Any], lease_type: LeaseType, semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
    """Process a single lease segment with enhanced inference and risk detection"""
    async with semaphore:
        try:
            # Create debug directory
            debug_dir = os.path.join("app", "storage", "debug", "gpt", segment["section_name"])
            os.makedirs(debug_dir, exist_ok=True)
            
            # Skip empty segments
            if not segment.get("content", "").strip():
                logger.warning(f"Empty segment content for {segment['section_name']}")
                return {}
            
            # Log detailed segment info
            logger.debug(f"Processing segment '{segment['section_name']}' with {len(segment.get('content', ''))} characters")
            
            # Limit content size to prevent timeouts
            max_content_length = 8000  # Characters
            if len(segment.get("content", "")) > max_content_length:
                logger.warning(f"Segment '{segment['section_name']}' content too long ({len(segment.get('content', ''))} chars), truncating to {max_content_length}")
                segment = segment.copy()
                segment["content"] = segment["content"][:max_content_length] + "... [CONTENT TRUNCATED]"
            
            # Get intelligent prompts
            system_prompt, user_prompt = get_intelligent_prompts_enhanced(segment, lease_type)
            
            # Check if template lease
            if is_template_lease(segment.get("content", "")):
                logger.info(f"Detected template lease for segment {segment['section_name']}")
                user_prompt += "\n\nNOTE: This appears to be a template lease with placeholder values. Extract the structure and identify any risk from placeholder values."
            
            # Save prompts for debugging
            with open(os.path.join(debug_dir, "system_prompt.txt"), "w", encoding="utf-8") as f:
                f.write(system_prompt)
            with open(os.path.join(debug_dir, "user_prompt.txt"), "w", encoding="utf-8") as f:
                f.write(user_prompt)
            
            # Call GPT API
            start_time = time.time()
            response = await call_openai_api(system_prompt, user_prompt)
            processing_time = time.time() - start_time
            
            # Log response info
            if response:
                logger.debug(f"GPT response length for '{segment['section_name']}': {len(response)} characters")
            else:
                logger.warning(f"Empty GPT response for segment '{segment['section_name']}'")
            
            # Save response
            with open(os.path.join(debug_dir, "gpt_response.json"), "w", encoding="utf-8") as f:
                f.write(response if response else "NO RESPONSE")
            
            if not response:
                logger.warning(f"Empty response for segment {segment['section_name']}")
                return {}
            
            logger.info(f"GPT response for segment '{segment['section_name']}' received in {processing_time:.2f} seconds")
            
            # Parse JSON response
            try:
                extracted_data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON response for segment {segment['section_name']}: {e}")
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group(0))
                else:
                    return {}
            
            # Process extracted data with enhanced metadata
            result = {}
            
            if isinstance(extracted_data, dict) and "detected_clauses" in extracted_data:
                detected_clauses = extracted_data.get("detected_clauses", [])
                
                logger.info(f"Extracted {len(detected_clauses)} clauses from segment '{segment['section_name']}'")
                
                for clause in detected_clauses:
                    clause_type = clause.get("clause_type", "unknown")
                    
                    # Skip signature and certificate related clauses
                    skip_types = ["signature", "certificate", "acknowledgment", "notary", "witness"]
                    if any(skip_type in clause_type for skip_type in skip_types):
                        logger.info(f"Skipping {clause_type} clause from GPT response")
                        continue
                    
                    # Check if this clause was inferred from a different section
                    inferred_from = None
                    if clause_type not in segment["section_name"].lower():
                        # This clause type doesn't match the section name
                        inferred_from = segment["section_name"]
                    
                    # Detect risk tags
                    risk_tags = detect_risk_tags(
                        clause.get("supporting_text", ""),
                        clause.get("extracted_data", {})
                    )
                    
                    # Add any risk tags from GPT response (convert strings to dicts if needed)
                    if "risk_tags" in clause:
                        for risk_tag in clause["risk_tags"]:
                            if isinstance(risk_tag, str):
                                risk_tags.append({
                                    "type": risk_tag,
                                    "description": f"Risk identified by GPT: {risk_tag}"
                                })
                            elif isinstance(risk_tag, dict):
                                risk_tags.append(risk_tag)
                    
                    # Create unique key for this clause
                    clause_key = f"{clause_type}_data"
                    if clause_key in result:
                        # If we already have this clause type, append a number
                        counter = 2
                        while f"{clause_type}_data_{counter}" in result:
                            counter += 1
                        clause_key = f"{clause_type}_data_{counter}"
                    
                    # Create ClauseExtraction with enhanced metadata
                    standardized_value = {
                        "content": json.dumps(clause.get("extracted_data", {}), indent=2),
                        "raw_excerpt": clause.get("supporting_text", segment.get("content", "")[:200] + "..."),
                        "confidence": clause.get("confidence", 0.8),
                        "page_number": segment.get("page_start"),
                        "risk_tags": risk_tags,
                        "summary_bullet": clause.get("summary", f"Extracted {clause_type} information"),
                        "structured_data": {
                            **clause.get("extracted_data", {}),
                            "clause_type": clause_type,
                            "detection_method": clause.get("detection_method", ""),
                            "inferred_from_section": inferred_from
                        },
                        "needs_review": clause.get("confidence", 1.0) < 0.5 or bool(risk_tags),
                        "field_id": f"{segment['section_name']}.{clause_type}"
                    }
                    
                    # Add inference metadata if applicable
                    if inferred_from:
                        standardized_value["inferred_from_section"] = inferred_from
                    
                    # Add page range
                    if segment.get("page_start") and segment.get("page_end"):
                        standardized_value["page_range"] = f"{segment['page_start']} - {segment['page_end']}"
                    
                    result[clause_key] = ClauseExtraction(**standardized_value)
                
                # Process miscellaneous clauses and try to infer their types
                if "miscellaneous_clauses" in extracted_data:
                    misc_data = extracted_data["miscellaneous_clauses"]
                    if misc_data:
                        # Try to infer clause type from miscellaneous content
                        misc_text = json.dumps(misc_data)
                        inferred_type = infer_clause_type(misc_text)
                        
                        if inferred_type:
                            # Create a properly typed clause instead of miscellaneous
                            risk_tags = detect_risk_tags(misc_text, misc_data)
                            
                            result[f"{inferred_type}_inferred_data"] = ClauseExtraction(
                                content=json.dumps(misc_data, indent=2),
                                raw_excerpt=segment.get("content", "")[:200] + "...",
                                confidence=0.6,  # Lower confidence for inferred
                                page_number=segment.get("page_start"),
                                risk_tags=risk_tags,
                                summary_bullet=f"Inferred {inferred_type} information from miscellaneous content",
                                structured_data={
                                    **misc_data,
                                    "clause_type": inferred_type,
                                    "inferred_from_section": segment["section_name"]
                                },
                                needs_review=True,
                                field_id=f"{segment['section_name']}.{inferred_type}_inferred",
                                inferred_from_section=segment["section_name"]
                            )
                        else:
                            # Keep as miscellaneous but with risk detection
                            risk_tags = detect_risk_tags(misc_text, misc_data)
                            
                            result["miscellaneous_data"] = ClauseExtraction(
                                content=json.dumps(misc_data, indent=2),
                                raw_excerpt=segment.get("content", "")[:200] + "...",
                                confidence=0.7,
                                page_number=segment.get("page_start"),
                                risk_tags=risk_tags,
                                summary_bullet="Additional clause information that doesn't fit standard categories",
                                structured_data=misc_data,
                                needs_review=True,
                                field_id=f"{segment['section_name']}.miscellaneous"
                            )
                        
            elif isinstance(extracted_data, dict):
                # Fallback for simpler response format
                clause_key = f"{segment['section_name']}_data"
                
                # Try to infer actual clause type
                text_content = json.dumps(extracted_data)
                inferred_type = infer_clause_type(text_content)
                if inferred_type:
                    clause_key = f"{inferred_type}_data"
                
                # Detect risks
                risk_tags = detect_risk_tags(text_content, extracted_data)
                
                standardized_value = {
                    "content": json.dumps(extracted_data, indent=2),
                    "raw_excerpt": segment.get("content", "")[:200] + "...",
                    "confidence": 0.9 if not inferred_type else 0.7,
                    "page_number": segment.get("page_start"),
                    "risk_tags": risk_tags,
                    "summary_bullet": f"Extracted {len(extracted_data)} key fields from {segment['section_name']} section",
                    "structured_data": extracted_data,
                    "needs_review": bool(risk_tags) or bool(inferred_type),
                    "field_id": f"{segment['section_name']}.extracted_data"
                }
                
                if inferred_type and inferred_type not in segment["section_name"].lower():
                    standardized_value["inferred_from_section"] = segment["section_name"]
                
                if segment.get("page_start") and segment.get("page_end"):
                    standardized_value["page_range"] = f"{segment['page_start']} - {segment['page_end']}"
                    
                result[clause_key] = ClauseExtraction(**standardized_value)
                    
            return result
            
        except Exception as e:
            logger.error(f"Error processing segment {segment.get('section_name')}: {str(e)}")
            return {}

async def call_openai_api(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI API with enhanced retry logic and diagnostics"""
    max_retries = 3
    retry_delay = 1
    
    system_prompt_preview = system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
    user_prompt_preview = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
    logger.info(f"Calling GPT-4-Turbo with system prompt: {system_prompt_preview}")
    logger.info(f"User prompt: {user_prompt_preview}")
    
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found in environment variables")
            
            def sync_openai_call():
                try:
                    sync_client = openai.OpenAI(api_key=api_key)
                    
                    # Ensure prompts contain "json" when using json_object format
                    modified_user_prompt = user_prompt
                    if "json" not in user_prompt.lower() and "json" not in system_prompt.lower():
                        modified_user_prompt = user_prompt + "\n\nReturn your response as valid JSON format."
                    
                    response = sync_client.chat.completions.create(
                        model="gpt-4-turbo-preview",  # Use full GPT-4 Turbo, not mini
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": modified_user_prompt}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"},
                        max_tokens=4000  # Increase token limit
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.error(f"Synchronous OpenAI call failed: {e}")
                    raise
            
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, sync_openai_call)
                response_content = await asyncio.wait_for(future, timeout=30)  # Reduced from 60 to 30
            
            response_time = time.time() - start_time
            logger.info(f"GPT API call successful in {response_time:.2f} seconds")
            
            return response_content
            
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API call timed out (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                return ""
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"OpenAI API call failed. Retrying in {retry_delay} seconds. Error: {str(e)}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"OpenAI API call failed after {max_retries} attempts: {str(e)}")
                return ""

def get_intelligent_prompts_enhanced(segment: Dict[str, Any], lease_type: LeaseType) -> Tuple[str, str]:
    """Get enhanced prompts with cross-section inference and risk detection"""
    # Use the new optimized prompts
    return get_optimized_lease_prompts(segment, lease_type)

# Keep deprecated functions for backward compatibility
def get_intelligent_prompts(segment: Dict[str, Any], lease_type: LeaseType) -> Tuple[str, str]:
    """DEPRECATED - Use get_intelligent_prompts_enhanced instead"""
    return get_intelligent_prompts_enhanced(segment, lease_type)

def get_section_specific_prompts(segment: Dict[str, Any], lease_type: LeaseType) -> Tuple[str, str]:
    """DEPRECATED - Use get_intelligent_prompts_enhanced instead"""
    return get_intelligent_prompts_enhanced(segment, lease_type)

def get_built_in_prompts_for_section(section_name: str, lease_type: LeaseType) -> Tuple[str, str]:
    """DEPRECATED - Use get_intelligent_prompts_enhanced instead"""
    fake_segment = {"section_name": section_name, "content": "{{content}}"}
    return get_intelligent_prompts_enhanced(fake_segment, lease_type)

# Backward compatibility
async def process_segment(segment: Dict[str, Any], lease_type: LeaseType, semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
    """DEPRECATED - Use process_segment_enhanced instead"""
    return await process_segment_enhanced(segment, lease_type, semaphore)
