"""
Multi-Pass Extraction System

This module implements a sophisticated multi-pass extraction approach that
first extracts structure and definitions, then uses that context for detailed extraction.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import asyncio
import json
from dataclasses import dataclass, field
from app.schemas import LeaseType, ClauseExtraction
from app.core.gpt_extract import call_openai_api
from app.core.specialized_extractors import (
    FinancialClauseExtractor, DateTimeExtractor, 
    ConditionalClauseExtractor, RightsAndOptionsExtractor
)
from app.core.table_extractor import TableExtractor
from app.utils.logger import logger


@dataclass
class StructuralContext:
    """Document structure and context from first pass"""
    document_outline: Dict[str, List[str]]  # Section hierarchy
    defined_terms: Dict[str, str]  # Term -> Definition
    party_names: Dict[str, str]  # Role -> Name (e.g., "Landlord" -> "ABC Corp")
    key_dates: Dict[str, str]  # Date type -> Date value
    cross_references: List[Dict[str, Any]]  # All cross-references found
    tables_found: List[Dict[str, Any]]  # Table locations and types
    exhibit_references: List[str]  # Referenced exhibits
    
    
class MultiPassExtractor:
    """
    Implements multi-pass extraction for complex documents
    """
    
    def __init__(self, lease_type: LeaseType):
        self.lease_type = lease_type
        self.financial_extractor = FinancialClauseExtractor()
        self.datetime_extractor = DateTimeExtractor()
        self.conditional_extractor = ConditionalClauseExtractor()
        self.rights_extractor = RightsAndOptionsExtractor()
        self.table_extractor = TableExtractor()
        
    async def extract_with_multi_pass(self, segments: List[Dict[str, Any]]) -> Dict[str, ClauseExtraction]:
        """
        Main multi-pass extraction method
        """
        logger.info("Starting multi-pass extraction")
        
        # Pre-filter segments to remove pure signature/certificate sections
        filtered_segments = []
        for segment in segments:
            section_name = segment.get("section_name", "").lower()
            content = segment.get("content", "")
            
            # Only skip pure signature/certificate sections
            if section_name == "signature" or section_name == "certificate":
                # Check if this is ONLY a signature section (very short)
                if len(content) < 1500:  # Pure signature sections are usually short
                    logger.info(f"Multi-pass: Pre-filtering pure signature section: {section_name} ({len(content)} chars)")
                    continue
            
            # Keep all other sections
            filtered_segments.append(segment)
        
        logger.info(f"Multi-pass: Filtered {len(segments)} segments down to {len(filtered_segments)}")
        
        if not filtered_segments:
            logger.warning("No segments left after filtering signatures/certificates")
            return {}
        
        # Pass 1: Extract structure and definitions
        structural_context = await self._extract_structure_and_definitions(filtered_segments)
        logger.info(f"Pass 1 complete: Found {len(structural_context.defined_terms)} defined terms")
        
        # Pass 2: Extract clauses with full context
        clauses = await self._extract_with_full_context(filtered_segments, structural_context)
        logger.info(f"Pass 2 complete: Extracted {len(clauses)} clauses")
        
        # Pass 3: Specialized extraction and enhancement
        enhanced_clauses = await self._specialized_extraction(clauses, filtered_segments, structural_context)
        logger.info(f"Pass 3 complete: Enhanced {len(enhanced_clauses)} clauses")
        
        # Pass 4: Cross-reference resolution and validation
        final_clauses = await self._resolve_and_validate(enhanced_clauses, structural_context)
        logger.info(f"Pass 4 complete: Validated {len(final_clauses)} clauses")
        
        return final_clauses
        
    async def _extract_structure_and_definitions(self, segments: List[Dict[str, Any]]) -> StructuralContext:
        """
        First pass: Extract document structure, definitions, and key context
        """
        context = StructuralContext(
            document_outline={},
            defined_terms={},
            party_names={},
            key_dates={},
            cross_references=[],
            tables_found=[],
            exhibit_references=[]
        )
        
        # Process each segment for structural information
        tasks = []
        segments_to_process = []  # Keep track of which segments we're processing
        
        for segment in segments:
            # Skip signature and certificate sections
            section_name = segment.get("section_name", "").lower()
            content_preview = segment.get("content", "")[:200].lower()
            
            skip_keywords = [
                "signature", "certificate", "acknowledgment", "notary",
                "witness", "executed", "signed", "seal", "attestation",
                "certification", "accuracy"
            ]
            
            if any(keyword in section_name for keyword in skip_keywords):
                logger.info(f"Skipping signature/certificate section in structure extraction: {section_name}")
                continue
                
            if any(keyword in content_preview for keyword in ["tenant signature", "landlord signature", "certificate of accuracy"]):
                logger.info(f"Skipping section with signature content in structure extraction: {section_name}")
                continue
                
            task = self._extract_segment_structure(segment)
            tasks.append(task)
            segments_to_process.append(segment)  # Track the segment
            
        results = await asyncio.gather(*tasks)
        
        # Combine results
        for segment, result in zip(segments_to_process, results):  # Use segments_to_process instead
            if result:
                # Add to document outline
                section = segment.get("section_name", "Unknown")
                context.document_outline[section] = result.get("subsections", [])
                
                # Merge defined terms
                context.defined_terms.update(result.get("defined_terms", {}))
                
                # Extract party names
                for party in result.get("parties", []):
                    role = party.get("role")
                    name = party.get("name")
                    if role and name:
                        context.party_names[role] = name
                        
                # Extract key dates
                context.key_dates.update(result.get("key_dates", {}))
                
                # Add cross-references
                context.cross_references.extend(result.get("cross_references", []))
                
                # Note table locations
                if result.get("contains_table"):
                    context.tables_found.append({
                        "section": section,
                        "table_type": result.get("table_type"),
                        "content": segment.get("content", "")
                    })
                    
                # Extract exhibit references
                context.exhibit_references.extend(result.get("exhibit_references", []))
                
        # Deduplicate
        context.exhibit_references = list(set(context.exhibit_references))
        
        return context
        
    async def _extract_segment_structure(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structural information from a segment"""
        
        prompt = f"""Analyze this lease segment for structural information and context.

Extract:
1. Document structure (subsections, hierarchy)
2. Defined terms with their definitions
3. Party names and roles
4. Key dates mentioned
5. Cross-references to other sections
6. Whether it contains a table and what type
7. References to exhibits or schedules

Segment: {segment.get('section_name', 'Unknown')}
Content: {segment.get('content', '')[:2000]}

Return JSON with these fields:
{{
    "subsections": ["list of subsection headings"],
    "defined_terms": {{"Term": "definition"}},
    "parties": [{{"role": "Landlord", "name": "ABC Corp"}}],
    "key_dates": {{"Commencement Date": "2024-01-01"}},
    "cross_references": [{{"type": "section", "reference": "Section 5.1"}}],
    "contains_table": true/false,
    "table_type": "rent_schedule/cam_allocation/etc",
    "exhibit_references": ["Exhibit A", "Schedule 1"]
}}

Return your response in valid JSON format."""

        response = await call_openai_api(
            "You are a legal document structure analyzer.",
            prompt
        )
        
        try:
            return json.loads(response) if response else {}
        except:
            return {}
            
    async def _extract_with_full_context(self, segments: List[Dict[str, Any]], 
                                       context: StructuralContext) -> Dict[str, ClauseExtraction]:
        """
        Second pass: Extract clauses with full context available
        """
        all_clauses = {}
        
        # Create enhanced prompts with context
        tasks = []
        semaphore = asyncio.Semaphore(5)  # Limit concurrency
        
        for segment in segments:
            # Skip signature and certificate sections
            section_name = segment.get("section_name", "").lower()
            content_preview = segment.get("content", "")[:200].lower()
            
            skip_keywords = [
                "signature", "certificate", "acknowledgment", "notary",
                "witness", "executed", "signed", "seal", "attestation",
                "certification", "accuracy"
            ]
            
            if any(keyword in section_name for keyword in skip_keywords):
                logger.info(f"Skipping signature/certificate section in context extraction: {section_name}")
                continue
                
            if any(keyword in content_preview for keyword in ["tenant signature", "landlord signature", "certificate of accuracy"]):
                logger.info(f"Skipping section with signature content in context extraction: {section_name}")
                continue
                
            task = self._extract_segment_with_context(segment, context, semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # Combine results
        for result in results:
            if result:
                all_clauses.update(result)
                
        return all_clauses
        
    async def _extract_segment_with_context(self, segment: Dict[str, Any],
                                          context: StructuralContext,
                                          semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
        """Extract clauses from segment using structural context"""
        async with semaphore:
            # Build context-aware prompt
            defined_terms_str = json.dumps(dict(list(context.defined_terms.items())[:10]))  # Limit size
            parties_str = json.dumps(context.party_names)
            
            system_prompt = f"""You are an expert lease analyst with knowledge of this document's structure.

Key Context:
- Defined Terms (partial): {defined_terms_str}
- Parties: {parties_str}
- Document has {len(context.document_outline)} main sections

When extracting clauses:
1. Use the actual party names, not generic "Landlord"/"Tenant"
2. Resolve defined terms to their definitions
3. Note any cross-references to other sections
4. Extract complete information even if split across paragraphs"""

            user_prompt = f"""Extract all lease clauses from this section.

Section: {segment.get('section_name', 'Unknown')}
Content: {segment.get('content', '')}

For each clause found, provide:
- Complete extracted data
- Confidence score
- Any cross-references
- Risk factors

Return your response in valid JSON format."""

            response = await call_openai_api(system_prompt, user_prompt)
            
            # Process response into ClauseExtraction objects
            return self._process_contextual_response(response, segment, context)
            
    def _process_contextual_response(self, response: str, segment: Dict[str, Any],
                                   context: StructuralContext) -> Dict[str, ClauseExtraction]:
        """Process GPT response with context enhancement"""
        clauses = {}
        
        try:
            data = json.loads(response) if response else {}
            
            for clause_data in data.get("clauses", []):
                # Enhance with party names
                if "party" in clause_data and clause_data["party"] in context.party_names:
                    clause_data["party_name"] = context.party_names[clause_data["party"]]
                    
                # Resolve defined terms
                content = clause_data.get("content", "")
                for term, definition in context.defined_terms.items():
                    if term in content:
                        clause_data.setdefault("resolved_terms", {})[term] = definition
                        
                # Create ClauseExtraction
                clause_key = f"{clause_data.get('type', 'unknown')}_data"
                clauses[clause_key] = ClauseExtraction(
                    content=json.dumps(clause_data),
                    raw_excerpt=clause_data.get("excerpt", ""),
                    confidence=clause_data.get("confidence", 0.7),
                    page_number=segment.get("page_start"),
                    risk_tags=clause_data.get("risk_tags", []),
                    summary_bullet=clause_data.get("summary", ""),
                    structured_data=clause_data,
                    needs_review=clause_data.get("needs_review", False),
                    field_id=f"{segment['section_name']}.{clause_data.get('type', 'unknown')}"
                )
                
        except Exception as e:
            logger.error(f"Error processing contextual response: {e}")
            
        return clauses
        
    async def _specialized_extraction(self, clauses: Dict[str, ClauseExtraction],
                                    segments: List[Dict[str, Any]],
                                    context: StructuralContext) -> Dict[str, ClauseExtraction]:
        """
        Third pass: Apply specialized extractors for complex clauses
        """
        enhanced_clauses = clauses.copy()
        
        # Extract tables
        for table_info in context.tables_found:
            tables = self.table_extractor.extract_tables_from_text(table_info["content"])
            
            for i, table in enumerate(tables):
                table_key = f"{table_info['section']}_{table.table_type}_table_{i}"
                enhanced_clauses[table_key] = ClauseExtraction(
                    content=json.dumps({
                        "headers": table.headers,
                        "rows": table.rows,
                        "metadata": table.metadata
                    }),
                    raw_excerpt=f"Table in {table_info['section']}",
                    confidence=table.confidence,
                    page_number=None,  # Would need to track this
                    risk_tags=[],
                    summary_bullet=f"{table.table_type} table with {len(table.rows)} rows",
                    structured_data={
                        "table_type": table.table_type,
                        "data": table.rows
                    },
                    needs_review=False,
                    field_id=table_key
                )
                
        # Apply specialized extractors to relevant clauses
        for key, clause in list(enhanced_clauses.items()):
            if "rent" in key or "financial" in key:
                result = self.financial_extractor.extract_base_rent(
                    clause.raw_excerpt if clause.raw_excerpt else ""
                )
                if result.extracted_data:
                    clause.structured_data.update(result.extracted_data)
                    clause.confidence = max(clause.confidence, result.confidence)
                    
            elif "date" in key or "term" in key:
                result = self.datetime_extractor.extract_critical_dates(
                    clause.raw_excerpt if clause.raw_excerpt else ""
                )
                if result.extracted_data:
                    clause.structured_data.update(result.extracted_data)
                    
            elif "condition" in key or "co_tenancy" in key:
                result = self.conditional_extractor.extract_conditional_rights(
                    clause.raw_excerpt if clause.raw_excerpt else ""
                )
                if result.extracted_data:
                    clause.structured_data.update(result.extracted_data)
                    
        return enhanced_clauses
        
    async def _resolve_and_validate(self, clauses: Dict[str, ClauseExtraction],
                                   context: StructuralContext) -> Dict[str, ClauseExtraction]:
        """
        Fourth pass: Resolve cross-references and validate consistency
        """
        # Build a map of section -> clauses
        section_clause_map = {}
        for key, clause in clauses.items():
            section = clause.field_id.split('.')[0] if clause.field_id else "Unknown"
            if section not in section_clause_map:
                section_clause_map[section] = []
            section_clause_map[section].append((key, clause))
            
        # Resolve cross-references
        for ref in context.cross_references:
            source_section = ref.get("source_section")
            target_section = ref.get("target_section")
            
            if source_section in section_clause_map and target_section in section_clause_map:
                # Link the clauses
                for key, clause in section_clause_map[source_section]:
                    if not hasattr(clause, 'cross_references'):
                        clause.cross_references = []
                    clause.cross_references.append({
                        "target_section": target_section,
                        "relationship": ref.get("type", "references")
                    })
                    
        # Validate date sequences
        all_dates = {}
        for key, clause in clauses.items():
            if clause.structured_data and isinstance(clause.structured_data, dict):
                for field, value in clause.structured_data.items():
                    if "date" in field.lower() and value:
                        all_dates[f"{key}.{field}"] = value
                        
        # Check date logic
        if "lease_commencement" in all_dates and "lease_expiration" in all_dates:
            # Add validation notes
            for key, clause in clauses.items():
                if "term" in key:
                    clause.validation_notes = self._validate_term_dates(all_dates)
                    
        return clauses
        
    def _validate_term_dates(self, dates: Dict[str, str]) -> List[str]:
        """Validate term-related dates"""
        notes = []
        
        # Simple validation logic
        if "lease_commencement" in dates and "rent_commencement" in dates:
            if dates["rent_commencement"] < dates["lease_commencement"]:
                notes.append("Warning: Rent commencement before lease commencement")
                
        return notes


class DocumentLevelExtractor:
    """
    Extracts document-level insights and relationships
    """
    
    def __init__(self):
        self.multi_pass_extractor = None
        
    async def extract_document_insights(self, all_clauses: Dict[str, ClauseExtraction]) -> Dict[str, Any]:
        """
        Extract high-level document insights from all clauses
        """
        insights = {
            "lease_structure": self._analyze_lease_structure(all_clauses),
            "financial_summary": self._create_financial_summary(all_clauses),
            "key_dates_timeline": self._create_timeline(all_clauses),
            "risk_profile": self._assess_risk_profile(all_clauses),
            "complexity_score": self._calculate_complexity_score(all_clauses)
        }
        
        return insights
        
    def _analyze_lease_structure(self, clauses: Dict[str, ClauseExtraction]) -> Dict[str, Any]:
        """Analyze overall lease structure"""
        structure = {
            "lease_type": "unknown",
            "is_gross_lease": False,
            "is_net_lease": False,
            "has_percentage_rent": False,
            "has_co_tenancy": False,
            "has_exclusive_use": False,
            "total_clauses": len(clauses)
        }
        
        # Determine lease type
        for key, clause in clauses.items():
            if clause.structured_data:
                if "cam" in key or "operating_expenses" in key:
                    structure["is_net_lease"] = True
                if "percentage_rent" in key:
                    structure["has_percentage_rent"] = True
                if "co_tenancy" in key:
                    structure["has_co_tenancy"] = True
                if "exclusive" in key:
                    structure["has_exclusive_use"] = True
                    
        # Determine overall lease type
        if structure["is_net_lease"]:
            structure["lease_type"] = "Triple Net (NNN)" if "insurance" in str(clauses) else "Net"
        else:
            structure["lease_type"] = "Gross"
            
        return structure
        
    def _create_financial_summary(self, clauses: Dict[str, ClauseExtraction]) -> Dict[str, Any]:
        """Create financial summary from all financial clauses"""
        summary = {
            "base_rent": None,
            "additional_rent": [],
            "total_estimated_rent": 0,
            "security_deposit": None,
            "rent_escalations": [],
            "percentage_rent": None
        }
        
        for key, clause in clauses.items():
            if clause.structured_data:
                data = clause.structured_data
                
                if "base_rent" in data:
                    summary["base_rent"] = data["base_rent"]
                    summary["total_estimated_rent"] += float(data["base_rent"]) if isinstance(data["base_rent"], (int, float)) else 0
                    
                if "cam" in data or "cam_estimate" in data:
                    cam_amount = data.get("cam") or data.get("cam_estimate")
                    summary["additional_rent"].append({
                        "type": "CAM",
                        "amount": cam_amount
                    })
                    
                if "escalations" in data:
                    summary["rent_escalations"] = data["escalations"]
                    
                if "security_deposit" in data:
                    summary["security_deposit"] = data["security_deposit"]
                    
                if "percentage_rent" in data:
                    summary["percentage_rent"] = data["percentage_rent"]
                    
        return summary
        
    def _create_timeline(self, clauses: Dict[str, ClauseExtraction]) -> List[Dict[str, Any]]:
        """Create timeline of key dates"""
        timeline = []
        
        for key, clause in clauses.items():
            if clause.structured_data:
                data = clause.structured_data
                
                # Extract all date fields
                for field, value in data.items():
                    if "date" in field.lower() and value:
                        timeline.append({
                            "date": value,
                            "event": field.replace("_", " ").title(),
                            "source": key
                        })
                        
        # Sort by date
        timeline.sort(key=lambda x: x["date"])
        
        return timeline
        
    def _assess_risk_profile(self, clauses: Dict[str, ClauseExtraction]) -> Dict[str, Any]:
        """Assess overall risk profile"""
        risk_profile = {
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "critical_risks": [],
            "overall_risk_level": "low"
        }
        
        for key, clause in clauses.items():
            if clause.risk_tags:
                for risk in clause.risk_tags:
                    risk_level = risk.get("level", "low")
                    
                    if risk_level == "high":
                        risk_profile["high_risk_count"] += 1
                        risk_profile["critical_risks"].append({
                            "clause": key,
                            "description": risk.get("description", "")
                        })
                    elif risk_level == "medium":
                        risk_profile["medium_risk_count"] += 1
                    else:
                        risk_profile["low_risk_count"] += 1
                        
        # Determine overall risk level
        if risk_profile["high_risk_count"] > 2:
            risk_profile["overall_risk_level"] = "high"
        elif risk_profile["high_risk_count"] > 0 or risk_profile["medium_risk_count"] > 5:
            risk_profile["overall_risk_level"] = "medium"
            
        return risk_profile
        
    def _calculate_complexity_score(self, clauses: Dict[str, ClauseExtraction]) -> int:
        """Calculate document complexity score (0-100)"""
        score = 0
        
        # Factor in number of clauses
        score += min(len(clauses) / 2, 30)  # Max 30 points for clause count
        
        # Factor in cross-references
        cross_ref_count = sum(1 for c in clauses.values() if hasattr(c, 'cross_references'))
        score += min(cross_ref_count * 2, 20)  # Max 20 points for cross-refs
        
        # Factor in conditional clauses
        conditional_count = sum(1 for k in clauses.keys() if 'condition' in k)
        score += min(conditional_count * 5, 20)  # Max 20 points for conditionals
        
        # Factor in financial complexity
        financial_count = sum(1 for k in clauses.keys() if any(f in k for f in ['rent', 'cam', 'percentage', 'escalation']))
        score += min(financial_count * 3, 20)  # Max 20 points for financial
        
        # Factor in tables
        table_count = sum(1 for k in clauses.keys() if 'table' in k)
        score += min(table_count * 5, 10)  # Max 10 points for tables
        
        return int(min(score, 100))
