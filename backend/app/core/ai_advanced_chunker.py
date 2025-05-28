"""
AI-Native Advanced Chunking System

This module implements a truly intelligent chunking system that uses GPT-4
to understand document structure without any pattern matching.
"""

from typing import List, Dict, Any, Optional, Tuple
import json
import os
import asyncio
import time
from dataclasses import dataclass, field
import openai

from app.schemas import LeaseType
from app.utils.logger import logger


@dataclass
class AIChunk:
    """Represents an intelligently identified chunk"""
    content: str
    semantic_type: str  # AI's understanding of what this is
    importance: str  # high/medium/low
    relationships: List[str] = field(default_factory=list)
    visual_cues: Dict[str, Any] = field(default_factory=dict)
    page_info: Dict[str, int] = field(default_factory=dict)
    ai_analysis: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class AIAdvancedChunker:
    """
    Pure AI-driven chunking system.
    No patterns, no rules - just understanding.
    """
    
    def __init__(self, text_content: str, lease_type: LeaseType, api_key: str):
        self.text_content = text_content
        self.lease_type = lease_type
        self.api_key = api_key
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.chunks: List[AIChunk] = []
        
    async def process(self) -> List[Dict[str, Any]]:
        """
        Main processing pipeline - completely AI-driven
        """
        logger.info("Starting AI-native chunking process")
        
        try:
            # Phase 1: AI understands the document structure
            document_analysis = await self._analyze_document_structure()
            
            # Phase 2: AI determines optimal chunking strategy
            chunking_strategy = await self._determine_chunking_strategy(document_analysis)
            
            # Phase 3: AI creates semantic chunks
            raw_chunks = await self._create_semantic_chunks(chunking_strategy)
            
            # Phase 4: AI analyzes each chunk in context
            enriched_chunks = await self._enrich_chunks_with_context(raw_chunks)
            
            # Phase 5: AI identifies relationships
            final_chunks = await self._map_chunk_relationships(enriched_chunks)
            
            # Convert to expected format
            return self._format_chunks_for_output(final_chunks)
            
        except Exception as e:
            logger.error(f"AI chunking failed: {e}")
            # Fallback to simple chunking
            return await self._emergency_fallback()
    
    async def _analyze_document_structure(self) -> Dict[str, Any]:
        """
        Let AI analyze the entire document structure
        """
        # Sample the document intelligently
        doc_length = len(self.text_content)
        
        # Get samples from different parts
        samples = {
            "beginning": self.text_content[:2000],
            "middle": self.text_content[doc_length//2 - 1000:doc_length//2 + 1000],
            "end": self.text_content[-2000:] if doc_length > 2000 else "",
            "total_length": doc_length
        }
        
        prompt = {
            "system": """You are an expert legal document analyst specializing in lease agreements.
            Analyze the document structure WITHOUT using any patterns or rules.
            Understand what makes this document unique.""",
            
            "user": f"""Analyze this {self.lease_type.value} lease document:

Beginning:
{samples['beginning']}

Middle section:
{samples['middle']}

End:
{samples['end']}

Total document length: {samples['total_length']} characters

Provide a comprehensive analysis:
{{
    "document_type_confidence": 0.0-1.0,
    "structural_style": "describe the formatting style",
    "hierarchy_type": "flat/nested/mixed",
    "section_indicators": ["what indicates new sections"],
    "key_sections_identified": ["list of major sections you can identify"],
    "unique_characteristics": ["what makes this document special"],
    "recommended_chunking_approach": "how should we intelligently chunk this",
    "estimated_complexity": "simple/moderate/complex",
    "special_handling_needed": ["any special considerations"]
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        return json.loads(response)
    
    async def _determine_chunking_strategy(self, document_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI determines the best chunking strategy based on document analysis
        """
        prompt = {
            "system": """You are designing an optimal chunking strategy for a lease document.
            Create a strategy that preserves meaning and legal context.""",
            
            "user": f"""Based on this document analysis:
{json.dumps(document_analysis, indent=2)}

Design a chunking strategy:
{{
    "chunk_identification_method": "how to identify chunk boundaries",
    "target_chunk_size": "optimal size in characters",
    "boundary_markers": ["what indicates a chunk boundary"],
    "preserve_together": ["what content must stay together"],
    "special_sections": {{
        "section_name": {{
            "handling": "special handling instructions",
            "reason": "why this needs special handling"
        }}
    }},
    "context_overlap": "how much context to preserve between chunks",
    "priority_order": ["which sections are most important"]
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        return json.loads(response)
    
    async def _create_semantic_chunks(self, strategy: Dict[str, Any]) -> List[AIChunk]:
        """
        AI creates chunks based on semantic understanding
        """
        chunks = []
        
        # Let AI identify chunk boundaries
        chunk_boundaries = await self._identify_chunk_boundaries(strategy)
        
        # Create chunks from boundaries
        for i, boundary in enumerate(chunk_boundaries):
            chunk_content = self.text_content[boundary['start']:boundary['end']]
            
            # AI analyzes what this chunk is
            chunk_analysis = await self._analyze_chunk_content(
                chunk_content,
                context_before=self.text_content[max(0, boundary['start']-500):boundary['start']],
                context_after=self.text_content[boundary['end']:min(len(self.text_content), boundary['end']+500)]
            )
            
            chunk = AIChunk(
                content=chunk_content,
                semantic_type=chunk_analysis['semantic_type'],
                importance=chunk_analysis['importance'],
                visual_cues=chunk_analysis.get('visual_cues', {}),
                page_info=self._estimate_page_info(boundary['start'], boundary['end']),
                ai_analysis=chunk_analysis,
                confidence=chunk_analysis.get('confidence', 0.8)
            )
            
            chunks.append(chunk)
        
        return chunks
    
    async def _identify_chunk_boundaries(self, strategy: Dict[str, Any]) -> List[Dict[str, int]]:
        """
        AI identifies where chunks should be split
        """
        # Process document in windows to find boundaries
        window_size = 3000
        overlap = 500
        boundaries = []
        
        position = 0
        while position < len(self.text_content):
            window_end = min(position + window_size, len(self.text_content))
            window_text = self.text_content[position:window_end]
            
            # AI identifies boundaries in this window
            window_boundaries = await self._find_boundaries_in_window(
                window_text,
                window_start_position=position,
                strategy=strategy
            )
            
            boundaries.extend(window_boundaries)
            
            # Move to next window with overlap
            position = window_end - overlap
            if window_end >= len(self.text_content):
                break
        
        # Merge and clean up boundaries
        return self._clean_boundaries(boundaries)
    
    async def _find_boundaries_in_window(
        self, 
        window_text: str,
        window_start_position: int,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, int]]:
        """
        AI finds chunk boundaries within a text window
        """
        prompt = {
            "system": """You are identifying natural chunk boundaries in a legal document.
            Find where one complete legal concept ends and another begins.""",
            
            "user": f"""Using this strategy:
{json.dumps(strategy, indent=2)}

Find chunk boundaries in this text:
{window_text}

Return boundaries as:
{{
    "boundaries": [
        {{
            "relative_position": "character position within this window",
            "confidence": 0.0-1.0,
            "reason": "why this is a good boundary",
            "semantic_transition": "what changes at this boundary"
        }}
    ]
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        data = json.loads(response)
        
        # Convert relative positions to absolute
        boundaries = []
        for boundary in data.get('boundaries', []):
            boundaries.append({
                'start': window_start_position + boundary.get('relative_position', 0),
                'end': window_start_position + boundary.get('relative_position', 0),
                'confidence': boundary.get('confidence', 0.5),
                'reason': boundary.get('reason', ''),
                'semantic_transition': boundary.get('semantic_transition', '')
            })
        
        return boundaries
    
    async def _analyze_chunk_content(
        self,
        chunk_content: str,
        context_before: str = "",
        context_after: str = ""
    ) -> Dict[str, Any]:
        """
        AI deeply analyzes what a chunk contains
        """
        prompt = {
            "system": f"""You are analyzing a chunk from a {self.lease_type.value} lease.
            Understand what this chunk represents without using patterns.""",
            
            "user": f"""Analyze this chunk:

Context before: ...{context_before[-200:]}

CHUNK CONTENT:
{chunk_content}

Context after: {context_after[:200]}...

Provide analysis:
{{
    "semantic_type": "what kind of lease content this is",
    "importance": "high/medium/low",
    "key_concepts": ["main concepts discussed"],
    "legal_implications": ["what this means legally"],
    "extracted_values": {{
        "field": "value"
    }},
    "risks_identified": ["potential risks"],
    "missing_elements": ["what should be here but isn't"],
    "confidence": 0.0-1.0,
    "visual_cues": {{
        "formatting": "description of formatting",
        "structure": "how it's structured"
    }}
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        return json.loads(response)
    
    async def _enrich_chunks_with_context(self, chunks: List[AIChunk]) -> List[AIChunk]:
        """
        AI enriches chunks by understanding their context
        """
        enriched = []
        
        for i, chunk in enumerate(chunks):
            # Get surrounding chunks for context
            prev_chunk = chunks[i-1] if i > 0 else None
            next_chunk = chunks[i+1] if i < len(chunks)-1 else None
            
            # AI analyzes chunk in context
            contextual_analysis = await self._analyze_chunk_in_context(
                chunk,
                prev_chunk,
                next_chunk
            )
            
            # Merge analysis
            chunk.ai_analysis.update(contextual_analysis)
            
            # Update relationships
            if 'related_chunks' in contextual_analysis:
                chunk.relationships.extend(contextual_analysis['related_chunks'])
            
            enriched.append(chunk)
        
        return enriched
    
    async def _analyze_chunk_in_context(
        self,
        chunk: AIChunk,
        prev_chunk: Optional[AIChunk],
        next_chunk: Optional[AIChunk]
    ) -> Dict[str, Any]:
        """
        AI analyzes a chunk considering its neighbors
        """
        context = {
            "current": {
                "type": chunk.semantic_type,
                "summary": chunk.content[:200] + "..."
            }
        }
        
        if prev_chunk:
            context["previous"] = {
                "type": prev_chunk.semantic_type,
                "summary": prev_chunk.content[-200:] + "..."
            }
        
        if next_chunk:
            context["next"] = {
                "type": next_chunk.semantic_type,
                "summary": next_chunk.content[:200] + "..."
            }
        
        prompt = {
            "system": """Analyze how this chunk relates to its context.
            Identify references, dependencies, and connections.""",
            
            "user": f"""Analyze this chunk in context:
{json.dumps(context, indent=2)}

Current chunk full content:
{chunk.content}

Provide contextual analysis:
{{
    "references_previous": boolean,
    "references_next": boolean,
    "standalone_complete": boolean,
    "related_chunks": ["semantic types this relates to"],
    "cross_references": ["specific references found"],
    "contextual_meaning": "what this means in context",
    "enhanced_risk_assessment": ["risks considering context"]
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        return json.loads(response)
    
    async def _map_chunk_relationships(self, chunks: List[AIChunk]) -> List[AIChunk]:
        """
        AI maps relationships between all chunks
        """
        # Create a summary of all chunks
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_summaries.append({
                "index": i,
                "type": chunk.semantic_type,
                "importance": chunk.importance,
                "key_concepts": chunk.ai_analysis.get('key_concepts', []),
                "preview": chunk.content[:100] + "..."
            })
        
        # AI analyzes relationships
        relationships = await self._analyze_global_relationships(chunk_summaries)
        
        # Apply relationships to chunks
        for relationship in relationships:
            from_idx = relationship['from_chunk']
            to_idx = relationship['to_chunk']
            
            if 0 <= from_idx < len(chunks) and 0 <= to_idx < len(chunks):
                chunks[from_idx].relationships.append(f"chunk_{to_idx}:{relationship['relationship_type']}")
        
        return chunks
    
    async def _analyze_global_relationships(self, chunk_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        AI analyzes relationships across all chunks
        """
        prompt = {
            "system": """Identify all meaningful relationships between chunks.
            Look for dependencies, references, modifications, and logical connections.""",
            
            "user": f"""Analyze relationships between these chunks:
{json.dumps(chunk_summaries, indent=2)}

Return relationships:
{{
    "relationships": [
        {{
            "from_chunk": index,
            "to_chunk": index,
            "relationship_type": "depends_on/modifies/references/triggers/conflicts_with",
            "strength": "strong/medium/weak",
            "description": "explanation"
        }}
    ]
}}"""
        }
        
        response = await self._call_gpt(prompt["system"], prompt["user"])
        return json.loads(response).get('relationships', [])
    
    def _format_chunks_for_output(self, chunks: List[AIChunk]) -> List[Dict[str, Any]]:
        """
        Convert AI chunks to expected output format
        """
        formatted = []
        
        for i, chunk in enumerate(chunks):
            # Extract risk information
            risk_flags = []
            for risk in chunk.ai_analysis.get('risks_identified', []):
                risk_flags.append({
                    'risk_level': 'medium',  # Would be determined by AI
                    'description': risk
                })
            
            # Format for compatibility
            formatted_chunk = {
                'chunk_id': f'AI-{i+1:03d}',
                'content': chunk.content,
                'clause_hint': chunk.semantic_type,
                'risk_score': chunk.importance,
                'confidence': chunk.confidence,
                'justification': chunk.ai_analysis.get('contextual_meaning', ''),
                'page_start': chunk.page_info.get('start_page', 1),
                'page_end': chunk.page_info.get('end_page', 1),
                'char_start': chunk.page_info.get('start_char', 0),
                'char_end': chunk.page_info.get('end_char', len(chunk.content)),
                'parent_heading': '',  # AI doesn't use hierarchical headings
                'heading': chunk.semantic_type,
                'level': 1,
                'source_excerpt': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content,
                'matched_keywords': chunk.ai_analysis.get('key_concepts', []),
                'token_estimate': len(chunk.content) // 4,
                'is_table': 'table' in chunk.semantic_type.lower(),
                'risk_flags': risk_flags,
                'key_values': chunk.ai_analysis.get('extracted_values', {}),
                'gpt_enriched': True,
                'error_flag': False,
                'error_type': None,
                'truncated': False,
                'relationships': chunk.relationships
            }
            
            formatted.append(formatted_chunk)
        
        return formatted
    
    async def _call_gpt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call GPT-4 with proper error handling
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"GPT call failed: {e}")
            raise
    
    def _estimate_page_info(self, start_pos: int, end_pos: int) -> Dict[str, int]:
        """
        Estimate page information based on position
        """
        chars_per_page = 3000
        return {
            'start_page': (start_pos // chars_per_page) + 1,
            'end_page': (end_pos // chars_per_page) + 1,
            'start_char': start_pos,
            'end_char': end_pos
        }
    
    def _clean_boundaries(self, boundaries: List[Dict[str, int]]) -> List[Dict[str, int]]:
        """
        Clean and merge overlapping boundaries
        """
        if not boundaries:
            return []
        
        # Sort by start position
        sorted_boundaries = sorted(boundaries, key=lambda x: x['start'])
        
        # Merge overlapping boundaries
        cleaned = []
        current = sorted_boundaries[0]
        
        for boundary in sorted_boundaries[1:]:
            if boundary['start'] <= current['end'] + 100:  # Small overlap tolerance
                # Merge boundaries
                current['end'] = max(current['end'], boundary['end'])
                current['confidence'] = max(current['confidence'], boundary.get('confidence', 0.5))
            else:
                cleaned.append(current)
                current = boundary
        
        cleaned.append(current)
        
        # Convert to start/end pairs
        final_boundaries = []
        for i in range(len(cleaned)):
            if i < len(cleaned) - 1:
                final_boundaries.append({
                    'start': cleaned[i]['start'],
                    'end': cleaned[i+1]['start']
                })
            else:
                final_boundaries.append({
                    'start': cleaned[i]['start'],
                    'end': len(self.text_content)
                })
        
        return final_boundaries
    
    async def _emergency_fallback(self) -> List[Dict[str, Any]]:
        """
        Emergency fallback when AI chunking fails
        """
        logger.warning("Using emergency fallback chunking")
        
        # Simple fixed-size chunking
        chunk_size = 2000
        chunks = []
        
        for i in range(0, len(self.text_content), chunk_size):
            chunk_content = self.text_content[i:i+chunk_size]
            
            chunks.append({
                'chunk_id': f'FALLBACK-{i//chunk_size + 1:03d}',
                'content': chunk_content,
                'clause_hint': 'unknown',
                'risk_score': 'low',
                'confidence': 0.1,
                'justification': 'Emergency fallback - AI processing failed',
                'page_start': (i // 3000) + 1,
                'page_end': ((i + len(chunk_content)) // 3000) + 1,
                'char_start': i,
                'char_end': i + len(chunk_content),
                'parent_heading': '',
                'heading': f'Section {i//chunk_size + 1}',
                'level': 1,
                'source_excerpt': chunk_content[:200] + '...',
                'matched_keywords': [],
                'token_estimate': len(chunk_content) // 4,
                'is_table': False,
                'risk_flags': [],
                'key_values': {},
                'gpt_enriched': False,
                'error_flag': True,
                'error_type': 'ai_chunking_failed',
                'truncated': False,
                'relationships': []
            })
        
        return chunks


# Compatibility wrapper
class AdvancedChunker:
    """Wrapper for backward compatibility"""
    
    def __init__(self, text_content: str, lease_type: LeaseType):
        self.text_content = text_content
        self.lease_type = lease_type
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
    async def process(self) -> List[Dict[str, Any]]:
        """Process using AI-native chunking"""
        if not self.api_key:
            raise ValueError("OpenAI API key not found")
        
        chunker = AIAdvancedChunker(self.text_content, self.lease_type, self.api_key)
        return await chunker.process()
