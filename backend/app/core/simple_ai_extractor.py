"""
Simple AI-Native Lease Extraction
Just chunk PDFs intelligently and extract structured data with GPT-4

No patterns, no complexity - just AI understanding
"""

import json
import asyncio
from typing import Dict, List, Any
import openai
from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger


class SimpleAIExtractor:
    """
    Dead simple AI extraction:
    1. Chunk the document intelligently
    2. Send chunks to GPT-4
    3. Return structured data
    """
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    async def extract(self, text: str, lease_type: LeaseType) -> Dict[str, ClauseExtraction]:
        """
        Main extraction - simple and direct
        """
        # Step 1: Chunk the document
        chunks = self._chunk_document(text)
        logger.info(f"Created {len(chunks)} chunks from document")
        
        # Step 2: Extract from each chunk in parallel
        results = await self._extract_from_chunks(chunks, lease_type)
        
        # Step 3: Convert to ClauseExtraction format
        return self._format_results(results)
    
    def _chunk_document(self, text: str) -> List[str]:
        """
        Simple intelligent chunking based on paragraphs and size
        """
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        max_chunk_size = 3000  # Keep chunks under 3KB for GPT
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Skip signature/certificate paragraphs
            if any(word in paragraph.lower()[:200] for word in ['signature', 'certificate', 'notary', 'executed']):
                continue
            
            # If adding this paragraph exceeds max size