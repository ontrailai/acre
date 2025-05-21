from typing import List, Dict, Any, Tuple
import json
import os
import asyncio
import time
import openai
import re
from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger

def is_template_lease(text):
    """Check if the lease appears to be a template with placeholders"""
    placeholder_patterns = [r'\[.+?\]', r'\{\{.+?\}\}', r'\$\[#\]']
    placeholder_count = 0
    for pattern in placeholder_patterns:
        placeholder_count += len(re.findall(pattern, text))
    return placeholder_count > 5  # If more than 5 placeholders, likely a template

async def extract_clauses(segments: List[Dict[str, Any]], lease_type: LeaseType) -> Dict[str, ClauseExtraction]:
    """
    Extract lease clauses from segmented lease text using GPT-4-Turbo.
    Uses parallel processing for faster results with section-specific prompting.
    Enhanced with diagnostic information and input validation.
    """
    try:
        # First, validate segments have required data
        for i, segment in enumerate(segments):
            if not segment.get("content"):
                logger.warning(f"Segment {i} ({segment.get('section_name', 'unknown')}) has no content")
            if len(segment.get("content", "")) < 20:
                logger.warning(f"Segment {i} ({segment.get('section_name', 'unknown')}) has very little content: {len(segment.get('content', ''))} chars")
        
        # Initialize result dictionary and diagnostics
        extracted_clauses = {}
        diagnostics = {
            "total_segments": len(segments),
            "successful_segments": 0,
            "failed_segments": 0,
            "empty_segments": 0,
            "segment_results": []
        }
        
        # Create debug directory
        debug_dir = os.path.join("app", "storage", "debug", "gpt")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Filter out empty segments
        valid_segments = [s for s in segments if s.get("content") and len(s.get("content", "")) > 20]
        empty_segments = len(segments) - len(valid_segments)
        
        if empty_segments > 0:
            logger.warning(f"Skipping {empty_segments} segments with insufficient content")
            diagnostics["empty_segments"] = empty_segments
        
        # Check if we have any segments to process
        if not valid_segments:
            logger.error("No valid segments to process")
            
            # Save diagnostics
            with open(os.path.join(debug_dir, "extraction_diagnostics.json"), "w", encoding="utf-8") as f:
                json.dump(diagnostics, f, indent=2)
            
            return {}
        
        # Process segments in parallel (with reasonable concurrency limit)
        tasks = []
        semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls
        
        for segment in valid_segments:
            task = process_segment(segment, lease_type, semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results and check for exceptions
        for i, result in enumerate(results):
            segment_name = valid_segments[i]["section_name"] if i < len(valid_segments) else "unknown"
            
            # Track segment result
            segment_result = {
                "section_name": segment_name,
                "success": False,
                "error": None,
                "clauses_extracted": 0
            }
            
            # Check if result is an exception
            if isinstance(result, Exception):
                logger.error(f"Error processing segment {segment_name}: {str(result)}")
                segment_result["error"] = str(result)
                diagnostics["failed_segments"] += 1
            elif not result:  # Empty result
                logger.warning(f"No clauses extracted from segment {segment_name}")
                segment_result["error"] = "No clauses extracted"
                diagnostics["failed_segments"] += 1
            else:  # Successful extraction
                extracted_clauses.update(result)
                segment_result["success"] = True
                segment_result["clauses_extracted"] = len(result)
                diagnostics["successful_segments"] += 1
            
            diagnostics["segment_results"].append(segment_result)
        
        # Log extraction statistics
        logger.info(f"Extracted {len(extracted_clauses)} clauses from {diagnostics['successful_segments']} successful segments")
        logger.info(f"Failed segments: {diagnostics['failed_segments']}")
        
        # Save diagnostics
        with open(os.path.join(debug_dir, "extraction_diagnostics.json"), "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
        
        # If no clauses were extracted at all, this is a critical failure
        if not extracted_clauses:
            logger.error("CRITICAL: No lease clauses extracted from any segment")
            # Save the segments for debugging
            with open(os.path.join(debug_dir, "segments_with_no_extractions.json"), "w", encoding="utf-8") as f:
                json.dump(valid_segments, f, indent=2, default=str)
        
        return extracted_clauses
        
    except Exception as e:
        logger.error(f"Error extracting clauses: {str(e)}")
        raise


async def process_segment(segment: Dict[str, Any], lease_type: LeaseType, semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
    """Process a single lease segment with GPT using section-specific prompts"""
    async with semaphore:
        try:
            # Create debug directory
            debug_dir = os.path.join("app", "storage", "debug", "gpt", segment["section_name"])
            os.makedirs(debug_dir, exist_ok=True)
            
            # Skip empty segments
            if not segment.get("content", "").strip():
                logger.warning(f"Empty segment content for {segment['section_name']}")
                return {}
            
            # Check for minimum content length
            if len(segment.get("content", "").strip()) < 50:
                logger.warning(f"Segment {segment['section_name']} has very short content: {len(segment.get('content', '').strip())} chars")
                
            # Get section-specific prompts
            system_prompt, user_prompt = get_section_specific_prompts(segment, lease_type)
            
            # Check if this appears to be a template lease and adjust prompts
            if is_template_lease(segment.get("content", "")):
                logger.info(f"Detected template lease for segment {segment['section_name']}")
                user_prompt += "\n\nNOTE: This appears to be a template lease with placeholder values such as [DATE], [AMOUNT], etc. Please focus on extracting the structure and clause types, treating placeholders as valid values. For each placeholder, extract its purpose rather than the placeholder itself."
            
            # Save prompts for debugging
            with open(os.path.join(debug_dir, "system_prompt.txt"), "w", encoding="utf-8") as f:
                f.write(system_prompt)
                
            with open(os.path.join(debug_dir, "user_prompt.txt"), "w", encoding="utf-8") as f:
                f.write(user_prompt)
            
            # Log the segment details
            logger.info(f"Processing segment '{segment['section_name']}' ({len(segment.get('content', ''))} chars)")
            
            # Call GPT API with section-specific prompting
            start_time = time.time()
            response = await call_openai_api(system_prompt, user_prompt)
            processing_time = time.time() - start_time
            
            # Save the response
            with open(os.path.join(debug_dir, "gpt_response.json"), "w", encoding="utf-8") as f:
                f.write(response if response else "NO RESPONSE")
            
            # Process and validate response
            if not response:
                logger.warning(f"Empty response for segment {segment['section_name']} after {processing_time:.2f} seconds")
                return {}
            
            logger.info(f"GPT response for segment '{segment['section_name']}' received in {processing_time:.2f} seconds")
                
            # Parse JSON
            extracted_data = None
            parse_error = None
            
            try:
                extracted_data = json.loads(response)
            except json.JSONDecodeError as e:
                parse_error = str(e)
                logger.warning(f"Invalid JSON response for segment {segment['section_name']}: {e}")
                
                # Save the problematic response for analysis
                with open(os.path.join(debug_dir, "invalid_json_response.txt"), "w", encoding="utf-8") as f:
                    f.write(response)
                    
                # Try to extract JSON from the response with regex
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        extracted_data = json.loads(json_match.group(0))
                        logger.info(f"Successfully extracted JSON from response using regex")
                    else:
                        logger.error(f"No JSON found in response using regex")
                        return {}
                except Exception as regex_e:
                    logger.error(f"Regex extraction also failed: {str(regex_e)}")
                    return {}
            
            # Log the parsed data structure
            with open(os.path.join(debug_dir, "parsed_response.json"), "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2)
            
            # Process the extracted data into a standardized format
            result = {}
            for key, value in extracted_data.items():
                # Ensure consistent structure for all extracted clauses
                if isinstance(value, dict):
                    # Make sure all required fields are present
                    standardized_value = {
                        "content": value.get("content", ""),
                        "raw_excerpt": value.get("source_excerpt", value.get("raw_excerpt", "")),
                        "confidence": value.get("confidence_score", value.get("confidence", 0.5)),
                        "page_number": segment.get("page_start") or value.get("page_number"),
                        "risk_tags": value.get("risk_flags", value.get("risk_tags", [])),
                        "summary_bullet": value.get("summary_bullet", ""),
                        "structured_data": value.get("structured_json", value.get("structured_data", {})),
                        "needs_review": value.get("needs_review", value.get("uncertain", False)),
                        "field_id": f"{segment['section_name']}.{key}"  # Add unique field ID for feedback
                    }
                    
                    # Add page range if available
                    if segment.get("page_start") and segment.get("page_end"):
                        standardized_value["page_range"] = f"{segment['page_start']} - {segment['page_end']}"
                        
                    # Create ClauseExtraction
                    result[key] = ClauseExtraction(**standardized_value)
                    
            return result
            
        except Exception as e:
            logger.error(f"Error processing segment {segment.get('section_name')}: {str(e)}")
            return {}


async def call_openai_api(system_prompt: str, user_prompt: str) -> str:
    """
    Call OpenAI API with enhanced retry logic and diagnostics
    """
    max_retries = 3
    retry_delay = 1
    
    # Create a truncated version of prompts for logging (to avoid excessive log size)
    system_prompt_preview = system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
    user_prompt_preview = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
    logger.info(f"Calling GPT-4-Turbo with system prompt: {system_prompt_preview}")
    logger.info(f"User prompt: {user_prompt_preview}")
    
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            # Set API key from environment variable
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("OpenAI API key not found in environment variables")
                raise ValueError("OpenAI API key not found in environment variables. Please add OPENAI_API_KEY to your .env file.")
            
            # Validate API key format (basic check)
            if not (api_key.startswith("sk-") and len(api_key) > 20):
                logger.warning("OpenAI API key format appears invalid. Standard keys should start with 'sk-' and be longer than 20 characters.")
            # Special case for service account keys which have different format
            if api_key.startswith("sk-svcacct-"):
                logger.info("Service account API key detected")
                
            client = openai.AsyncOpenAI(api_key=api_key)
            
            # Calculate token usage for monitoring
            try:
                import tiktoken
                encoding = tiktoken.encoding_for_model("gpt-4")
                system_tokens = len(encoding.encode(system_prompt))
                user_tokens = len(encoding.encode(user_prompt))
                total_tokens = system_tokens + user_tokens
                logger.info(f"Estimated token usage: {total_tokens} tokens (system: {system_tokens}, user: {user_tokens})")
                
                if total_tokens > 8000:
                    logger.warning(f"High token usage detected: {total_tokens}. This may impact response quality or cause truncation.")
            except Exception as token_e:
                logger.warning(f"Could not calculate token usage: {token_e}")
            
            # Call API with timeout
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                ),
                timeout=120  # 120 second timeout (increased from 60)
            )
            
            # Calculate response time
            response_time = time.time() - start_time
            logger.info(f"GPT API call successful in {response_time:.2f} seconds")
            
            # Extract response content
            return response.choices[0].message.content
            
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API call timed out after 120 seconds (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                logger.warning(f"Retrying in {retry_delay} seconds due to timeout")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("OpenAI API calls consistently timing out, giving up")
                return ""  # Return empty string rather than raising exception
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"OpenAI API call failed. Retrying in {retry_delay} seconds. Error: {str(e)}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"OpenAI API call failed after {max_retries} attempts: {str(e)}")
                # Return empty string rather than raising to allow processing to continue
                return ""


def get_section_specific_prompts(segment: Dict[str, Any], lease_type: LeaseType) -> Tuple[str, str]:
    """Get section-specific prompts optimized for each lease section"""
    section_name = segment["section_name"]
    content = segment["content"]
    
    # Try to load custom prompts from the prompts directory
    prompts_dir = os.path.join("app", "storage", "prompts")
    
    try:
        system_prompt_file = os.path.join(prompts_dir, f"{section_name}_system.txt")
        user_prompt_file = os.path.join(prompts_dir, f"{section_name}_user.txt")
        
        if os.path.exists(system_prompt_file) and os.path.exists(user_prompt_file):
            with open(system_prompt_file, 'r') as f:
                system_prompt = f.read()
            with open(user_prompt_file, 'r') as f:
                user_prompt = f.read()
                
            # Replace placeholders
            user_prompt = user_prompt.replace("{{content}}", content)
            user_prompt = user_prompt.replace("{{lease_type}}", lease_type)
                
            return system_prompt, user_prompt
    except Exception as e:
        logger.warning(f"Error loading custom prompts for {section_name}: {str(e)}")
    
    # If custom prompts aren't found, use section-specific built-in prompts
    system_prompt, user_prompt = get_built_in_prompts_for_section(section_name, lease_type)
    
    # Replace content placeholder in user prompt
    user_prompt = user_prompt.replace("{{content}}", content)
    
    return system_prompt, user_prompt


def get_built_in_prompts_for_section(section_name: str, lease_type: LeaseType) -> Tuple[str, str]:
    """Get built-in prompts for specific lease sections"""
    
    # Base system prompt template for all sections
    base_system_prompt = f"""You are an expert paralegal specializing in commercial real estate leases.
Your task is to analyze the {section_name.replace('_', ' ')} section of a {lease_type} lease.
Extract key legal and economic terms with precision. Think like a legal analyst who understands intent, not just formatting.

Important capabilities:
1. Understand dense legal language and extract key financial and legal terms
2. Identify clauses regardless of their formatting or labeling
3. Analyze and flag potential risks
4. Determine terms or clauses that are unusual, vague, or missing

For each key clause you identify, provide:
- A structured_json object with the extracted terms in a clean format
- A summary_bullet with a human-readable explanation
- Any risk_flags with descriptions and severity (low/medium/high)
- A confidence_score (0.0 to 1.0) reflecting your certainty
- The source_excerpt from the original text that supports your extraction

If information is unclear or appears to be missing, explicitly mark it as "uncertain" or "needs_review".
Format numeric values consistently and provide complete interpretations of financial terms.
"""

    # Base user prompt template (general format)
    base_user_prompt = f"""Below is the {section_name.replace('_', ' ')} section from a {lease_type} lease.
Extract all relevant information and return as JSON. Be thorough but precise.

LEASE TEXT:
{{{{content}}}}

Return a JSON object where each key is a specific clause or term, and each value contains:
- "structured_json": A structured representation of the clause data
- "content": A concise explanation of what the clause means
- "summary_bullet": A single bullet point summarizing the key information
- "source_excerpt": The exact text from the lease that supports this extraction
- "confidence_score": A number from 0.0 to 1.0 indicating your confidence
- "risk_flags": An array of objects with "level" (low/medium/high) and "description"
- "needs_review": Boolean indicating if human review is recommended

Example response format:
{{
  "lease_term": {{
    "structured_json": {{
      "start_date": "01/01/2023",
      "end_date": "12/31/2028",
      "initial_term_months": 60,
      "has_renewal_options": true,
      "renewal_options": [
        {{
          "duration_months": 60,
          "notice_period_months": 12
        }}
      ]
    }},
    "content": "The lease has an initial 5-year term starting January 1, 2023 with one 5-year renewal option.",
    "summary_bullet": "5-year initial term (Jan 2023-Dec 2028) with one 5-year renewal option requiring 12 months' notice",
    "source_excerpt": "The term of this Lease (the 'Term') shall commence on January 1, 2023 (the 'Commencement Date') and end on December 31, 2028, unless sooner terminated as provided herein.",
    "confidence_score": 0.95,
    "risk_flags": [],
    "needs_review": false
  }}
}}
"""

    # Section-specific prompts
    if section_name == "premises" or "premises" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Property/building address and description
- Square footage/rentable area (be precise about measurement standards like BOMA)
- Floor/unit number
- Common area access rights
- Any exclusions from the premises
- Special purpose designations
"""
        user_prompt = base_user_prompt

    elif section_name == "term" or "term" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Lease commencement date (including any contingencies)
- Lease expiration date
- Initial term length in years/months
- Any early access/fixturing period
- Renewal or extension options and their terms
- Early termination rights (by either party)
- Notice periods required for exercising options
- Any holdover provisions
"""
        user_prompt = base_user_prompt
        
    elif section_name == "rent" or "payment" in section_name or "rent" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Base rent amount (initial and scheduled increases)
- Rent payment schedule and due dates
- Payment method requirements
- Rent abatements or free rent periods
- Percentage rent terms (for retail leases)
- Late fee provisions
- Security deposit amount and terms
- Operating expense structure (NNN, modified gross, full-service)
- Any CPI or other adjustment mechanisms
- Rent steps or escalations with exact amounts and dates
"""
        user_prompt = base_user_prompt + """
For rent amounts, be very specific about:
- The exact dollar amounts
- The time periods for each rent amount
- The calculation method for any escalations
- The total rent over the initial lease term
"""

    elif "additional" in section_name or "charge" in section_name or "cam" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Common Area Maintenance (CAM) charges
- Real estate taxes responsibility
- Insurance cost responsibility
- Operating expense inclusions and exclusions
- Expense caps or limitations (if any)
- Audit rights for additional charges
- Base year definitions (if applicable)
- Expense stops (if applicable)
- Proportionate share calculations
- Gross-up provisions for operating expenses
"""
        user_prompt = base_user_prompt + """
Pay special attention to:
- Calculation methods for tenant's share of expenses
- Any caps on increases
- Excluded costs (especially capital expenditures)
- Audit rights and limitations
- Expense reconciliation procedures
"""

    elif "maintenance" in section_name or "repair" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Landlord repair responsibilities
- Tenant repair responsibilities
- Maintenance obligations for structural components
- Maintenance obligations for building systems
- Capital repair/replacement responsibilities
- Maintenance standards requirements
- Alterations and improvements rights
- Restoration obligations
- Warranty provisions (if any)
"""
        user_prompt = base_user_prompt
        
    elif "use" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Permitted use clause (exact language)
- Prohibited uses
- Exclusive use provisions
- Operating requirements or continuous operation clauses
- Operating hours requirements
- Signage rights and limitations
- Compliance with laws requirements
- Any use restrictions specific to this property/center
- Merchantability requirements (retail)
"""
        user_prompt = base_user_prompt + """
For retail leases, be particularly alert for:
- Exclusive use rights
- Co-tenancy provisions
- Required operating hours
- Restrictions on merchandise types
"""

    elif "assignment" in section_name or "sublet" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Assignment and subletting rights
- Landlord consent requirements
- Standards for landlord consent (e.g., "not unreasonably withheld")
- Permitted transfers exceptions
- Recapture or termination rights upon request
- Profit sharing on assignment/subletting
- Change of control provisions
- Assignment processing fees
- Timelines for landlord response
"""
        user_prompt = base_user_prompt + """
Pay particular attention to assignment restrictions and any potential flexibility limitations:
- What specific standards must be met for consent?
- Are there any absolute prohibitions?
- Are there any permitted transfers without consent?
- What constitutes a change of control?
"""

    elif "insurance" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Required insurance types and coverage amounts
- Additional insured requirements
- Waiver of subrogation provisions
- Self-insurance allowances (if any)
- Insurance certificate delivery requirements
- Primary/non-contributory requirements
- Notice of cancellation requirements
- Indemnification provisions
- Limitations on liability
"""
        user_prompt = base_user_prompt + """
Be very specific about:
- Exact coverage types required
- Minimum coverage amounts
- Deductible limitations
- Any mutual or one-sided waivers
- Any gaps in coverage requirements
"""

    elif "default" in section_name or "remedies" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Tenant default triggers and cure periods
- Landlord default triggers and cure periods
- Landlord remedies upon default
- Self-help rights
- Acceleration of rent provisions
- Attorney fees provisions
- Force majeure provisions
- Damage limitations
- Specific performance provisions
"""
        user_prompt = base_user_prompt

    elif "casualty" in section_name or "damage" in section_name:
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Damage/destruction termination rights
- Repair obligations after casualty
- Repair timeframes
- Rent abatement provisions during repairs
- Insurance proceeds application
- End-of-term casualty provisions
- Partial vs. total destruction distinctions
"""
        user_prompt = base_user_prompt
        
    elif any(term in section_name for term in ["option", "renewal", "extension", "termination"]):
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Renewal option terms and conditions
- Extension option terms and conditions
- Early termination rights
- Notice periods for exercising options
- Rent determination for option periods
- Conditions precedent to exercise options
- Right of first offer/refusal provisions
- Expansion rights
- Contraction rights
"""
        user_prompt = base_user_prompt
        
    # For lease type specific sections
    elif lease_type == LeaseType.RETAIL and ("co_tenancy" in section_name or "cotenancy" in section_name):
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Anchor tenant co-tenancy requirements
- Occupancy threshold co-tenancy requirements
- Co-tenancy remedies (rent abatement, termination, etc.)
- Cure periods for co-tenancy failures
- Duration limitations on co-tenancy remedies
- Replacement tenant provisions
"""
        user_prompt = base_user_prompt
        
    elif lease_type == LeaseType.INDUSTRIAL and ("environmental" in section_name or "hazardous" in section_name):
        system_prompt = base_system_prompt + """
Focus on extracting the following:
- Environmental compliance requirements
- Hazardous materials restrictions
- Environmental indemnifications
- Environmental inspections and testing rights
- Remediation requirements
- Environmental representations and warranties
- Notification requirements for environmental issues
"""
        user_prompt = base_user_prompt

    # Default to base prompts if no specific section is matched
    else:
        system_prompt = base_system_prompt
        user_prompt = base_user_prompt
        
    return system_prompt, user_prompt
