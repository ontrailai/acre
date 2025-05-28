"""
Enhanced GPT Extraction Module with All Production Features

This is the updated extraction module that integrates all the new production-scale
features including multi-pass extraction, graph-based analysis, and specialized extractors.
"""

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
from app.core.document_graph import DocumentGraph, DocumentNode, DocumentType
from app.core.clause_graph import ClauseGraph, CrossDocumentClauseGraph
from app.core.multi_pass_extractor import MultiPassExtractor, DocumentLevelExtractor
from app.core.consistency_checker import ConsistencyChecker
from app.core.embedding_similarity import EmbeddingService, ClauseSimilarityFinder
from app.core.audit_trail import AuditTrail, PerformanceMonitor, DebugLogger
from app.core.ai_specialized_extractors import create_specialized_extractor
from app.core.table_extractor import TableExtractor
from app.core.ai_native_extractor import extract_with_ai_native

# Import original functions to maintain compatibility
from app.core.gpt_extract import (
    is_template_lease, detect_risk_tags, infer_clause_type,
    deduplicate_clauses, call_openai_api, _has_hierarchical_structure
)


class EnhancedLeaseExtractor:
    """
    Production-scale lease extraction system with all advanced features
    """
    
    def __init__(self, lease_type: LeaseType):
        self.lease_type = lease_type
        
        # Initialize all components
        self.multi_pass_extractor = MultiPassExtractor(lease_type)
        self.document_level_extractor = DocumentLevelExtractor()
        self.consistency_checker = ConsistencyChecker()
        self.embedding_service = EmbeddingService()
        self.similarity_finder = ClauseSimilarityFinder(self.embedding_service)
        self.table_extractor = TableExtractor()
        
        # Initialize tracking systems
        self.audit_trail = AuditTrail()
        self.performance_monitor = PerformanceMonitor()
        self.debug_logger = DebugLogger()
        
        # Document and clause graphs
        self.document_graph = None
        self.clause_graph = None
        
    async def extract_from_document_set(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract from a set of related documents (base lease, amendments, exhibits, etc.)
        
        Args:
            documents: List of document dictionaries with 'type', 'content', 'metadata'
            
        Returns:
            Comprehensive extraction results with cross-document analysis
        """
        start_time = time.time()
        
        # Initialize document graph
        self.document_graph = DocumentGraph()
        
        # Process each document
        all_results = {}
        
        for doc_info in documents:
            doc_id = doc_info.get("id", str(time.time()))
            doc_type = DocumentType[doc_info.get("type", "BASE_LEASE").upper()]
            
            # Start audit trail for document
            self.audit_trail.start_document_processing(
                doc_id, 
                doc_info.get("filename", "unknown"),
                len(doc_info.get("content", ""))
            )
            
            # Create document node
            doc_node = DocumentNode(
                doc_id=doc_id,
                doc_type=doc_type,
                title=doc_info.get("title", f"Document {doc_id}"),
                date=doc_info.get("date"),
                content=doc_info.get("content", "")
            )
            
            self.document_graph.add_document(doc_node)
            
            # Extract from individual document
            result = await self.extract_from_single_document(
                doc_info.get("content", ""),
                doc_info.get("segments", None),
                doc_id
            )
            
            all_results[doc_id] = result
            doc_node.extracted_data = result
            
        # Establish document relationships
        await self._establish_document_relationships(documents)
        
        # Perform cross-document analysis
        cross_doc_analysis = await self._analyze_across_documents(all_results)
        
        # Apply amendments if base lease exists
        current_states = {}
        for base_doc in self.document_graph.get_base_documents():
            current_state = self.document_graph.apply_amendments(base_doc.doc_id)
            current_states[base_doc.doc_id] = current_state
            
        # Final validation
        validation_results = {}
        for doc_id, state in current_states.items():
            validation = self.consistency_checker.validate_extraction(
                state.get("current_state", {}),
                self.document_graph
            )
            validation_results[doc_id] = validation
            
        # Export performance metrics
        processing_time = time.time() - start_time
        
        return {
            "individual_documents": all_results,
            "cross_document_analysis": cross_doc_analysis,
            "current_states": current_states,
            "validation_results": validation_results,
            "document_graph": self.document_graph.export_graph(),
            "processing_time": processing_time,
            "metrics": self.audit_trail.get_processing_stats()
        }
        
    async def extract_from_single_document(self, text_content: str, 
                                         segments: Optional[List[Dict[str, Any]]] = None,
                                         doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract from a single document with AI-native intelligence
        """
        if not doc_id:
            doc_id = str(time.time())
            
        # Segment if not provided
        if not segments:
            from app.core.segmenter import segment_lease
            segments = segment_lease(text_content, self.lease_type)
            
        # Save segments for debugging
        self.debug_logger.save_extraction_debug(doc_id, "segments", segments)
        
        # Use AI-native extraction with the already-segmented chunks
        logger.info(f"Using AI-native extraction for document {doc_id} with {len(segments)} pre-chunked segments")
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found")
            
        try:
            # Pass the segments directly to AI-native extraction
            # The segments are already well-chunked by the recursive chunker
            clauses = await extract_with_ai_native(segments, self.lease_type, api_key)
            logger.info(f"AI-native extraction found {len(clauses)} clauses")
        except Exception as e:
            logger.error(f"AI-native extraction failed: {e}")
            # Fallback to multi-pass if AI-native fails
            logger.info("Falling back to multi-pass extraction")
            clauses = await self.multi_pass_extractor.extract_with_multi_pass(segments)
                
        # Build clause graph
        self.clause_graph = ClauseGraph()
        for clause_id, clause in clauses.items():
            # Add to graph
            from app.core.clause_graph import ClauseNode as GraphClauseNode
            
            graph_node = GraphClauseNode(
                clause_id=clause_id,
                doc_id=doc_id,
                section_number=clause.field_id.split('.')[0] if clause.field_id else "",
                heading=clause_id.replace('_data', '').replace('_', ' ').title(),
                content=clause.raw_excerpt or "",
                clause_type=clause_id.split('_')[0],
                page_start=clause.page_number or 0,
                page_end=clause.page_number or 0,
                extracted_data=clause.structured_data or {},
                risk_score="high" if any(r.get("level") == "high" for r in clause.risk_tags) else "low",
                confidence=clause.confidence
            )
            
            self.clause_graph.add_clause(graph_node)
            
        # Build relationships in clause graph
        self.clause_graph.build_relationships()
        
        # Find similar clauses using embeddings
        await self.similarity_finder.index_clauses({
            clause_id: {
                "content": clause.raw_excerpt or "",
                "metadata": clause.structured_data
            }
            for clause_id, clause in clauses.items()
        })
        
        # Extract tables only if we have actual lease clauses
        # This prevents false positive table extraction in non-lease documents
        if len(clauses) > 5:  # Only extract tables if we found reasonable number of clauses
            tables = self.table_extractor.extract_tables_from_text(text_content)
            
            # Limit tables to reasonable number
            if len(tables) > 5:
                logger.warning(f"Found {len(tables)} tables, limiting to 5 most confident")
                tables.sort(key=lambda t: t.confidence, reverse=True)
                tables = tables[:5]
            
            for i, table in enumerate(tables):
                # Only add tables with reasonable confidence
                if table.confidence > 0.3:
                    table_key = f"table_{table.table_type}_{i}"
                    clauses[table_key] = ClauseExtraction(
                        content=json.dumps({"headers": table.headers, "rows": table.rows}),
                        raw_excerpt=f"Table: {table.table_type}",
                        confidence=table.confidence,
                        page_number=None,
                        risk_tags=[],
                        summary_bullet=f"{table.table_type} table extracted",
                        structured_data=table.metadata,
                        needs_review=table.confidence < 0.5,
                        field_id=table_key
                    )
        else:
            tables = []
            logger.info(f"Skipping table extraction due to low clause count ({len(clauses)} clauses found)")
            
        # Perform consistency validation
        validation_report = self.consistency_checker.validate_extraction(
            {k: v.structured_data for k, v in clauses.items() if v.structured_data}
        )
        
        # Log validation results
        self.audit_trail.log_validation_result(doc_id, validation_report.__dict__)
        
        # Extract document-level insights
        insights = await self.document_level_extractor.extract_document_insights(clauses)
        
        # Complete audit trail
        self.audit_trail.complete_document_processing(doc_id, success=True)
        
        return {
            "clauses": clauses,
            "validation": validation_report,
            "insights": insights,
            "clause_graph": self.clause_graph.export_clause_map(),
            "similar_clauses": self.similarity_finder.find_duplicate_clauses(),
            "outlier_clauses": self.similarity_finder.find_outlier_clauses(),
            "tables": [{"type": t.table_type, "data": t.rows, "confidence": t.confidence} for t in tables if t.confidence > 0.3]
        }
        
    async def _extract_clauses_enhanced(self, segments: List[Dict[str, Any]]) -> Dict[str, ClauseExtraction]:
        """
        Enhanced clause extraction with all production features
        """
        all_clauses = {}
        
        # Process segments in parallel with rate limiting
        semaphore = asyncio.Semaphore(5)
        tasks = []
        
        for segment in segments:
            task = self._process_segment_production(segment, semaphore)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, dict):
                all_clauses.update(result)
            elif isinstance(result, Exception):
                logger.error(f"Segment processing error: {result}")
                
        # Deduplicate and enhance
        all_clauses = deduplicate_clauses(all_clauses)
        
        return all_clauses
        
    async def _process_segment_production(self, segment: Dict[str, Any], 
                                        semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
        """
        Process segment with all production enhancements
        """
        async with semaphore:
            # Track performance
            op_id = self.performance_monitor.start_operation("segment_processing")
            
            try:
                # Get appropriate specialized extractor
                segment_type = self._determine_segment_type(segment)
                specialized_extractor = create_specialized_extractor(segment_type)
                
                # Extract using specialized extractor if available
                if specialized_extractor and segment_type:
                    try:
                        segment_content = segment.get("content", "")
                        result = None
                        
                        # Call the appropriate method based on extractor type
                        if segment_type == "financial":
                            # Try multiple financial extraction methods
                            if hasattr(specialized_extractor, 'extract_base_rent'):
                                result = specialized_extractor.extract_base_rent(segment_content)
                            if not result or not result.extracted_data:
                                if hasattr(specialized_extractor, 'extract_percentage_rent'):
                                    result = specialized_extractor.extract_percentage_rent(segment_content)
                            if not result or not result.extracted_data:
                                if hasattr(specialized_extractor, 'extract_cam_charges'):
                                    result = specialized_extractor.extract_cam_charges(segment_content)
                                    
                        elif segment_type == "datetime":
                            # Try multiple datetime extraction methods
                            if hasattr(specialized_extractor, 'extract_critical_dates'):
                                result = specialized_extractor.extract_critical_dates(segment_content)
                            if not result or not result.extracted_data:
                                if hasattr(specialized_extractor, 'extract_notice_periods'):
                                    result = specialized_extractor.extract_notice_periods(segment_content)
                                    
                        elif segment_type == "conditional":
                            # Try conditional extraction methods
                            if hasattr(specialized_extractor, 'extract_conditional_rights'):
                                result = specialized_extractor.extract_conditional_rights(segment_content)
                            if not result or not result.extracted_data:
                                if hasattr(specialized_extractor, 'extract_co_tenancy_provisions'):
                                    result = specialized_extractor.extract_co_tenancy_provisions(segment_content)
                                    
                        elif segment_type == "rights":
                            # Try rights extraction methods
                            if hasattr(specialized_extractor, 'extract_renewal_options'):
                                result = specialized_extractor.extract_renewal_options(segment_content)
                            if not result or not result.extracted_data:
                                if hasattr(specialized_extractor, 'extract_expansion_rights'):
                                    result = specialized_extractor.extract_expansion_rights(segment_content)
                        
                        # If specialized extraction succeeded, convert and return
                        if result and result.extracted_data:
                            return self._convert_specialized_result(result, segment)
                            
                    except Exception as e:
                        logger.warning(f"Specialized extractor failed for {segment_type}: {e}")
                        
                # Fall back to GPT extraction
                return await self._gpt_extract_segment(segment)
                
            except Exception as e:
                logger.error(f"Segment processing error: {e}")
                return {}
                
            finally:
                duration = self.performance_monitor.end_operation(op_id)
                logger.debug(f"Segment processed in {duration}ms")
                
    def _determine_segment_type(self, segment: Dict[str, Any]) -> Optional[str]:
        """Determine the type of segment for specialized extraction"""
        section_name = segment.get("section_name", "").lower()
        
        if any(term in section_name for term in ["rent", "payment", "financial"]):
            return "financial"
        elif any(term in section_name for term in ["date", "term", "commencement"]):
            return "datetime"
        elif any(term in section_name for term in ["condition", "contingent", "if"]):
            return "conditional"
        elif any(term in section_name for term in ["option", "right", "renewal"]):
            return "rights"
            
        return None
        
    def _convert_specialized_result(self, result, segment: Dict[str, Any]) -> Dict[str, ClauseExtraction]:
        """Convert specialized extractor result to ClauseExtraction"""
        clause_key = f"{segment.get('section_name', 'unknown')}_specialized"
        
        return {
            clause_key: ClauseExtraction(
                content=json.dumps(result.extracted_data),
                raw_excerpt=segment.get("content", "")[:500],
                confidence=result.confidence,
                page_number=segment.get("page_start"),
                risk_tags=[],
                summary_bullet=f"Extracted using specialized {self._determine_segment_type(segment)} extractor",
                structured_data=result.extracted_data,
                needs_review=result.confidence < 0.7,
                field_id=f"{segment['section_name']}.specialized"
            )
        }
        
    async def _gpt_extract_segment(self, segment: Dict[str, Any]) -> Dict[str, ClauseExtraction]:
        """GPT extraction with audit trail"""
        # Build prompt
        system_prompt = """You are an expert lease analyst. Extract all relevant clauses with high precision."""
        user_prompt = f"""Extract clauses from this section:
        
Section: {segment.get('section_name')}
Content: {segment.get('content', '')}

Return JSON with detected clauses, confidence scores, and risk flags."""

        # Track GPT call
        gpt_start = time.time()
        
        try:
            response = await call_openai_api(system_prompt, user_prompt)
            gpt_duration = int((time.time() - gpt_start) * 1000)
            
            # Log GPT interaction
            self.audit_trail.log_gpt_interaction(
                user_prompt, response, 
                tokens_used=len(user_prompt.split()) + len(response.split()) if response else 0,
                duration_ms=gpt_duration,
                success=bool(response)
            )
            
            # Process response
            if response:
                return self._process_gpt_response(response, segment)
            else:
                return {}
                
        except Exception as e:
            logger.error(f"GPT extraction error: {e}")
            self.audit_trail.log_gpt_interaction(
                user_prompt, "", 0, 0, success=False, error=str(e)
            )
            return {}
            
    def _process_gpt_response(self, response: str, segment: Dict[str, Any]) -> Dict[str, ClauseExtraction]:
        """Process GPT response into ClauseExtraction objects"""
        try:
            data = json.loads(response)
            clauses = {}
            
            for clause_data in data.get("clauses", []):
                clause_type = clause_data.get("type", "unknown")
                clause_key = f"{clause_type}_data"
                
                # Log extraction decision
                self.audit_trail.log_extraction_decision(
                    f"{segment.get('section_name')}_{clause_type}",
                    clause_data,
                    clause_data.get("reasoning", "GPT extraction"),
                    clause_data.get("confidence", 0.7)
                )
                
                clauses[clause_key] = ClauseExtraction(
                    content=json.dumps(clause_data.get("data", {})),
                    raw_excerpt=clause_data.get("excerpt", segment.get("content", "")[:200]),
                    confidence=clause_data.get("confidence", 0.7),
                    page_number=segment.get("page_start"),
                    risk_tags=clause_data.get("risk_flags", []),
                    summary_bullet=clause_data.get("summary", ""),
                    structured_data=clause_data.get("data", {}),
                    needs_review=clause_data.get("needs_review", False),
                    field_id=f"{segment['section_name']}.{clause_type}"
                )
                
            return clauses
            
        except Exception as e:
            logger.error(f"Error processing GPT response: {e}")
            return {}
            
    async def _establish_document_relationships(self, documents: List[Dict[str, Any]]):
        """Establish relationships between documents in the graph"""
        # This would analyze document content to determine relationships
        # For now, using metadata
        
        for doc in documents:
            if doc.get("amends"):
                # This document amends another
                from app.core.document_graph import DocumentRelationship, RelationshipType
                
                rel = DocumentRelationship(
                    source_id=doc.get("id"),
                    target_id=doc.get("amends"),
                    relationship_type=RelationshipType.AMENDS,
                    effective_date=doc.get("date"),
                    sections_affected=doc.get("sections_affected", [])
                )
                
                try:
                    self.document_graph.add_relationship(rel)
                except ValueError as e:
                    logger.warning(f"Could not establish relationship: {e}")
                    
    async def _analyze_across_documents(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-document analysis"""
        analysis = {
            "common_provisions": [],
            "conflicting_provisions": [],
            "missing_in_amendments": [],
            "cross_document_risks": []
        }
        
        # Find common provisions across documents
        if len(all_results) > 1:
            # Extract all clause types
            clause_types_by_doc = {}
            for doc_id, result in all_results.items():
                clause_types = set()
                for clause_key in result.get("clauses", {}).keys():
                    clause_type = clause_key.replace("_data", "")
                    clause_types.add(clause_type)
                clause_types_by_doc[doc_id] = clause_types
                
            # Find common clause types
            common_types = set.intersection(*clause_types_by_doc.values())
            analysis["common_provisions"] = list(common_types)
            
        return analysis


# Create wrapper function for backward compatibility
async def extract_clauses(segments: List[Dict[str, Any]], lease_type: LeaseType, use_ast: bool = True) -> Dict[str, ClauseExtraction]:
    """
    Backward compatible wrapper that uses the enhanced extraction system
    """
    extractor = EnhancedLeaseExtractor(lease_type)
    
    # Create a simple document
    doc_content = "\n\n".join(segment.get("content", "") for segment in segments)
    
    result = await extractor.extract_from_single_document(
        doc_content,
        segments,
        doc_id=f"lease_{int(time.time())}"
    )
    
    clauses = result.get("clauses", {})
    
    # If we still have no clauses, use simplified extraction directly
    if not clauses or len(clauses) < 2:
        logger.warning("Enhanced extraction failed, using simplified extraction directly")
        clauses = await extract_clauses_simple(segments, lease_type)
    
    return clauses
