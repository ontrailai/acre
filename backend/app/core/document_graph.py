"""
Document Graph System for Multi-Document Processing

This module implements a graph-based system for handling complex real estate
document relationships including amendments, exhibits, and related documents.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
import json
import uuid
from enum import Enum
import networkx as nx
from app.utils.logger import logger


class DocumentType(Enum):
    """Types of documents in the graph"""
    BASE_LEASE = "base_lease"
    AMENDMENT = "amendment"
    EXHIBIT = "exhibit"
    GUARANTY = "guaranty"
    SNDA = "snda"
    ESTOPPEL = "estoppel"
    ASSIGNMENT = "assignment"
    SUBLEASE = "sublease"
    SIDE_LETTER = "side_letter"
    MEMORANDUM = "memorandum"


class RelationshipType(Enum):
    """Types of relationships between documents"""
    AMENDS = "amends"
    EXHIBITS_TO = "exhibits_to"
    GUARANTEES = "guarantees"
    SUBORDINATES_TO = "subordinates_to"
    ASSIGNS = "assigns"
    SUBLEASES = "subleases"
    INCORPORATES = "incorporates"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"


@dataclass
class DocumentNode:
    """Represents a document in the graph"""
    doc_id: str
    doc_type: DocumentType
    title: str
    date: Optional[datetime] = None
    parties: List[str] = field(default_factory=list)
    content: Optional[str] = None
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    
    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = str(uuid.uuid4())


@dataclass
class DocumentRelationship:
    """Represents a relationship between documents"""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    effective_date: Optional[datetime] = None
    sections_affected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentGraph:
    """
    Manages relationships between multiple related real estate documents
    """
    
    def __init__(self):
        """Initialize the document graph"""
        self.graph = nx.DiGraph()
        self.documents: Dict[str, DocumentNode] = {}
        self.relationships: List[DocumentRelationship] = []
        self.defined_terms: Dict[str, Dict[str, Any]] = {}  # term -> {doc_id, definition, section}
        self.cross_references: List[Dict[str, Any]] = []
        
    def add_document(self, document: DocumentNode) -> str:
        """Add a document to the graph"""
        self.documents[document.doc_id] = document
        self.graph.add_node(document.doc_id, 
                          doc_type=document.doc_type.value,
                          title=document.title,
                          date=document.date)
        logger.info(f"Added document {document.doc_id}: {document.title}")
        return document.doc_id
        
    def add_relationship(self, relationship: DocumentRelationship):
        """Add a relationship between documents"""
        if relationship.source_id not in self.documents:
            raise ValueError(f"Source document {relationship.source_id} not found")
        if relationship.target_id not in self.documents:
            raise ValueError(f"Target document {relationship.target_id} not found")
            
        self.relationships.append(relationship)
        self.graph.add_edge(relationship.source_id, 
                           relationship.target_id,
                           relationship_type=relationship.relationship_type.value,
                           effective_date=relationship.effective_date,
                           sections_affected=relationship.sections_affected)
        
        logger.info(f"Added relationship: {relationship.source_id} {relationship.relationship_type.value} {relationship.target_id}")
        
    def get_base_documents(self) -> List[DocumentNode]:
        """Get all base lease documents"""
        return [doc for doc in self.documents.values() 
                if doc.doc_type == DocumentType.BASE_LEASE]
        
    def get_amendments_for_document(self, doc_id: str) -> List[DocumentNode]:
        """Get all amendments for a specific document in chronological order"""
        amendments = []
        for rel in self.relationships:
            if (rel.target_id == doc_id and 
                rel.relationship_type == RelationshipType.AMENDS):
                amendments.append(self.documents[rel.source_id])
        
        # Sort by date
        amendments.sort(key=lambda x: x.date or datetime.min)
        return amendments
        
    def get_document_chain(self, base_doc_id: str) -> List[DocumentNode]:
        """Get the complete chain of documents (base + amendments) in order"""
        base_doc = self.documents.get(base_doc_id)
        if not base_doc:
            return []
            
        chain = [base_doc]
        amendments = self.get_amendments_for_document(base_doc_id)
        chain.extend(amendments)
        
        return chain
        
    def apply_amendments(self, base_doc_id: str) -> Dict[str, Any]:
        """
        Apply all amendments to a base document and return the current state
        """
        chain = self.get_document_chain(base_doc_id)
        if not chain:
            return {}
            
        # Start with base document extracted data
        current_state = chain[0].extracted_data.copy()
        amendment_history = []
        
        # Apply each amendment in order
        for i, amendment in enumerate(chain[1:], 1):
            amendment_record = {
                "amendment_number": i,
                "doc_id": amendment.doc_id,
                "title": amendment.title,
                "date": amendment.date,
                "changes": []
            }
            
            # Find what sections this amendment affects
            for rel in self.relationships:
                if (rel.source_id == amendment.doc_id and 
                    rel.relationship_type == RelationshipType.AMENDS):
                    
                    for section in rel.sections_affected:
                        # Apply the amendment to the affected section
                        if section in amendment.extracted_data:
                            old_value = current_state.get(section)
                            new_value = amendment.extracted_data[section]
                            
                            current_state[section] = new_value
                            
                            amendment_record["changes"].append({
                                "section": section,
                                "old_value": old_value,
                                "new_value": new_value
                            })
            
            amendment_history.append(amendment_record)
        
        return {
            "current_state": current_state,
            "amendment_history": amendment_history,
            "base_document": base_doc_id,
            "total_amendments": len(chain) - 1
        }
        
    def find_defined_terms(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find all defined terms across all documents
        Returns a dictionary of term -> list of definitions (handling conflicts)
        """
        terms = {}
        
        for doc_id, document in self.documents.items():
            if "defined_terms" in document.extracted_data:
                for term, definition in document.extracted_data["defined_terms"].items():
                    if term not in terms:
                        terms[term] = []
                    
                    terms[term].append({
                        "doc_id": doc_id,
                        "doc_title": document.title,
                        "doc_type": document.doc_type.value,
                        "definition": definition,
                        "date": document.date
                    })
        
        # Sort definitions by date (most recent first)
        for term in terms:
            terms[term].sort(key=lambda x: x["date"] or datetime.min, reverse=True)
            
        return terms
        
    def find_cross_references(self) -> List[Dict[str, Any]]:
        """Find all cross-references between documents"""
        cross_refs = []
        
        for doc_id, document in self.documents.items():
            if "cross_references" in document.extracted_data:
                for ref in document.extracted_data["cross_references"]:
                    # Try to resolve the reference
                    target_doc = self._resolve_reference(ref["reference_text"])
                    
                    cross_refs.append({
                        "source_doc": doc_id,
                        "source_title": document.title,
                        "reference_text": ref["reference_text"],
                        "reference_type": ref.get("type", "unknown"),
                        "target_doc": target_doc,
                        "resolved": target_doc is not None
                    })
        
        self.cross_references = cross_refs
        return cross_refs
        
    def _resolve_reference(self, reference_text: str) -> Optional[str]:
        """Try to resolve a reference text to a document ID"""
        reference_lower = reference_text.lower()
        
        # Try to match by title
        for doc_id, doc in self.documents.items():
            if doc.title.lower() in reference_lower:
                return doc_id
                
        # Try to match by common patterns
        if "exhibit" in reference_lower:
            # Extract exhibit letter/number
            import re
            match = re.search(r'exhibit\s+([a-z0-9]+)', reference_lower, re.I)
            if match:
                exhibit_id = match.group(1)
                for doc_id, doc in self.documents.items():
                    if (doc.doc_type == DocumentType.EXHIBIT and 
                        exhibit_id in doc.title.lower()):
                        return doc_id
                        
        return None
        
    def validate_document_set(self) -> Dict[str, List[str]]:
        """
        Validate the document set for completeness and consistency
        """
        issues = {
            "missing_exhibits": [],
            "circular_amendments": [],
            "date_inconsistencies": [],
            "unresolved_references": [],
            "orphaned_documents": []
        }
        
        # Check for missing exhibits
        for doc_id, doc in self.documents.items():
            if "exhibit_references" in doc.extracted_data:
                for exhibit_ref in doc.extracted_data["exhibit_references"]:
                    if not self._resolve_reference(exhibit_ref):
                        issues["missing_exhibits"].append(f"{doc.title} references missing {exhibit_ref}")
        
        # Check for circular amendments
        for node in self.graph.nodes():
            if nx.has_path(self.graph, node, node):
                issues["circular_amendments"].append(f"Circular amendment chain detected involving {self.documents[node].title}")
        
        # Check date consistency
        for rel in self.relationships:
            if rel.relationship_type == RelationshipType.AMENDS:
                amending_doc = self.documents[rel.source_id]
                amended_doc = self.documents[rel.target_id]
                
                if (amending_doc.date and amended_doc.date and 
                    amending_doc.date < amended_doc.date):
                    issues["date_inconsistencies"].append(
                        f"{amending_doc.title} dated {amending_doc.date} cannot amend "
                        f"{amended_doc.title} dated {amended_doc.date}"
                    )
        
        # Check for unresolved references
        for ref in self.cross_references:
            if not ref["resolved"]:
                issues["unresolved_references"].append(
                    f"{ref['source_title']} contains unresolved reference: {ref['reference_text']}"
                )
        
        # Check for orphaned documents (no relationships)
        for doc_id in self.documents:
            if (self.graph.in_degree(doc_id) == 0 and 
                self.graph.out_degree(doc_id) == 0 and
                self.documents[doc_id].doc_type != DocumentType.BASE_LEASE):
                issues["orphaned_documents"].append(self.documents[doc_id].title)
        
        return issues
        
    def export_graph(self) -> Dict[str, Any]:
        """Export the graph structure for visualization"""
        nodes = []
        edges = []
        
        for doc_id, doc in self.documents.items():
            nodes.append({
                "id": doc_id,
                "label": doc.title,
                "type": doc.doc_type.value,
                "date": doc.date.isoformat() if doc.date else None
            })
        
        for rel in self.relationships:
            edges.append({
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.relationship_type.value,
                "sections_affected": rel.sections_affected
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_documents": len(self.documents),
                "total_relationships": len(self.relationships),
                "document_types": {doc_type.value: sum(1 for d in self.documents.values() if d.doc_type == doc_type) 
                                  for doc_type in DocumentType}
            }
        }
