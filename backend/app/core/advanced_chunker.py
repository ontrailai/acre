"""
Recursive GPT-Based Lease Chunking System

This module implements a modern recursive GPT-based chunking system that:
1. Parses lease documents into hierarchical AST (Abstract Syntax Tree)
2. Recursively processes each clause node with GPT-4
3. Produces enriched chunks with clause classification and risk analysis
4. Maintains full traceability and backward compatibility
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import json
import os
import uuid
import math
import asyncio
import time
from collections import defaultdict, Counter
from dataclasses import dataclass
from app.schemas import LeaseType
from app.utils.logger import logger
import openai
from app.core.ai_advanced_chunker import AIAdvancedChunker
from app.core.gpt_cache import gpt_cache

# Debug configuration
try:
    from app.core.debug_config import BYPASS_GPT_FOR_DEBUG, VERBOSE_LOGGING
except ImportError:
    BYPASS_GPT_FOR_DEBUG = False
    VERBOSE_LOGGING = False


@dataclass
class ClauseNode:
    """Represents a node in the lease document AST"""
    heading: str
    content: str
    char_start: int
    char_end: int
    level: int
    parent: Optional['ClauseNode'] = None
    children: List['ClauseNode'] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    @property
    def parent_heading(self) -> str:
        """Get the parent heading for context"""
        return self.parent.heading if self.parent else ""
    
    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)"""
        return len(self.children) == 0
    
    def add_child(self, child: 'ClauseNode'):
        """Add a child node"""
        child.parent = self
        self.children.append(child)
    
    def get_all_descendants(self) -> List['ClauseNode']:
        """Get all descendant nodes recursively"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants


class RecursiveGPTChunker:
    """
    Modern recursive GPT-based lease chunking system that builds an AST
    and processes each clause node with GPT for intelligent classification.
    """
    
    def __init__(self, text_content: str, lease_type: LeaseType):
        """Initialize the recursive chunker"""
        self.text_content = text_content
        self.lease_type = lease_type
        self.root_node = None
        self.pages = self._extract_pages()
        self.debug_dir = os.path.join("app", "storage", "debug", "recursive_chunker")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Telemetry for tracking performance
        self.telemetry = {
            "total_nodes": 0,
            "leaf_nodes": 0,
            "gpt_calls": 0,
            "gpt_failures": 0,
            "processing_time": 0,
            "clause_categories": {},
            "risk_levels": {"high": 0, "medium": 0, "low": 0},
            "total_tokens_used": 0,
            "avg_tokens_per_chunk": 0
        }
        
        # Heading patterns for building AST
        self.heading_patterns = [
            # Article level
            (r'(?:^|\n)\s*((?:ARTICLE|Article)\s+[IVXLCDM]+[:.]\s*[^\n]{3,})(?:\n|$)', 1),
            (r'(?:^|\n)\s*((?:ARTICLE|Article)\s+\d+[:.]\s*[^\n]{3,})(?:\n|$)', 1),
            
            # Section level
            (r'(?:^|\n)\s*((?:SECTION|Section)\s+\d+(?:\.\d+)?[:.]\s*[^\n]{3,})(?:\n|$)', 2),
            (r'(?:^|\n)\s*(\d+\.\d+\s+[A-Z][^\n]{3,})(?:\n|$)', 2),
            
            # Subsection level
            (r'(?:^|\n)\s*((?:SECTION|Section)\s+\d+(?:\.\d+)?[\(\[][a-z0-9]+[\)\]][:.]\s*[^\n]{3,})(?:\n|$)', 3),
            (r'(?:^|\n)\s*(\d+\.\d+[\(\[][a-z0-9]+[\)\]]\s+[A-Z][^\n]{3,})(?:\n|$)', 3),
            
            # General numbered/lettered subsections
            (r'(?:^|\n)\s*([\(\[][a-z0-9]+[\)\]]\s+[A-Z][^\n]{3,})(?:\n|$)', 3),
            
            # ALL CAPS headings (common in leases)
            (r'(?:^|\n)\s*([A-Z][A-Z\s\d.,:;(){}_-]{8,}[A-Z])(?:\n|$)', 2),
        ]
    
    async def process(self) -> List[Dict[str, Any]]:
        """
        Main processing method that builds AST and recursively processes nodes with GPT
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting recursive GPT chunking for {self.lease_type} lease")
            
            # Step 1: Build hierarchical AST
            self.root_node = self._build_ast()
            if not self.root_node:
                logger.error("Failed to build AST - falling back to simple chunking")
                return await self._fallback_chunking()
            
            # Step 2: Recursively process nodes with GPT
            enriched_chunks = await self._process_ast_with_gpt(self.root_node)
            
            # Step 3: Update telemetry
            self.telemetry["processing_time"] = time.time() - start_time
            self.telemetry["total_nodes"] = len(self.root_node.get_all_descendants()) + 1
            self.telemetry["leaf_nodes"] = len([n for n in self.root_node.get_all_descendants() if n.is_leaf])
            
            # Calculate average tokens per chunk
            if self.telemetry["gpt_calls"] > 0:
                self.telemetry["avg_tokens_per_chunk"] = self.telemetry["total_tokens_used"] / self.telemetry["gpt_calls"]
            
            # Step 4: Save debug information
            await self._save_debug_info(enriched_chunks)
            
            logger.info(f"Recursive chunking complete: {len(enriched_chunks)} chunks in {self.telemetry['processing_time']:.2f}s")
            return enriched_chunks
            
        except Exception as e:
            logger.error(f"Error in recursive chunking: {str(e)}")
            return await self._fallback_chunking()
    
    def _build_ast(self) -> Optional[ClauseNode]:
        """
        Build hierarchical AST from lease text using heading patterns
        """
        if len(self.text_content) < 500:
            logger.warning("Document too short for AST building")
            return None
        
        # Find all potential headings
        potential_headings = []
        for pattern, level in self.heading_patterns:
            for match in re.finditer(pattern, self.text_content, re.MULTILINE):
                heading_text = match.group(1).strip()
                potential_headings.append({
                    'text': heading_text,
                    'level': level,
                    'start': match.start(),
                    'end': match.end(),
                    'match_end': match.end()
                })
        
        # Sort by position and remove duplicates
        potential_headings.sort(key=lambda x: (x['start'], x['level']))
        filtered_headings = self._filter_overlapping_headings(potential_headings)
        
        # Group nearby headings to reduce chunk count
        grouped_headings = self._group_nearby_headings(filtered_headings)
        
        if len(grouped_headings) < 2:
            logger.warning("Insufficient headings found for AST - trying fallback patterns")
            return self._build_simple_ast()
        
        # Create root node
        root = ClauseNode(
            heading="Document Root",
            content="",
            char_start=0,
            char_end=len(self.text_content),
            level=0,
            page_start=1,
            page_end=self._get_page_for_position(len(self.text_content))
        )
        
        # Build hierarchy with grouped headings
        node_stack = [root]
        
        for i, heading_info in enumerate(grouped_headings):
            # Determine content boundaries
            content_start = heading_info['start']
            if i < len(grouped_headings) - 1:
                content_end = grouped_headings[i + 1]['start']
            else:
                content_end = len(self.text_content)
            
            # Extract content
            content = self.text_content[content_start:content_end].strip()
            if len(content) < 50:  # Skip very short content
                continue
            
            # Create node
            node = ClauseNode(
                heading=heading_info['text'],
                content=content,
                char_start=content_start,
                char_end=content_end,
                level=heading_info['level'],
                page_start=self._get_page_for_position(content_start),
                page_end=self._get_page_for_position(content_end)
            )
            
            # Find appropriate parent in stack
            while len(node_stack) > 1 and node_stack[-1].level >= node.level:
                node_stack.pop()
            
            # Add to parent
            parent = node_stack[-1]
            parent.add_child(node)
            node_stack.append(node)
        
        logger.info(f"Built AST with {len(root.get_all_descendants())} nodes")
        return root
    
    def _group_nearby_headings(self, headings: List[Dict]) -> List[Dict]:
        """
        Group headings that are very close together to reduce chunk count
        """
        if not headings:
            return []
        
        grouped = []
        current_group = headings[0]
        
        for i in range(1, len(headings)):
            heading = headings[i]
            # If this heading is within 500 chars of the previous one and same level
            if (heading['start'] - current_group['end'] < 500 and 
                heading['level'] == current_group['level']):
                # Merge into current group
                current_group['end'] = heading['end']
                current_group['text'] += " / " + heading['text']
            else:
                # Start new group
                grouped.append(current_group)
                current_group = heading
        
        grouped.append(current_group)
        
        logger.info(f"Grouped {len(headings)} headings into {len(grouped)} chunks")
        return grouped
    
    def _filter_overlapping_headings(self, headings: List[Dict]) -> List[Dict]:
        """Remove overlapping headings, keeping the most specific ones"""
        filtered = []
        for heading in headings:
            # Check if this heading significantly overlaps with any existing heading
            should_add = True
            for existing in filtered:
                overlap_start = max(heading['start'], existing['start'])
                overlap_end = min(heading['end'], existing['end'])
                
                if overlap_start < overlap_end:
                    overlap_length = overlap_end - overlap_start
                    heading_length = heading['end'] - heading['start']
                    
                    # If there's significant overlap, keep the more specific (higher level) one
                    if overlap_length / heading_length > 0.5:
                        if heading['level'] > existing['level']:
                            # Remove the existing less specific heading
                            filtered.remove(existing)
                        else:
                            # Don't add this less specific heading
                            should_add = False
                            break
            
            if should_add:
                filtered.append(heading)
        
        return filtered
    
    def _build_simple_ast(self) -> Optional[ClauseNode]:
        """
        Fallback AST building when no clear headings are found
        """
        # Try to identify paragraph breaks as boundaries
        paragraphs = re.split(r'\n\s*\n', self.text_content)
        
        if len(paragraphs) < 3:
            # Very simple document - create one root node
            return ClauseNode(
                heading="Complete Document",
                content=self.text_content,
                char_start=0,
                char_end=len(self.text_content),
                level=1,
                page_start=1,
                page_end=self._get_page_for_position(len(self.text_content))
            )
        
        # Create root and add paragraphs as children
        root = ClauseNode(
            heading="Document Root",
            content="",
            char_start=0,
            char_end=len(self.text_content),
            level=0
        )
        
        current_pos = 0
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if len(paragraph) < 50:  # Skip very short paragraphs
                current_pos += len(paragraph) + 2  # Account for line breaks
                continue
            
            # Find actual position in text
            para_start = self.text_content.find(paragraph, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(paragraph)
            
            node = ClauseNode(
                heading=f"Paragraph {i+1}",
                content=paragraph,
                char_start=para_start,
                char_end=para_end,
                level=1,
                page_start=self._get_page_for_position(para_start),
                page_end=self._get_page_for_position(para_end)
            )
            
            root.add_child(node)
            current_pos = para_end + 2
        
        logger.info(f"Built simple AST with {len(root.children)} paragraph nodes")
        return root
    
    async def _process_ast_with_gpt(self, root: ClauseNode) -> List[Dict[str, Any]]:
        """
        Recursively process AST nodes with GPT and return enriched chunks
        """
        chunks = []
        
        # Get all leaf nodes for processing
        leaf_nodes = [node for node in root.get_all_descendants() if node.is_leaf]
        
        if not leaf_nodes:
            # If root is the only node, process it
            leaf_nodes = [root] if root.content.strip() else []
        
        logger.info(f"Processing {len(leaf_nodes)} leaf nodes with GPT")
        
        # Process nodes with controlled concurrency
        # Balance speed with quality - don't overwhelm the system
        semaphore = asyncio.Semaphore(8)  # Process 8 chunks in parallel
        tasks = []
        
        logger.info(f"Creating {len(leaf_nodes)} parallel tasks...")
        
        # Create tasks with semaphore
        for i, node in enumerate(leaf_nodes):
            task = self._enrich_node_with_gpt(node, i + 1, semaphore)
            tasks.append(task)
        
        # Now await all tasks together
        logger.info(f"Awaiting {len(tasks)} parallel GPT calls...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"All GPT calls completed")
        
        # Process results and create chunks
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"GPT processing failed for node {i+1}: {str(result)}")
                self.telemetry["gpt_failures"] += 1
                # Create a basic chunk without GPT enrichment
                chunk = self._create_basic_chunk(leaf_nodes[i], i + 1)
                chunks.append(chunk)
            elif result:
                chunks.append(result)
        
        return chunks
    
    async def _enrich_node_with_gpt_no_semaphore(self, node: ClauseNode, chunk_num: int) -> Optional[Dict[str, Any]]:
        """Enrich node without semaphore for true parallel processing"""
        return await self._enrich_node_with_gpt(node, chunk_num, None)
    
    async def _enrich_node_with_gpt(self, node: ClauseNode, chunk_num: int, semaphore: Optional[asyncio.Semaphore]) -> Optional[Dict[str, Any]]:
        """
        Enrich a single node with GPT analysis
        """
        if semaphore:
            async with semaphore:
                return await self._process_node(node, chunk_num)
        else:
            return await self._process_node(node, chunk_num)
    
    async def _process_node(self, node: ClauseNode, chunk_num: int) -> Optional[Dict[str, Any]]:
        """Process a single node"""
        error_type = None
        was_truncated = False
        truncation_note = None
        
        logger.debug(f"Processing chunk {chunk_num}...")
        
        try:
            # Check token limit and handle smart truncation
            content_tokens = self._estimate_tokens(node.content)
            original_content = node.content
            
            if content_tokens > 2000:  # Optimal chunk size for detailed analysis
                logger.warning(f"Node content too long ({content_tokens} tokens), applying smart truncation")
                node.content, was_truncated = self._smart_truncate_content(node.content, 2000)
                if was_truncated:
                    truncation_note = "Content was truncated due to token limits"
            
            # Track tokens used in telemetry
            final_tokens = self._estimate_tokens(node.content)
            self.telemetry["total_tokens_used"] += final_tokens
            
            # DEBUG MODE: Skip GPT calls
            if BYPASS_GPT_FOR_DEBUG:
                logger.info(f"DEBUG MODE: Bypassing GPT for chunk {chunk_num}")
                # Create a mock GPT response
                gpt_data = {
                    "clause_category": "miscellaneous",
                    "risk_flags": [],
                    "key_values": {},
                    "confidence": 0.5,
                    "justification": "DEBUG MODE: GPT bypassed for testing"
                }
            else:
                # Create GPT prompt
                prompt = self._create_gpt_prompt(node)
                
                # Call GPT with retry logic
                gpt_response = await self._call_gpt_with_retry(prompt)
                if not gpt_response:
                    logger.warning(f"Empty GPT response for node {chunk_num}")
                    error_type = "gpt_timeout"
                    return self._create_basic_chunk(node, chunk_num, error_type, was_truncated, truncation_note)
                
                # Parse GPT response
                gpt_data = self._parse_gpt_response(gpt_response)
                if not gpt_data:
                    logger.warning(f"Failed to parse GPT response for node {chunk_num}")
                    error_type = "malformed_response"
                    return self._create_basic_chunk(node, chunk_num, error_type, was_truncated, truncation_note)
            
            # Add truncation info to justification if needed
            if was_truncated and "truncat" not in gpt_data.get("justification", "").lower():
                gpt_data["justification"] += f" Note: {truncation_note}"
            
            # Create enriched chunk
            chunk = self._create_enriched_chunk(node, chunk_num, gpt_data, was_truncated, truncation_note)
            
            # Update telemetry
            self.telemetry["gpt_calls"] += 1
            clause_category = gpt_data.get("clause_category", "unknown")
            self.telemetry["clause_categories"][clause_category] = self.telemetry["clause_categories"].get(clause_category, 0) + 1
            
            # Count risk levels
            for risk in gpt_data.get("risk_flags", []):
                risk_level = risk.get("risk_level", "low")
                if risk_level in self.telemetry["risk_levels"]:
                    self.telemetry["risk_levels"][risk_level] += 1
            
            return chunk
            
        except asyncio.TimeoutError:
            logger.error(f"GPT timeout for node {chunk_num}")
            self.telemetry["gpt_failures"] += 1
            error_type = "gpt_timeout"
            return self._create_basic_chunk(node, chunk_num, error_type, was_truncated, truncation_note)
        except Exception as e:
            logger.error(f"Error enriching node {chunk_num}: {str(e)}")
            self.telemetry["gpt_failures"] += 1
            error_type = "gpt_error"
            return self._create_basic_chunk(node, chunk_num, error_type, was_truncated, truncation_note)
    
    def _create_gpt_prompt(self, node: ClauseNode) -> str:
        """Create the GPT prompt for a node with injection protection"""
        return f"""You are acting as an expert lease analyst and document intelligence engine.

Your job is to analyze **one specific node (or chunk)** of a commercial lease agreement. This node has been extracted using a layout-aware and semantically guided chunking algorithm. Each node has:

- A heading (e.g. "Section 3.2(a): Percentage Rent")
- A parent heading (e.g. "Article III: Rent")
- The full unmodified content of that clause, as found in the lease
- Page numbers and character positions for traceability

You must classify and extract from this node **without altering the legal language or skipping over hidden or complex provisions**.

---

TASK INSTRUCTIONS

Your output must include the following fields in a JSON object:

1. "clause_category" – The best-fit classification for this clause. Examples: "rent", "maintenance", "use", "assignment", "co_tenancy", "termination", "insurance", etc.

2. "risk_flags" – A list of detected risks in this clause, if any. Each risk must include:
   - "risk_level": "high", "medium", or "low"
   - "description": A short plain-English explanation of the risk

3. "key_values" – A dictionary of any extracted values such as:
   - monetary amounts
   - percentages
   - durations
   - rights or thresholds
   - deadlines or conditions
   These must be **explicitly stated** in the clause (do not infer).

4. "confidence" – A float from 0.0 to 1.0 reflecting how confident you are in the correctness of your classification and extraction.

5. "justification" – A short paragraph (2–3 sentences max) explaining how you classified the clause, where the key values came from, and what risks were detected.

---

STRICT RULES

- Do NOT interpret or rewrite legal language.
- Do NOT hallucinate or fill in missing information.
- Do NOT reword, summarize, or generalize the clause.
- Extract only what is **actually present** in the clause text.
- If multiple concepts exist, classify the primary one and list the rest as secondary risks.

---

CONTEXT

Heading: {node.heading}
Parent Heading: {node.parent_heading}
Page Range: {node.page_start}–{node.page_end}

Clause content is enclosed between <<<CLAUSE_START>>> and <<<CLAUSE_END>>>. Only analyze what's inside.

<<<CLAUSE_START>>>
{node.content}
<<<CLAUSE_END>>>

Please provide your analysis as a JSON object only."""
    
    def _smart_truncate_content(self, content: str, max_tokens: int) -> Tuple[str, bool]:
        """Smart truncation at sentence boundaries when possible"""
        current_tokens = self._estimate_tokens(content)
        if current_tokens <= max_tokens:
            return content, False
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        truncated_content = ""
        for sentence in sentences:
            test_content = truncated_content + sentence + " "
            if self._estimate_tokens(test_content) > max_tokens:
                break
            truncated_content = test_content
        
        # If we couldn't fit even one sentence, do character-based truncation
        if not truncated_content.strip():
            target_chars = int(max_tokens * 4)  # Rough approximation
            truncated_content = content[:target_chars]
        
        return truncated_content.strip(), True
    
    async def _call_gpt_with_retry(self, prompt: str, retries: int = 1) -> Optional[str]:
        """Call GPT API with retry logic - reduced retries for speed"""
        for attempt in range(retries + 1):
            try:
                result = await self._call_gpt(prompt)
                if result:
                    return result
                logger.warning(f"Empty response on attempt {attempt + 1}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on GPT attempt {attempt + 1}")
                if attempt < retries:
                    await asyncio.sleep(1)  # Short delay
            except Exception as e:
                logger.error(f"GPT call failed on attempt {attempt + 1}: {str(e)}")
                if attempt < retries:
                    await asyncio.sleep(1)
        
        logger.error(f"All GPT retry attempts failed")
        return None
    
    async def _call_gpt(self, prompt: str) -> Optional[str]:
        """Call GPT API with the given prompt"""
        # Check cache first
        cached_response = await gpt_cache.get(prompt)
        if cached_response:
            logger.debug("Using cached GPT response")
            return cached_response
        
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("OpenAI API key not found")
                return None
            
            logger.debug(f"Calling GPT-4 with prompt length: {len(prompt)} chars")
            
            try:
                # Try basic client creation
                client = openai.AsyncOpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"OpenAI client creation failed: {e}")
                # Try with minimal config
                try:
                    client = openai.AsyncOpenAI(
                        api_key=api_key,
                        base_url="https://api.openai.com/v1"
                    )
                except Exception as e2:
                    logger.error(f"Alternative OpenAI client creation failed: {e2}")
                    return None
            
            # Add timeout and better error handling
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model="gpt-4-turbo",  # Keep GPT-4 for accuracy
                        messages=[
                            {"role": "system", "content": "You are an expert lease analyst. Respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"},
                        timeout=20  # 20 second timeout per request
                    ),
                    timeout=25  # Overall timeout slightly higher
                )
                
                logger.debug("GPT-4 response received successfully")
                result = response.choices[0].message.content
                
                # Cache the response
                await gpt_cache.set(prompt, result)
                
                return result
                
            except asyncio.TimeoutError:
                logger.error("GPT-4 API call timed out after 35 seconds")
                return None
            except Exception as api_error:
                logger.error(f"GPT-4 API error: {type(api_error).__name__}: {str(api_error)}")
                return None
            
        except Exception as e:
            if "rate_limit_exceeded" in str(e):
                # Extract wait time from error message
                import re
                match = re.search(r'Please try again in (\d+\.?\d*)s', str(e))
                if match:
                    wait_time = float(match.group(1))
                    logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time + 1)  # Add 1s buffer
                    # Retry once after waiting
                    try:
                        return await self._call_gpt(prompt)
                    except Exception as retry_error:
                        logger.error(f"Retry after rate limit failed: {retry_error}")
                        return None
            
            logger.error(f"GPT API call failed: {str(e)}")
            return None
    
    def _parse_gpt_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse GPT JSON response with enhanced validation"""
        try:
            data = json.loads(response)
            
            # Validate required fields and types
            validation_rules = {
                "clause_category": str,
                "risk_flags": list,
                "key_values": dict,
                "confidence": (float, int),
                "justification": str
            }
            
            for field, expected_type in validation_rules.items():
                if field not in data:
                    logger.warning(f"Missing required field in GPT response: {field}")
                    return None
                
                if not isinstance(data[field], expected_type):
                    logger.warning(f"Invalid type for field '{field}': expected {expected_type}, got {type(data[field])}")
                    return None
            
            # Additional validation for specific fields
            if not (0.0 <= data["confidence"] <= 1.0):
                logger.warning(f"Confidence value out of range: {data['confidence']}")
                return None
            
            # Validate risk_flags structure
            for risk in data["risk_flags"]:
                if not isinstance(risk, dict):
                    logger.warning(f"Invalid risk flag structure: {risk}")
                    return None
                if "risk_level" not in risk or "description" not in risk:
                    logger.warning(f"Missing required risk flag fields: {risk}")
                    return None
                if risk["risk_level"] not in ["high", "medium", "low"]:
                    logger.warning(f"Invalid risk level: {risk['risk_level']}")
                    return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {str(e)}")
            return None
    
    def _create_enriched_chunk(self, node: ClauseNode, chunk_num: int, gpt_data: Dict[str, Any], was_truncated: bool = False, truncation_note: str = None) -> Dict[str, Any]:
        """Create an enriched chunk from node and GPT data"""
        # Determine risk score from risk flags
        risk_score = "low"
        if gpt_data.get("risk_flags"):
            risk_levels = [risk.get("risk_level", "low") for risk in gpt_data["risk_flags"]]
            if "high" in risk_levels:
                risk_score = "high"
            elif "medium" in risk_levels:
                risk_score = "medium"
        
        # Create source excerpt
        source_excerpt = node.content[:150] + "..." if len(node.content) > 150 else node.content
        
        chunk_data = {
            "chunk_id": f"R-{chunk_num:03d}",
            "content": node.content,
            "clause_hint": gpt_data["clause_category"],
            "risk_score": risk_score,
            "confidence": gpt_data["confidence"],
            "justification": gpt_data["justification"],
            "page_start": node.page_start,
            "page_end": node.page_end,
            "char_start": node.char_start,
            "char_end": node.char_end,
            "parent_heading": node.parent_heading,
            "heading": node.heading,
            "level": node.level,
            "source_excerpt": source_excerpt,
            "matched_keywords": list(gpt_data.get("key_values", {}).keys()),
            "token_estimate": self._estimate_tokens(node.content),
            "is_table": False,
            "risk_flags": gpt_data.get("risk_flags", []),
            "key_values": gpt_data.get("key_values", {}),
            "gpt_enriched": True,
            "error_flag": False,
            "error_type": None,
            "truncated": was_truncated
        }
        
        if was_truncated and truncation_note:
            chunk_data["truncation_note"] = truncation_note
        
        return chunk_data
    
    def _create_basic_chunk(self, node: ClauseNode, chunk_num: int, error_type: str = None, was_truncated: bool = False, truncation_note: str = None) -> Dict[str, Any]:
        """Create a basic chunk when GPT processing fails"""
        source_excerpt = node.content[:150] + "..." if len(node.content) > 150 else node.content
        
        justification = "GPT processing failed, classified as miscellaneous"
        if was_truncated and truncation_note:
            justification += f". {truncation_note}"
        
        chunk_data = {
            "chunk_id": f"R-{chunk_num:03d}",
            "content": node.content,
            "clause_hint": "miscellaneous",
            "risk_score": "low",
            "confidence": 0.5,
            "justification": justification,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "char_start": node.char_start,
            "char_end": node.char_end,
            "parent_heading": node.parent_heading,
            "heading": node.heading,
            "level": node.level,
            "source_excerpt": source_excerpt,
            "matched_keywords": [],
            "token_estimate": self._estimate_tokens(node.content),
            "is_table": False,
            "risk_flags": [],
            "key_values": {},
            "gpt_enriched": False,
            "error_flag": True,
            "error_type": error_type,
            "truncated": was_truncated
        }
        
        if was_truncated and truncation_note:
            chunk_data["truncation_note"] = truncation_note
        
        return chunk_data
    
    async def _fallback_chunking(self) -> List[Dict[str, Any]]:
        """
        Fallback chunking method when AST building fails
        """
        logger.warning("Using fallback chunking method")
        
        # Simple paragraph-based chunking
        paragraphs = re.split(r'\n\s*\n', self.text_content)
        chunks = []
        
        current_pos = 0
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if len(paragraph) < 50:
                current_pos += len(paragraph) + 2
                continue
            
            # Find position in text
            para_start = self.text_content.find(paragraph, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(paragraph)
            
            chunk = {
                "chunk_id": f"F-{i+1:03d}",
                "content": paragraph,
                "clause_hint": "miscellaneous",
                "risk_score": "low",
                "confidence": 0.3,
                "justification": "Fallback chunking - no AST available",
                "page_start": self._get_page_for_position(para_start),
                "page_end": self._get_page_for_position(para_end),
                "char_start": para_start,
                "char_end": para_end,
                "parent_heading": "",
                "heading": f"Paragraph {i+1}",
                "level": 1,
                "source_excerpt": paragraph[:150] + "..." if len(paragraph) > 150 else paragraph,
                "matched_keywords": [],
                "token_estimate": self._estimate_tokens(paragraph),
                "is_table": False,
                "risk_flags": [],
                "key_values": {},
                "gpt_enriched": False,
                "error_flag": True,
                "error_type": "fallback_used",
                "truncated": False
            }
            
            chunks.append(chunk)
            current_pos = para_end + 2
        
        return chunks
    
    def _extract_pages(self) -> List[Dict[str, Any]]:
        """Extract page information from the document"""
        pages = []
        
        # Look for page markers
        patterns = [
            r"---\s*PAGE\s*(\d+)\s*---",
            r"(?:^|\n)\s*Page\s+(\d+)\s*(?:$|\n)"
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, self.text_content, re.MULTILINE):
                page_num = int(match.group(1))
                pages.append({
                    "page_num": page_num,
                    "position": match.start()
                })
        
        if not pages:
            # Estimate pages based on content size
            chars_per_page = 3000
            total_pages = max(1, len(self.text_content) // chars_per_page)
            
            for page_num in range(1, total_pages + 1):
                position = (page_num - 1) * chars_per_page
                if position < len(self.text_content):
                    pages.append({
                        "page_num": page_num,
                        "position": position
                    })
        
        pages.sort(key=lambda x: x["position"])
        return pages
    
    def _get_page_for_position(self, position: int) -> int:
        """Get page number for a character position"""
        if not self.pages:
            return 1
        
        for i, page in enumerate(self.pages):
            if page["position"] <= position:
                page_num = page["page_num"]
            else:
                break
        else:
            page_num = self.pages[-1]["page_num"]
        
        return page_num
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0
        
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except (ImportError, Exception):
            # Fallback approximation
            return max(1, math.ceil(len(text) / 4))
    
    async def _save_debug_info(self, chunks: List[Dict[str, Any]]):
        """Save debug information and audit files"""
        try:
            # Save telemetry
            with open(os.path.join(self.debug_dir, "telemetry.json"), "w") as f:
                json.dump(self.telemetry, f, indent=2)
            
            # Save audit file
            audit_data = []
            for chunk in chunks:
                audit_data.append({
                    "chunk_id": chunk["chunk_id"],
                    "heading": chunk["heading"],
                    "parent_heading": chunk["parent_heading"],
                    "clause_category": chunk["clause_hint"],
                    "confidence": chunk["confidence"],
                    "risk_score": chunk["risk_score"],
                    "risk_flags": chunk.get("risk_flags", []),
                    "key_values": chunk.get("key_values", {}),
                    "page_range": f"{chunk['page_start']}-{chunk['page_end']}",
                    "gpt_enriched": chunk.get("gpt_enriched", False),
                    "justification": chunk.get("justification", ""),
                    "content_preview": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                })
            
            with open(os.path.join(self.debug_dir, "recursive_chunk_audit.json"), "w") as f:
                json.dump(audit_data, f, indent=2)
            
            # Save AST structure if available
            if self.root_node:
                ast_data = self._serialize_ast(self.root_node)
                with open(os.path.join(self.debug_dir, "ast_structure.json"), "w") as f:
                    json.dump(ast_data, f, indent=2)
            
            logger.info(f"Debug information saved to {self.debug_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save debug info: {str(e)}")
    
    def _serialize_ast(self, node: ClauseNode) -> Dict[str, Any]:
        """Serialize AST node for debugging"""
        return {
            "heading": node.heading,
            "level": node.level,
            "char_start": node.char_start,
            "char_end": node.char_end,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "content_length": len(node.content),
            "content_preview": node.content[:100] + "..." if len(node.content) > 100 else node.content,
            "children": [self._serialize_ast(child) for child in node.children]
        }


class AdvancedChunker:
    """
    Wrapper class to maintain backward compatibility with existing LeaseLogik backend
    Now uses AI-native chunking instead of pattern-based
    """
    
    def __init__(self, text_content: str, lease_type: LeaseType):
        self.text_content = text_content
        self.lease_type = lease_type
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
    async def process(self) -> List[Dict[str, Any]]:
        """Process using AI-native chunking - no patterns"""
        if not self.api_key:
            logger.error("OpenAI API key not found")
            raise ValueError("OpenAI API key not found")
        
        logger.info("Using AI-native chunking system")
        ai_chunker = AIAdvancedChunker(self.text_content, self.lease_type, self.api_key)
        
        try:
            return await ai_chunker.process()
        except Exception as e:
            logger.error(f"AI-native chunking failed: {e}")
            # Fallback to recursive GPT chunker if needed
            logger.info("Falling back to recursive GPT chunker")
            self.chunker = RecursiveGPTChunker(self.text_content, self.lease_type)
            return await self.chunker.process()


def chunk_lease(text_content: str, lease_type: LeaseType) -> List[Dict[str, Any]]:
    """
    Main function to chunk a lease document using recursive GPT processing.
    
    Args:
        text_content: The full text of the lease document
        lease_type: The type of lease (RETAIL, OFFICE, INDUSTRIAL)
        
    Returns:
        A list of chunk dictionaries with GPT enrichment
    """
    chunker = RecursiveGPTChunker(text_content, lease_type)
    
    # Since this is being called from a synchronous context, we need to handle asyncio properly
    try:
        # Check if we're already in an event loop
        import asyncio
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context but being called synchronously
        # This shouldn't happen, but if it does, we need to handle it
        logger.warning("chunk_lease called from within an async context")
        # Create a new thread to run the async code
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, chunker.process())
            return future.result()
    except RuntimeError:
        # No event loop is running - this is the normal case
        # We can safely use asyncio.run
        return asyncio.run(chunker.process())
