"""
Document validation and type detection module.

Determines if a document is actually a lease vs other real estate documents.
"""

from typing import Dict, List, Tuple, Optional, Any
import re
from app.utils.logger import logger


class DocumentValidator:
    """
    Validates documents and determines their type before processing.
    """
    
    def __init__(self):
        # Key patterns that indicate a lease document
        self.lease_indicators = [
            # Strong indicators (must have at least 2)
            (r'\b(lease\s+agreement|lease\s+term|leased\s+premises)\b', 2.0),
            (r'\b(landlord|lessor)\b', 1.5),
            (r'\b(tenant|lessee)\b', 1.5),
            (r'\b(monthly\s+rent|base\s+rent|minimum\s+rent)\b', 1.5),
            (r'\b(commencement\s+date|expiration\s+date|lease\s+expiration)\b', 1.5),
            (r'\b(security\s+deposit|damage\s+deposit)\b', 1.0),
            (r'\b(leased\s+space|demised\s+premises)\b', 1.0),
            
            # Medium indicators
            (r'\barticle\s+\d+\b', 0.5),
            (r'\bsection\s+\d+\.\d+\b', 0.5),
            (r'\b(maintenance|repairs|alterations)\b', 0.5),
            (r'\b(insurance\s+requirements|liability\s+insurance)\b', 0.5),
            (r'\b(assignment|subletting|sublet)\b', 0.5),
            (r'\b(default|remedies|breach)\b', 0.5),
        ]
        
        # Patterns that indicate other document types
        self.non_lease_indicators = {
            'rent_roll': [
                (r'\b(tenant\s+roster|rent\s+roll|occupancy\s+report)\b', 3.0),
                (r'\b(total\s+square\s+feet|occupied\s+square\s+feet)\b', 2.0),
                (r'\b(occupancy\s+rate|vacancy\s+rate)\b', 2.0),
                (r'(?:tenant|suite|unit)\s+\d+.*sq\s*ft', 1.5),
            ],
            'property_summary': [
                (r'\b(property\s+summary|building\s+summary|asset\s+summary)\b', 3.0),
                (r'\b(cam\s+allocation|expense\s+breakdown)\b', 2.0),
                (r'\b(operating\s+expenses|property\s+management)\b', 1.5),
            ],
            'financial_statement': [
                (r'\b(income\s+statement|profit\s+and\s+loss|p&l)\b', 3.0),
                (r'\b(balance\s+sheet|cash\s+flow)\b', 3.0),
                (r'\b(year\s+ended|quarter\s+ended)\b', 2.0),
            ]
        }
        
        # Minimum score thresholds
        self.min_lease_score = 5.0
        self.max_non_lease_score = 4.0
        
    def validate_document(self, text: str, filename: Optional[str] = None) -> Tuple[bool, str, float, List[str]]:
        """
        Validate if a document is a lease and determine its type.
        
        Args:
            text: Document text content
            filename: Optional filename for additional context
            
        Returns:
            Tuple of (is_lease, document_type, confidence, warnings)
        """
        if not text or len(text.strip()) < 100:
            return False, "empty", 0.0, ["Document appears to be empty or too short"]
            
        # Normalize text for analysis
        text_lower = text.lower()
        
        # Calculate lease score
        lease_score = 0.0
        matched_patterns = []
        
        for pattern, weight in self.lease_indicators:
            if re.search(pattern, text_lower, re.IGNORECASE):
                lease_score += weight
                matched_patterns.append(pattern)
                
        # Check for non-lease document types
        non_lease_scores = {}
        for doc_type, patterns in self.non_lease_indicators.items():
            score = 0.0
            for pattern, weight in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += weight
            non_lease_scores[doc_type] = score
            
        # Determine document type
        max_non_lease_type = max(non_lease_scores.items(), key=lambda x: x[1])
        max_non_lease_score = max_non_lease_type[1]
        
        warnings = []
        
        # Decision logic
        if max_non_lease_score > self.max_non_lease_score:
            # This is likely NOT a lease
            is_lease = False
            document_type = max_non_lease_type[0]
            confidence = min(max_non_lease_score / 10.0, 0.95)
            warnings.append(f"Document appears to be a {document_type.replace('_', ' ')} rather than a lease")
            
        elif lease_score >= self.min_lease_score:
            # This is likely a lease
            is_lease = True
            document_type = "lease"
            confidence = min(lease_score / 15.0, 0.95)
            
        else:
            # Uncertain - could be a partial lease or other document
            is_lease = False
            document_type = "unknown"
            confidence = 0.3
            warnings.append("Document does not contain enough lease-specific language")
            warnings.append(f"Lease score: {lease_score:.1f} (minimum required: {self.min_lease_score})")
            
        # Add specific warnings based on content
        if is_lease:
            # Check for completeness
            essential_terms = [
                ("tenant", "tenant name"),
                ("landlord", "landlord name"),
                ("rent", "rent amount"),
                ("term", "lease term"),
                ("premises", "premises description")
            ]
            
            missing_terms = []
            for term, description in essential_terms:
                if not re.search(rf'\b{term}\b', text_lower):
                    missing_terms.append(description)
                    
            if missing_terms:
                warnings.append(f"Missing essential terms: {', '.join(missing_terms)}")
                
        # Check for template indicators
        template_indicators = [
            r'\[.*?\]',  # Brackets
            r'\{.*?\}',  # Braces
            r'___+',     # Underscores
            r'\binsert\s+here\b',
            r'\bto\s+be\s+determined\b',
            r'\btbd\b'
        ]
        
        template_count = sum(1 for pattern in template_indicators 
                           if re.search(pattern, text_lower))
        
        if template_count >= 3:
            warnings.append("Document appears to be a template with unfilled fields")
            
        logger.info(f"Document validation: is_lease={is_lease}, type={document_type}, "
                   f"confidence={confidence:.2f}, lease_score={lease_score:.1f}")
        
        return is_lease, document_type, confidence, warnings
        
    def suggest_processing_method(self, document_type: str) -> str:
        """
        Suggest the appropriate processing method based on document type.
        
        Args:
            document_type: The detected document type
            
        Returns:
            Suggested processing method description
        """
        suggestions = {
            'lease': "Process with lease extraction pipeline",
            'rent_roll': "Use rent roll parser to extract tenant information and occupancy data",
            'property_summary': "Extract property metrics and financial summaries",
            'financial_statement': "Parse financial data and key metrics",
            'unknown': "Manual review recommended - document type unclear",
            'empty': "Document appears to be empty or corrupted"
        }
        
        return suggestions.get(document_type, "Manual review recommended")
        
    def extract_basic_info(self, text: str) -> Dict[str, Any]:
        """
        Extract basic information that might help identify the document.
        
        Args:
            text: Document text
            
        Returns:
            Dictionary of extracted basic information
        """
        info = {
            'page_count': len(re.findall(r'page\s+\d+|^\d+$', text, re.MULTILINE)),
            'has_tables': bool(re.search(r'\|.*\|.*\|', text)),
            'has_monetary_values': bool(re.search(r'\$[\d,]+', text)),
            'has_dates': bool(re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text)),
            'has_addresses': bool(re.search(r'\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|blvd|boulevard)', text, re.IGNORECASE)),
            'word_count': len(text.split()),
            'line_count': len(text.splitlines())
        }
        
        # Try to extract property name
        property_match = re.search(r'(?:property|building|center|plaza|tower|park):\s*([^\n]+)', text, re.IGNORECASE)
        if property_match:
            info['property_name'] = property_match.group(1).strip()
            
        return info
