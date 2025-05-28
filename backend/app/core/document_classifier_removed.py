"""
Document Type Classification Module

Classifies uploaded documents to determine the appropriate processing pipeline.
"""

import re
from typing import Dict, Tuple, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    LEASE = "lease"
    RENT_ROLL = "rent_roll"
    AMENDMENT = "amendment"
    PROPERTY_SUMMARY = "property_summary"
    FINANCIAL_STATEMENT = "financial_statement"
    UNKNOWN = "unknown"


class DocumentClassifier:
    """
    Classifies documents based on content analysis and pattern matching.
    """
    
    def __init__(self):
        # Define keywords and patterns for each document type
        self.document_patterns = {
            DocumentType.LEASE: {
                "required_keywords": ["landlord", "tenant", "lease", "premises"],
                "strong_indicators": [
                    "lease agreement", "lease term", "monthly rent", 
                    "security deposit", "commencement date", "expiration date",
                    "leased premises", "landlord and tenant", "base rent"
                ],
                "section_patterns": [
                    r"article\s+\d+", r"section\s+\d+\.\d+", 
                    r"rent\s+and\s+payment", r"use\s+of\s+premises"
                ],
                "min_score": 0.4
            },
            DocumentType.RENT_ROLL: {
                "required_keywords": ["tenant", "sq ft", "rent"],
                "strong_indicators": [
                    "tenant roster", "rent roll", "occupancy rate",
                    "square feet", "lease expiration", "monthly rent",
                    "total square feet", "occupied square feet"
                ],
                "section_patterns": [
                    r"tenant\s+name", r"suite\s+#", r"lease\s+start",
                    r"lease\s+end", r"base\s+rent"
                ],
                "min_score": 0.3
            },
            DocumentType.AMENDMENT: {
                "required_keywords": ["amendment", "lease", "modify"],
                "strong_indicators": [
                    "first amendment", "second amendment", "lease amendment",
                    "hereby amended", "modification to lease", "amends and restates",
                    "original lease", "amended as follows"
                ],
                "section_patterns": [
                    r"amendment\s+to\s+lease", r"whereas", r"now\s+therefore"
                ],
                "min_score": 0.5
            },
            DocumentType.PROPERTY_SUMMARY: {
                "required_keywords": ["property", "building", "square"],
                "strong_indicators": [
                    "property summary", "building information", "property details",
                    "cam allocation", "expense breakdown", "property management",
                    "total rentable", "common area maintenance"
                ],
                "section_patterns": [
                    r"property\s+information", r"building\s+details",
                    r"expense\s+summary"
                ],
                "min_score": 0.3
            },
            DocumentType.FINANCIAL_STATEMENT: {
                "required_keywords": ["income", "expense", "total"],
                "strong_indicators": [
                    "income statement", "profit and loss", "balance sheet",
                    "operating expenses", "net income", "gross revenue",
                    "financial statement", "year ended"
                ],
                "section_patterns": [
                    r"revenues?", r"expenses?", r"net\s+operating\s+income"
                ],
                "min_score": 0.4
            }
        }
        
    def classify_document(self, text_content: str, filename: Optional[str] = None) -> Tuple[DocumentType, float, Dict[str, any]]:
        """
        Classify a document based on its content.
        
        Args:
            text_content: The full text content of the document
            filename: Optional filename for additional context
            
        Returns:
            Tuple of (DocumentType, confidence_score, metadata)
        """
        # Normalize text for analysis
        normalized_text = text_content.lower()
        
        # Check filename hints if available
        filename_hint = self._check_filename_hints(filename) if filename else None
        
        