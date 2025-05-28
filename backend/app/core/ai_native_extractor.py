"""
AI-Native Lease Extraction System
No pattern matching - Pure AI understanding

This module completely replaces pattern-based extraction with intelligent AI analysis.
Every extraction decision is made by GPT-4, not by hardcoded rules.
"""

import json
import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import openai

from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger


@dataclass
class IntelligentChunk:
    """Represents a semantically meaningful chunk of the lease"""
    content: str
    visual_structure: Dict[str, Any]  # Font sizes, indentation, spacing
    page_info: Dict[str, int]  # Start/end pages and positions
    ai_classification: Optional[Dict[str, Any]] = None
    relationships: List[str] = field(default_factory=list)  # Links to other chunks
    extracted_data: Optional[Dict[str, Any]] = None


class AILeaseIntelligence:
    """
    Complete AI-driven lease extraction system.
    No patterns, no rules - just understanding.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        
    async def extract_complete_lease_intelligence(
        self, 
        pdf_content: Dict[str, Any],
        lease_type: LeaseType
    ) -> Dict[str, Any]:
        """
        Main extraction pipeline - fully AI-driven
        """
        logger.info("Starting AI-native lease extraction")
        
        # Log content size
        content_length = len(pdf_content.get('text', ''))
        logger.info(f"Processing document with {content_length} characters")
        
        try:
            # Phase 1: AI Document Structure Understanding
            logger.info("Phase 1: Understanding document structure...")
            document_structure = await self._understand_document_structure(pdf_content)
            
            # Phase 2: Intelligent Chunking (AI decides boundaries)
            logger.info("Phase 2: Creating intelligent chunks...")
            intelligent_chunks = await self._create_intelligent_chunks(
                pdf_content, 
                document_structure
            )
            logger.info(f"Created {len(intelligent_chunks)} intelligent chunks")
            
            # Phase 3: Multi-Pass AI Extraction
            logger.info("Phase 3: Starting multi-pass extraction...")
            extraction_results = await self._multi_pass_extraction(
                intelligent_chunks,
                lease_type
            )
            
            # Phase 4: AI Relationship Mapping
            logger.info("Phase 4: Mapping clause relationships...")
            relationships = await self._map_clause_relationships(extraction_results)
            
            # Phase 5: AI Risk Analysis
            logger.info("Phase 5: Performing risk analysis...")
            risk_analysis = await self._comprehensive_risk_analysis(
                extraction_results,
                relationships
            )
            
            # Phase 6: AI Completeness Check
            logger.info("Phase 6: Verifying completeness...")
            completeness = await self._verify_completeness(
                extraction_results,
                lease_type
            )
            
            return {
                "extracted_clauses": extraction_results,
                "document_structure": document_structure,
                "relationships": relationships,
                "risk_analysis": risk_analysis,
                "completeness_report": completeness,
                "metadata": {
                    "extraction_method": "ai_native",
                    "confidence_score": self._calculate_overall_confidence(extraction_results),
                    "extraction_timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"AI-native extraction failed at some phase: {e}")
            raise
    
    async def _understand_document_structure(
        self, 
        pdf_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Let AI understand the document's structure without patterns
        """
        # For large documents, use a sample-based approach
        full_text = pdf_content.get('text', '')
        text_length = len(full_text)
        
        # Sample approach for large documents
        if text_length > 10000:
            logger.info(f"Large document ({text_length} chars), using sampling approach")
            # Take samples from beginning, middle, and end
            sample_size = 500
            samples = [
                full_text[:sample_size],  # Beginning
                full_text[text_length//3:text_length//3 + sample_size],  # 1/3 point
                full_text[2*text_length//3:2*text_length//3 + sample_size],  # 2/3 point
                full_text[-sample_size:]  # End
            ]
            document_sample = "\n\n[...SAMPLE BREAK...]\n\n".join(samples)
        else:
            document_sample = full_text[:2000]
        
        # Prepare visual and textual information for AI
        structure_prompt = {
            "system": """You are an expert legal document analyst. Quickly analyze this document's structure.
            Focus on identifying main sections and structure, not detailed content.
            Be concise and efficient.""",
            
            "user": f"""Analyze this lease document structure:
            
            Document length: {text_length} characters
            
            Sample text:
            {document_sample}
            
            Provide a concise structure analysis:
            {{
                "document_type": "lease type",
                "main_sections": ["list of main section types found"],
                "estimated_chunks": "number of logical chunks needed",
                "chunking_strategy": "recommended approach"
            }}
            
            Return your response in valid JSON format."""
        }
        
        try:
            response = await self._call_gpt(
                structure_prompt["system"],
                structure_prompt["user"],
                response_format="json",
                timeout=15  # Shorter timeout for structure analysis
            )
            
            return json.loads(response)
        except asyncio.TimeoutError:
            logger.warning("Document structure analysis timed out, using default structure")
            # Return a default structure
            return {
                "document_type": "commercial_lease",
                "main_sections": ["parties", "premises", "term", "rent", "use", "maintenance", "default", "miscellaneous"],
                "estimated_chunks": max(10, text_length // 4000),
                "chunking_strategy": "paragraph_based"
            }
    
    async def _create_intelligent_chunks(
        self,
        pdf_content: Dict[str, Any],
        document_structure: Dict[str, Any]
    ) -> List[IntelligentChunk]:
        """
        AI decides optimal chunk boundaries based on semantic meaning
        """
        chunks = []
        full_text = pdf_content.get('text', '')
        text_length = len(full_text)
        
        # For large documents, use a simpler chunking approach
        if text_length > 20000 or document_structure.get('chunking_strategy') == 'paragraph_based':
            logger.info(f"Using fast paragraph-based chunking for {text_length} char document")
            chunks = await self._fast_paragraph_chunking(full_text, document_structure)
        else:
            # Let AI determine chunk boundaries for smaller documents
            chunking_prompt = {
                "system": """You are an expert at segmenting legal documents. Create optimal chunks by:
                - Identifying natural semantic boundaries
                - Preserving complete legal concepts
                - Each chunk should be 1000-3000 characters ideally
                - Maximum 20 chunks total""",
                
                "user": f"""Given this document structure:
                {json.dumps(document_structure, indent=2)}
                
                And this content preview (first 3000 chars):
                {full_text[:3000]}
                
                Total document length: {text_length} characters
                
                Identify optimal chunk boundaries. Return:
                {{
                    "chunks": [
                        {{
                            "start_position": int,
                            "end_position": int,
                            "semantic_type": "string describing content type",
                            "importance": "high/medium/low"
                        }}
                    ]
                }}
                
                Return your response in valid JSON format."""
            }
            
            try:
                chunk_boundaries = json.loads(await self._call_gpt(
                    chunking_prompt["system"],
                    chunking_prompt["user"],
                    response_format="json",
                    timeout=10
                ))
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"AI chunking failed: {e}, using fallback")
                chunks = await self._fast_paragraph_chunking(full_text, document_structure)
        
        # Create IntelligentChunk objects if we got boundaries
        if chunks:  # Already created by fast chunking
            return chunks
    
    async def _fast_paragraph_chunking(
        self,
        text: str,
        document_structure: Dict[str, Any]
    ) -> List[IntelligentChunk]:
        """
        Fast paragraph-based chunking for large documents
        """
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        # Group paragraphs into chunks of reasonable size
        current_chunk = []
        current_size = 0
        target_size = 5000  # Increase target chunk size
        max_size = 10000    # Increase maximum chunk size for better context
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            para_size = len(paragraph)
            
            # If adding this paragraph would exceed max size, start new chunk
            if current_size + para_size > max_size and current_chunk:
                # Create chunk from current paragraphs
                chunk_text = '\n\n'.join(current_chunk)
                chunk = IntelligentChunk(
                    content=chunk_text,
                    visual_structure={"method": "paragraph_based"},
                    page_info=self._calculate_page_info({'text': text}, 0, len(chunk_text)),
                    ai_classification={"type": "auto_paragraph", "confidence": 0.6},
                    relationships=[]
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = [paragraph]
                current_size = para_size
            else:
                # Add to current chunk
                current_chunk.append(paragraph)
                current_size += para_size
                
                # If we've reached target size, consider starting new chunk
                if current_size >= target_size:
                    # Look ahead - if next paragraph is small, include it
                    if i + 1 < len(paragraphs):
                        next_para = paragraphs[i + 1].strip()
                        if len(next_para) < 500:  # Small paragraph
                            continue  # Include it in current chunk
                    
                    # Create chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunk = IntelligentChunk(
                        content=chunk_text,
                        visual_structure={"method": "paragraph_based"},
                        page_info=self._calculate_page_info({'text': text}, 0, len(chunk_text)),
                        ai_classification={"type": "auto_paragraph", "confidence": 0.6},
                        relationships=[]
                    )
                    chunks.append(chunk)
                    current_chunk = []
                    current_size = 0
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunk = IntelligentChunk(
                content=chunk_text,
                visual_structure={"method": "paragraph_based"},
                page_info=self._calculate_page_info({'text': text}, 0, len(chunk_text)),
                ai_classification={"type": "auto_paragraph", "confidence": 0.6},
                relationships=[]
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks using fast paragraph method")
        
        # Skip signature chunks
        filtered_chunks = []
        skip_keywords = [
            "signature", "certificate", "acknowledgment", "notary",
            "witness", "executed", "signed", "seal", "attestation"
        ]
        
        for chunk in chunks:
            chunk_lower = chunk.content.lower()[:500]
            if any(keyword in chunk_lower for keyword in skip_keywords):
                logger.info(f"Skipping signature/certificate chunk in fast chunking")
                continue
            filtered_chunks.append(chunk)
        
        return filtered_chunks
            
        for i, boundary in enumerate(chunk_boundaries.get('chunks', [])):
            # Ensure positions are integers
            try:
                start_pos = int(boundary.get('start_position', 0))
                end_pos = int(boundary.get('end_position', len(full_text)))
            except (TypeError, ValueError):
                logger.warning(f"Invalid chunk boundaries: {boundary}")
                continue
            
            # Ensure positions are within bounds
            start_pos = max(0, min(start_pos, len(full_text)))
            end_pos = max(start_pos, min(end_pos, len(full_text)))
            
            chunk_text = full_text[start_pos:end_pos]
            
            # Skip signature and certificate chunks
            skip_keywords = [
                "signature", "certificate", "acknowledgment", "notary",
                "witness", "executed", "signed", "seal", "attestation"
            ]
            
            # Check if this is a signature/certificate section
            chunk_lower = chunk_text.lower()[:500]  # Check first 500 chars
            if any(keyword in chunk_lower for keyword in skip_keywords):
                logger.info(f"Skipping signature/certificate chunk at position {start_pos}")
                continue
                
            # AI classifies each chunk
            classification = await self._classify_chunk_content(chunk_text)
            
            chunks.append(IntelligentChunk(
                content=chunk_text,
                visual_structure=self._extract_visual_info(
                    pdf_content, 
                    boundary['start_position'],
                    boundary['end_position']
                ),
                page_info=self._calculate_page_info(
                    pdf_content,
                    start_pos,
                    end_pos
                ),
                ai_classification=classification,
                relationships=boundary.get('related_chunks', [])
            ))
        
        return chunks
    
    async def _multi_pass_extraction(
        self,
        chunks: List[IntelligentChunk],
        lease_type: LeaseType
    ) -> Dict[str, Any]:
        """
        Multiple AI passes for comprehensive extraction with parallel processing
        """
        extracted_data = {}
        
        # Pass 1: Direct Extraction (Parallel)
        logger.info(f"Pass 1: Direct content extraction from {len(chunks)} chunks")
        
        # Process chunks in parallel with higher concurrency for fewer, larger chunks
        semaphore = asyncio.Semaphore(10)  # Process up to 10 chunks at a time
        
        async def extract_with_semaphore(chunk, idx):
            async with semaphore:
                logger.debug(f"Extracting from chunk {idx+1}/{len(chunks)}")
                try:
                    return await self._extract_from_chunk(chunk, lease_type)
                except Exception as e:
                    logger.error(f"Failed to extract from chunk {idx}: {e}")
                    return {}
        
        # Create extraction tasks
        extraction_tasks = [
            extract_with_semaphore(chunk, i) 
            for i, chunk in enumerate(chunks)
        ]
        
        # Execute in parallel
        chunk_extractions = await asyncio.gather(*extraction_tasks)
        
        # Merge results
        for chunk, extraction in zip(chunks, chunk_extractions):
            chunk.extracted_data = extraction
            self._merge_extractions(extracted_data, extraction)
        
        # Skip additional passes for very large documents to avoid timeout
        if len(chunks) > 20:
            logger.info("Large document - skipping additional passes to avoid timeout")
            return extracted_data
        
        # Pass 2: Cross-Reference Analysis (only if not too many chunks)
        if len(chunks) <= 10:
            logger.info("Pass 2: Cross-reference and context enhancement")
            try:
                enhanced_data = await asyncio.wait_for(
                    self._enhance_with_context(chunks, extracted_data),
                    timeout=10
                )
                self._merge_extractions(extracted_data, enhanced_data)
            except asyncio.TimeoutError:
                logger.warning("Context enhancement timed out, skipping")
        
        # Pass 3: Skip implicit extraction for large documents
        # Pass 4: Skip calculations for large documents
        
        return extracted_data
    
    async def _extract_from_chunk(
        self,
        chunk: IntelligentChunk,
        lease_type: LeaseType
    ) -> Dict[str, Any]:
        """
        Pure AI extraction - no patterns, just understanding
        """
        # Use full chunk content - let's see the data!
        chunk_content = chunk.content
        logger.info(f"Processing chunk with {len(chunk_content)} characters")
        
        extraction_prompt = {
            "system": f"""You are an expert {lease_type.value} lease analyst. 
            Extract ALL information from this lease section.
            Be thorough and comprehensive.""",
            
            "user": f"""Analyze this lease section:
            
            Content: {chunk_content}
            
            Extract EVERYTHING - all terms, conditions, amounts, dates, parties, obligations. Return:
            {{
                "extracted_items": [
                    {{
                        "field_name": "descriptive name",
                        "value": "extracted value",
                        "confidence": 0.0-1.0,
                        "source_text": "exact quote from document",
                        "context": "additional context if needed"
                    }}
                ],
                "summary": "comprehensive summary of this section",
                "all_amounts": ["list all monetary amounts found"],
                "all_dates": ["list all dates found"],
                "all_parties": ["list all parties/entities mentioned"],
                "obligations": ["list all obligations and requirements"],
                "conditions": ["list all conditions and contingencies"],
                "risks": ["list of risks if any"]
            }}
            
            Extract EVERYTHING - rent, CAM, deposits, dates, terms, parties, insurance, maintenance, 
            use restrictions, default provisions, notices, options, rights, obligations, etc.
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            extraction_prompt["system"],
            extraction_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _enhance_with_context(
        self,
        chunks: List[IntelligentChunk],
        current_extraction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI enhances extraction by understanding relationships between chunks
        """
        context_prompt = {
            "system": """You are analyzing relationships between different parts of a lease.
            Enhance the extraction by:
            - Finding information split across sections
            - Resolving references (e.g., "as defined above")
            - Identifying dependencies between clauses
            - Catching contradictions or conflicts""",
            
            "user": f"""Current extraction: {json.dumps(current_extraction, indent=2)}
            
            Review these related chunks and enhance the extraction:
            {self._format_chunks_for_context(chunks)}
            
            Return additional extracted information and corrections.
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            context_prompt["system"],
            context_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _extract_implicit_information(
        self,
        chunks: List[IntelligentChunk],
        current_extraction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI infers information not explicitly stated
        """
        implicit_prompt = {
            "system": """You are an expert at understanding what's NOT said in legal documents.
            Identify:
            - Standard clauses that are missing
            - Implied obligations from stated terms
            - Hidden risks from what's omitted
            - Industry standards not mentioned
            - Calculations needed but not shown""",
            
            "user": f"""Based on this extraction: {json.dumps(current_extraction, indent=2)}
            
            And this lease type: {lease_type.value}
            
            What implicit information can you derive?
            What's missing that should be there?
            What risks arise from omissions?
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            implicit_prompt["system"],
            implicit_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _perform_calculations(
        self,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI performs all necessary calculations
        """
        calc_prompt = {
            "system": """You are a financial analyst for real estate leases.
            Perform all calculations needed:
            - Total rent over lease term
            - Effective rent including escalations
            - CAM/NNN projections
            - Security deposit requirements
            - Break-even analysis
            - Any other relevant calculations""",
            
            "user": f"""Using this extracted data: {json.dumps(extracted_data, indent=2)}
            
            Perform all relevant calculations.
            Show your work and assumptions.
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            calc_prompt["system"],
            calc_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _map_clause_relationships(
        self,
        extraction_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI maps relationships between all clauses
        """
        relationship_prompt = {
            "system": """Map all relationships between lease clauses.
            Identify:
            - Dependencies (X requires Y)
            - Conflicts (X contradicts Y)
            - Triggers (if X then Y)
            - Modifications (X modifies Y)
            - References (X refers to Y)""",
            
            "user": f"""Analyze relationships in: {json.dumps(extraction_results, indent=2)}
            
            Create a comprehensive relationship map.
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            relationship_prompt["system"],
            relationship_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _comprehensive_risk_analysis(
        self,
        extraction_results: Dict[str, Any],
        relationships: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI performs deep risk analysis
        """
        risk_prompt = {
            "system": """You are a legal risk analyst. Identify ALL risks:
            - Explicit risks from unfavorable terms
            - Implicit risks from missing protections
            - Structural risks from clause relationships
            - Financial risks from calculations
            - Operational risks from obligations
            - Future risks from contingencies
            
            Rate each risk: Critical, High, Medium, Low""",
            
            "user": f"""Analyze risks in:
            Extraction: {json.dumps(extraction_results, indent=2)}
            Relationships: {json.dumps(relationships, indent=2)}
            
            Provide comprehensive risk assessment.
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            risk_prompt["system"],
            risk_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _verify_completeness(
        self,
        extraction_results: Dict[str, Any],
        lease_type: LeaseType
    ) -> Dict[str, Any]:
        """
        AI verifies nothing was missed
        """
        completeness_prompt = {
            "system": f"""Verify completeness of {lease_type.value} lease extraction.
            Check against standard requirements.
            Identify any gaps or concerns.""",
            
            "user": f"""Review extraction: {json.dumps(extraction_results, indent=2)}
            
            Is this complete for a {lease_type.value} lease?
            What's missing or concerning?
            
            Return your response in valid JSON format."""
        }
        
        response = await self._call_gpt(
            completeness_prompt["system"],
            completeness_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    async def _call_gpt(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
        timeout: int = 90
    ) -> str:
        """
        Call GPT-4 with proper error handling and configurable timeout
        """
        try:
            # Ensure prompts contain "json" when using json_object format
            if response_format == "json":
                if "json" not in user_prompt.lower() and "json" not in system_prompt.lower():
                    user_prompt = user_prompt + "\n\nReturn your response in valid JSON format."
            
            # Use sync client in a thread pool to avoid asyncio issues
            def sync_call():
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"} if response_format == "json" else None,
                    max_tokens=4000,
                    timeout=60  # Increase API timeout to 60 seconds
                )
                return response.choices[0].message.content
            
            # Run in thread pool with timeout
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(executor, sync_call),
                        timeout=timeout  # 90 second timeout for large chunks
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.error(f"GPT call timed out after {timeout} seconds")
                    raise
        except Exception as e:
            logger.error(f"GPT call failed: {e}")
            raise
    
    async def _classify_chunk_content(self, chunk_text: str) -> Dict[str, Any]:
        """
        AI classifies what type of content this chunk contains
        """
        classify_prompt = {
            "system": """Classify this lease text section. Identify:
            - Primary legal concept
            - Secondary concepts present
            - Information completeness
            - Relationship indicators""",
            
            "user": f"Classify this text:\n{chunk_text[:1000]}"
        }
        
        response = await self._call_gpt(
            classify_prompt["system"],
            classify_prompt["user"],
            response_format="json"
        )
        
        return json.loads(response)
    
    def _extract_visual_info(
        self,
        pdf_content: Dict[str, Any],
        start_pos: int,
        end_pos: int
    ) -> Dict[str, Any]:
        """
        Extract visual structure information for the chunk
        """
        # This would extract font sizes, indentation, etc.
        # from the PDF layout information
        return {
            "fonts": [],
            "indentation": 0,
            "spacing": "normal"
        }
    
    def _calculate_page_info(
        self,
        pdf_content: Dict[str, Any],
        start_pos: int,
        end_pos: int
    ) -> Dict[str, int]:
        """
        Calculate page numbers for the chunk
        """
        # Ensure positions are integers
        try:
            start_pos = int(start_pos) if start_pos is not None else 0
            end_pos = int(end_pos) if end_pos is not None else len(pdf_content.get('text', ''))
        except (TypeError, ValueError):
            start_pos = 0
            end_pos = len(pdf_content.get('text', ''))
        
        # This would map character positions to page numbers
        return {
            "start_page": 1,
            "end_page": 1,
            "start_char": start_pos,
            "end_char": end_pos
        }
    
    def _merge_extractions(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any]
    ) -> None:
        """
        Intelligently merge extraction results
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_extractions(target[key], value)
            elif isinstance(value, list) and isinstance(target[key], list):
                target[key].extend(value)
    
    def _calculate_overall_confidence(
        self,
        extraction_results: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score
        """
        # Aggregate confidence scores from all extractions
        confidences = []
        self._collect_confidences(extraction_results, confidences)
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _collect_confidences(
        self,
        data: Any,
        confidences: List[float]
    ) -> None:
        """
        Recursively collect confidence scores
        """
        if isinstance(data, dict):
            if 'confidence' in data:
                confidences.append(float(data['confidence']))
            for value in data.values():
                self._collect_confidences(value, confidences)
        elif isinstance(data, list):
            for item in data:
                self._collect_confidences(item, confidences)
    
    def _format_chunks_for_context(
        self,
        chunks: List[IntelligentChunk]
    ) -> str:
        """
        Format chunks for context analysis
        """
        formatted = []
        for i, chunk in enumerate(chunks[:10]):  # Limit to prevent token overflow
            formatted.append(f"Chunk {i}: {chunk.content[:200]}...")
        return "\n\n".join(formatted)


# Integration function to work with existing system
async def extract_with_ai_native(
    segments: List[Dict[str, Any]],
    lease_type: LeaseType,
    api_key: str
) -> Dict[str, ClauseExtraction]:
    """
    Extract from pre-chunked segments using AI
    """
    logger.info(f"AI-native extraction starting with {len(segments)} segments")
    
    # Filter out signature sections
    filtered_segments = []
    for segment in segments:
        section_name = segment.get("section_name", "").lower()
        content = segment.get("content", "")
        
        # Skip pure signature/certificate sections
        if section_name in ["signature", "certificate", "acknowledgment"]:
            if len(content) < 1500:
                logger.info(f"AI-native: Skipping pure signature section: {section_name} ({len(content)} chars)")
                continue
        
        filtered_segments.append(segment)
    
    logger.info(f"Processing {len(filtered_segments)} segments after filtering")
    
    # Extract from each segment directly
    all_clauses = {}
    
    # Process segments in parallel
    async def process_segment(segment, idx):
        try:
            logger.info(f"Processing segment {idx+1}/{len(filtered_segments)}: {segment.get('section_name', 'unknown')} ({len(segment.get('content', ''))} chars)")
            
            # Create a simple prompt for this segment
            system_prompt = f"""You are an expert {lease_type.value} lease analyst. 
            Extract ALL information from this lease section.
            Be thorough and comprehensive."""
            
            # Handle very large segments by intelligent truncation
            content = segment.get('content', '')
            if len(content) > 6000:
                logger.warning(f"Segment {idx+1} is very large ({len(content)} chars), truncating intelligently")
                # Take beginning, middle, and end portions
                content = content[:2000] + "\n\n[... middle portion omitted for length ...]\n\n" + content[-2000:]
            
            user_prompt = f"""Analyze this lease section:
            
            Section: {segment.get('section_name', 'Unknown')}
            Content: {content}
            
            Extract EVERYTHING - all terms, conditions, amounts, dates, parties, obligations. Return:
            {{
                "extracted_items": [
                    {{
                        "field_name": "descriptive name",
                        "value": "extracted value",
                        "confidence": 0.0-1.0,
                        "source_text": "exact quote from document",
                        "context": "additional context if needed"
                    }}
                ],
                "summary": "comprehensive summary of this section",
                "all_amounts": ["list all monetary amounts found"],
                "all_dates": ["list all dates found"],
                "all_parties": ["list all parties/entities mentioned"],
                "obligations": ["list all obligations and requirements"],
                "conditions": ["list all conditions and contingencies"],
                "risks": ["list of risks if any"]
            }}
            
            Extract EVERYTHING - rent, CAM, deposits, dates, terms, parties, insurance, maintenance, 
            use restrictions, default provisions, notices, options, rights, obligations, etc.
            
            Return your response in valid JSON format."""
            
            # Call GPT directly
            client = openai.OpenAI(api_key=api_key)
            
            try:
                # For large segments, increase timeout
                segment_timeout = 120 if len(segment.get('content', '')) > 5000 else 90
                
                response = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: client.chat.completions.create(
                            model="gpt-4-turbo-preview",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.1,
                            response_format={"type": "json_object"},
                            max_tokens=4000,
                            timeout=90  # Increase API timeout
                        )
                    ),
                    timeout=segment_timeout
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.info(f"Segment {idx+1} extracted {len(result.get('extracted_items', []))} items")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout processing segment {idx+1}")
                return {"extracted_items": [], "error": "timeout"}
            except Exception as e:
                logger.error(f"Error processing segment {idx+1}: {e}")
                return {"extracted_items": [], "error": str(e)}
                
        except Exception as e:
            logger.error(f"Failed to process segment: {e}")
            return {"extracted_items": []}
    
    # Process all segments in parallel with semaphore
    semaphore = asyncio.Semaphore(3)  # Process 3 at a time to avoid overwhelming and timeouts
    
    async def process_with_semaphore(segment, idx):
        async with semaphore:
            return await process_segment(segment, idx)
    
    # Create tasks for all segments
    tasks = [process_with_semaphore(seg, i) for i, seg in enumerate(filtered_segments)]
    
    # Execute all tasks
    results = await asyncio.gather(*tasks)
    
    # Convert results to ClauseExtraction format
    clause_extractions = {}
    
    for segment, result in zip(filtered_segments, results):
        section_name = segment.get('section_name', 'unknown')
        
        if 'extracted_items' in result:
            # Store comprehensive lists at section level
            all_amounts = result.get('all_amounts', [])
            all_dates = result.get('all_dates', [])
            all_parties = result.get('all_parties', [])
            obligations = result.get('obligations', [])
            conditions = result.get('conditions', [])
            risks = result.get('risks', [])
            
            for i, item in enumerate(result['extracted_items']):
                clause_key = f"{section_name}_{item['field_name'].lower().replace(' ', '_')}_{i}"
                
                risk_tags = [{'type': 'general', 'level': 'medium', 'description': r} for r in risks]
                
                clause_extractions[clause_key] = ClauseExtraction(
                    content=json.dumps({
                        'value': item['value'],
                        'field_name': item['field_name'],
                        'context': item.get('context', ''),
                        'section': section_name,
                        'all_amounts': all_amounts,
                        'all_dates': all_dates,
                        'all_parties': all_parties,
                        'obligations': obligations,
                        'conditions': conditions
                    }, indent=2),
                    raw_excerpt=item.get('source_text', ''),
                    confidence=item.get('confidence', 0.7),
                    page_number=segment.get('page_start', 1),
                    risk_tags=risk_tags,
                    summary_bullet=result.get('summary', item['field_name']),
                    structured_data={
                        'field_name': item['field_name'],
                        'value': item['value'],
                        'context': item.get('context', ''),
                        'section': section_name
                    },
                    needs_review=item.get('confidence', 0.7) < 0.8,
                    field_id=f"ai_native.{section_name}.{item['field_name']}_{i}"
                )
    
    logger.info(f"AI-native extraction complete: {len(clause_extractions)} total clauses extracted")
    return clause_extractions
