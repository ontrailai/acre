"""
Clause Graph System for Complex Clause Relationships

This module implements a graph-based system for understanding relationships
between clauses within and across documents.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
import re
import networkx as nx
from enum import Enum
from app.utils.logger import logger


class ClauseRelationType(Enum):
    """Types of relationships between clauses"""
    CROSS_REFERENCE = "cross_reference"
    MODIFIES = "modifies"
    DEPENDS_ON = "depends_on"
    INCORPORATES = "incorporates"
    CONFLICTS_WITH = "conflicts_with"
    SUPERSEDES = "supersedes"
    TRIGGERS = "triggers"
    EXCLUDES = "excludes"
    SUBJECT_TO = "subject_to"


@dataclass
class ClauseNode:
    """Represents a clause in the graph"""
    clause_id: str
    doc_id: str
    section_number: str
    heading: str
    content: str
    clause_type: str
    page_start: int
    page_end: int
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    risk_score: str = "low"
    confidence: float = 0.0
    
    def get_key(self) -> str:
        """Get a unique key for this clause"""
        return f"{self.doc_id}:{self.clause_id}"


@dataclass
class ClauseRelationship:
    """Represents a relationship between clauses"""
    source_clause_id: str
    target_clause_id: str
    relationship_type: ClauseRelationType
    strength: float = 1.0  # How strong/certain the relationship is
    context: str = ""  # Text that establishes the relationship
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClauseGraph:
    """
    Manages relationships between clauses to understand document structure
    """
    
    def __init__(self):
        """Initialize the clause graph"""
        self.graph = nx.DiGraph()
        self.clauses: Dict[str, ClauseNode] = {}
        self.relationships: List[ClauseRelationship] = []
        self.reference_patterns = [
            # Cross-references
            (r'(?:as defined in|pursuant to|subject to|in accordance with)\s+Section\s+(\d+(?:\.\d+)*)', 
             ClauseRelationType.CROSS_REFERENCE),
            (r'(?:as set forth in|as provided in|as described in)\s+Section\s+(\d+(?:\.\d+)*)',
             ClauseRelationType.CROSS_REFERENCE),
            
            # Modifications
            (r'(?:notwithstanding|except as provided in|modified by)\s+Section\s+(\d+(?:\.\d+)*)',
             ClauseRelationType.MODIFIES),
            
            # Dependencies
            (r'(?:contingent upon|dependent on|requires compliance with)\s+Section\s+(\d+(?:\.\d+)*)',
             ClauseRelationType.DEPENDS_ON),
            
            # Incorporations
            (r'(?:incorporating|including by reference)\s+Section\s+(\d+(?:\.\d+)*)',
             ClauseRelationType.INCORPORATES),
            
            # Subject to
            (r'(?:subject to the terms of|subject to)\s+Section\s+(\d+(?:\.\d+)*)',
             ClauseRelationType.SUBJECT_TO)
        ]
        
    def add_clause(self, clause: ClauseNode) -> str:
        """Add a clause to the graph"""
        key = clause.get_key()
        self.clauses[key] = clause
        self.graph.add_node(key,
                           section=clause.section_number,
                           heading=clause.heading,
                           clause_type=clause.clause_type,
                           risk_score=clause.risk_score)
        return key
        
    def add_relationship(self, relationship: ClauseRelationship):
        """Add a relationship between clauses"""
        self.relationships.append(relationship)
        self.graph.add_edge(relationship.source_clause_id,
                           relationship.target_clause_id,
                           relationship_type=relationship.relationship_type.value,
                           strength=relationship.strength)
        
    def extract_relationships(self, clause: ClauseNode) -> List[ClauseRelationship]:
        """Extract relationships from clause content"""
        relationships = []
        content_lower = clause.content.lower()
        
        for pattern, rel_type in self.reference_patterns:
            for match in re.finditer(pattern, content_lower, re.IGNORECASE):
                ref_section = match.group(1)
                context = clause.content[max(0, match.start()-50):min(len(clause.content), match.end()+50)]
                
                # Try to find the target clause
                target_clause = self._find_clause_by_section(clause.doc_id, ref_section)
                
                if target_clause:
                    rel = ClauseRelationship(
                        source_clause_id=clause.get_key(),
                        target_clause_id=target_clause.get_key(),
                        relationship_type=rel_type,
                        context=context,
                        strength=0.9 if target_clause else 0.5
                    )
                    relationships.append(rel)
                    
        return relationships
        
    def _find_clause_by_section(self, doc_id: str, section_number: str) -> Optional[ClauseNode]:
        """Find a clause by document ID and section number"""
        for clause_key, clause in self.clauses.items():
            if (clause.doc_id == doc_id and 
                clause.section_number == section_number):
                return clause
        return None
        
    def build_relationships(self):
        """Build all relationships between clauses"""
        for clause in self.clauses.values():
            relationships = self.extract_relationships(clause)
            for rel in relationships:
                self.add_relationship(rel)
                
        logger.info(f"Built {len(self.relationships)} clause relationships")
        
    def find_hub_clauses(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Find 'hub' clauses that are referenced by many others
        Uses PageRank algorithm
        """
        if not self.graph.nodes() or not self.graph.edges():
            logger.warning("Graph is empty or has no edges for hub detection")
            return []
            
        try:
            pagerank = nx.pagerank(self.graph)
            sorted_clauses = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            
            return [(clause_id, self.graph.in_degree(clause_id)) 
                    for clause_id, _ in sorted_clauses[:top_n]]
        except Exception as e:
            logger.error(f"Error in PageRank calculation: {e}")
            # Fallback: return nodes sorted by in-degree
            return sorted([(node, self.graph.in_degree(node)) for node in self.graph.nodes()],
                         key=lambda x: x[1], reverse=True)[:top_n]
        
    def find_clause_clusters(self) -> List[Set[str]]:
        """
        Find clusters of highly interconnected clauses
        """
        # Check if graph is empty or too small
        if len(self.graph.nodes()) < 2 or len(self.graph.edges()) == 0:
            logger.warning("Graph is too small for community detection")
            # Return each node as its own cluster
            return [{node} for node in self.graph.nodes()]
        
        try:
            # Convert to undirected for community detection
            undirected = self.graph.to_undirected()
            
            # Find communities
            communities = list(nx.community.greedy_modularity_communities(undirected))
            
            return [set(community) for community in communities]
        except Exception as e:
            logger.error(f"Error in community detection: {e}")
            # Fallback: return each node as its own cluster
            return [{node} for node in self.graph.nodes()]
        
    def get_clause_dependencies(self, clause_id: str, 
                               depth: int = 2) -> Dict[str, Set[str]]:
        """
        Get all clauses that a given clause depends on (recursive)
        """
        dependencies = {
            "direct": set(),
            "indirect": set()
        }
        
        if clause_id not in self.graph:
            return dependencies
            
        # Direct dependencies
        for successor in self.graph.successors(clause_id):
            edge_data = self.graph[clause_id][successor]
            if edge_data.get("relationship_type") in [
                ClauseRelationType.DEPENDS_ON.value,
                ClauseRelationType.SUBJECT_TO.value,
                ClauseRelationType.INCORPORATES.value
            ]:
                dependencies["direct"].add(successor)
        
        # Indirect dependencies (up to specified depth)
        if depth > 1:
            for dep_clause in dependencies["direct"]:
                sub_deps = self.get_clause_dependencies(dep_clause, depth - 1)
                dependencies["indirect"].update(sub_deps["direct"])
                dependencies["indirect"].update(sub_deps["indirect"])
                
        return dependencies
        
    def find_conflicting_clauses(self) -> List[Tuple[ClauseNode, ClauseNode, str]]:
        """
        Find potentially conflicting clauses based on content analysis
        """
        conflicts = []
        
        # Group clauses by type
        clause_groups = {}
        for clause in self.clauses.values():
            if clause.clause_type not in clause_groups:
                clause_groups[clause.clause_type] = []
            clause_groups[clause.clause_type].append(clause)
        
        # Check for conflicts within each type
        for clause_type, clauses in clause_groups.items():
            for i, clause1 in enumerate(clauses):
                for clause2 in clauses[i+1:]:
                    conflict_reason = self._check_conflict(clause1, clause2)
                    if conflict_reason:
                        conflicts.append((clause1, clause2, conflict_reason))
                        
        return conflicts
        
    def _check_conflict(self, clause1: ClauseNode, clause2: ClauseNode) -> Optional[str]:
        """Check if two clauses conflict"""
        # Example conflict detection logic
        data1 = clause1.extracted_data
        data2 = clause2.extracted_data
        
        # Check for conflicting monetary amounts
        if "amount" in data1 and "amount" in data2:
            if data1["amount"] != data2["amount"]:
                return f"Conflicting amounts: {data1['amount']} vs {data2['amount']}"
                
        # Check for conflicting dates
        if "effective_date" in data1 and "effective_date" in data2:
            if data1["effective_date"] != data2["effective_date"]:
                return f"Conflicting dates: {data1['effective_date']} vs {data2['effective_date']}"
                
        # Check for conflicting obligations
        if clause1.clause_type == "obligation" and clause2.clause_type == "obligation":
            if "party" in data1 and "party" in data2:
                if data1["party"] == data2["party"] and data1.get("action") == data2.get("action"):
                    if data1.get("prohibited") != data2.get("prohibited"):
                        return "Conflicting obligations for same party and action"
                        
        return None
        
    def get_reading_order(self) -> List[str]:
        """
        Determine optimal reading order based on dependencies
        Uses topological sort
        """
        if not self.graph.nodes():
            return []
            
        try:
            return list(nx.topological_sort(self.graph))
        except (nx.NetworkXUnfeasible, nx.NetworkXError) as e:
            # Graph has cycles or other issues, fall back to degree-based ordering
            logger.warning(f"Cannot determine topological order: {e}, using degree-based ordering")
            return sorted(self.graph.nodes(), 
                         key=lambda x: (self.graph.in_degree(x), self.graph.out_degree(x)))
            
    def export_clause_map(self) -> Dict[str, Any]:
        """Export clause relationships for visualization"""
        nodes = []
        edges = []
        
        for clause_id, clause in self.clauses.items():
            nodes.append({
                "id": clause_id,
                "label": f"{clause.section_number}: {clause.heading}",
                "type": clause.clause_type,
                "risk_score": clause.risk_score,
                "doc_id": clause.doc_id
            })
            
        for rel in self.relationships:
            edges.append({
                "source": rel.source_clause_id,
                "target": rel.target_clause_id,
                "type": rel.relationship_type.value,
                "strength": rel.strength
            })
            
        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": [list(cluster) for cluster in self.find_clause_clusters()],
            "hub_clauses": self.find_hub_clauses(),
            "reading_order": self.get_reading_order()
        }


class CrossDocumentClauseGraph(ClauseGraph):
    """
    Extended clause graph that handles relationships across multiple documents
    """
    
    def __init__(self, document_graph):
        """Initialize with a document graph"""
        super().__init__()
        self.document_graph = document_graph
        
    def find_cross_document_relationships(self):
        """Find relationships between clauses in different documents"""
        cross_doc_relationships = []
        
        # Group clauses by document
        doc_clauses = {}
        for clause_key, clause in self.clauses.items():
            if clause.doc_id not in doc_clauses:
                doc_clauses[clause.doc_id] = []
            doc_clauses[clause.doc_id].append(clause)
            
        # Check for cross-document references
        for doc_id, clauses in doc_clauses.items():
            for clause in clauses:
                # Look for references to other documents
                other_doc_refs = self._extract_document_references(clause.content)
                
                for ref_doc_id, ref_section in other_doc_refs:
                    if ref_doc_id in doc_clauses:
                        target_clause = self._find_clause_by_section(ref_doc_id, ref_section)
                        if target_clause:
                            rel = ClauseRelationship(
                                source_clause_id=clause.get_key(),
                                target_clause_id=target_clause.get_key(),
                                relationship_type=ClauseRelationType.CROSS_REFERENCE,
                                metadata={"cross_document": True}
                            )
                            cross_doc_relationships.append(rel)
                            
        return cross_doc_relationships
        
    def _extract_document_references(self, content: str) -> List[Tuple[str, str]]:
        """Extract references to other documents"""
        references = []
        
        # Pattern for document references
        patterns = [
            r'(?:as defined in|pursuant to)\s+(?:the\s+)?(\w+\s+(?:Agreement|Lease|Amendment))\s+Section\s+(\d+(?:\.\d+)*)',
            r'(?:Exhibit|Schedule)\s+([A-Z0-9]+)\s+Section\s+(\d+(?:\.\d+)*)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                doc_ref = match.group(1)
                section_ref = match.group(2)
                
                # Try to resolve document reference
                resolved_doc_id = self._resolve_document_reference(doc_ref)
                if resolved_doc_id:
                    references.append((resolved_doc_id, section_ref))
                    
        return references
        
    def _resolve_document_reference(self, doc_ref: str) -> Optional[str]:
        """Resolve a document reference to a document ID"""
        doc_ref_lower = doc_ref.lower()
        
        for doc_id, doc in self.document_graph.documents.items():
            if doc_ref_lower in doc.title.lower():
                return doc_id
                
        return None
