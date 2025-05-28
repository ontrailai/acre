from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass, field
import asyncio
from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger


@dataclass
class ASTNode:
    """Represents a node in the lease document AST"""
    section_id: str
    title: str
    content: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    parent: Optional['ASTNode'] = None
    children: List['ASTNode'] = field(default_factory=list)
    extracted_clauses: Dict[str, ClauseExtraction] = field(default_factory=dict)
    
    def get_hierarchy(self) -> List[str]:
        """Get the full section hierarchy from root to this node"""
        hierarchy = []
        current = self
        while current:
            hierarchy.insert(0, current.section_id)
            current = current.parent
        return hierarchy
    
    def get_full_content(self) -> str:
        """Get content including all children"""
        full_content = self.content
        for child in self.children:
            full_content += "\n" + child.get_full_content()
        return full_content


def extract_section_number(section_name: str) -> Tuple[str, str]:
    """Extract section number and title from section name"""
    # Match patterns like "4.1", "4.1.1", "ARTICLE IV", "Section 4", etc.
    patterns = [
        r'^(\d+(?:\.\d+)*)\s*[.\-]?\s*(.*)$',  # 4.1 Title or 4.1. Title
        r'^(?:ARTICLE|Article)\s+([IVXLCDM]+)\s*[.\-]?\s*(.*)$',  # ARTICLE IV Title
        r'^(?:Section|SECTION)\s+(\d+(?:\.\d+)*)\s*[.\-]?\s*(.*)$',  # Section 4.1 Title
        r'^([A-Z])\.\s*(.*)$',  # A. Title
        r'^\(([a-z])\)\s*(.*)$',  # (a) Title
    ]
    
    for pattern in patterns:
        match = re.match(pattern, section_name.strip())
        if match:
            return match.group(1), match.group(2).strip()
    
    # If no pattern matches, treat the whole thing as title with no number
    return "", section_name.strip()


def compare_section_numbers(num1: str, num2: str) -> int:
    """Compare two section numbers. Returns -1 if num1 < num2, 0 if equal, 1 if num1 > num2"""
    # Handle Roman numerals
    def roman_to_int(s: str) -> int:
        roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        total = 0
        prev_value = 0
        for char in reversed(s):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        return total if total > 0 else float('inf')
    
    # Convert to comparable format
    def normalize_number(num: str) -> List[Any]:
        if not num:
            return [0]
        
        # Check if Roman numeral
        if all(c in 'IVXLCDM' for c in num):
            return [roman_to_int(num)]
        
        # Check if letter
        if len(num) == 1 and num.isalpha():
            return [ord(num.upper())]
        
        # Split by dots for numeric sections
        parts = []
        for part in num.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)
        return parts
    
    norm1 = normalize_number(num1)
    norm2 = normalize_number(num2)
    
    # Compare normalized numbers
    for i in range(min(len(norm1), len(norm2))):
        if norm1[i] < norm2[i]:
            return -1
        elif norm1[i] > norm2[i]:
            return 1
    
    # If all compared parts are equal, shorter is less
    if len(norm1) < len(norm2):
        return -1
    elif len(norm1) > len(norm2):
        return 1
    return 0


def is_child_section(parent_num: str, child_num: str) -> bool:
    """Check if child_num is a direct child of parent_num"""
    if not parent_num or not child_num:
        return False
    
    # For numeric sections (e.g., 4.1 is child of 4)
    if '.' in child_num:
        parent_prefix = parent_num + '.'
        if child_num.startswith(parent_prefix):
            # Check if it's a direct child (no additional dots)
            remainder = child_num[len(parent_prefix):]
            return '.' not in remainder
    
    # For letter subsections
    if len(parent_num) == 1 and parent_num.isdigit() and len(child_num) == 1 and child_num.isalpha():
        return True
    
    return False


def build_lease_ast(segments: List[Dict[str, Any]]) -> Optional[ASTNode]:
    """
    Build an AST from flat segments based on section numbering hierarchy
    """
    if not segments:
        return None
    
    # Create root node
    root = ASTNode(
        section_id="ROOT",
        title="Lease Document",
        content="",
        page_start=segments[0].get("page_start", 1),
        page_end=segments[-1].get("page_end", 1)
    )
    
    # Create nodes for each segment
    nodes = []
    for segment in segments:
        section_num, title = extract_section_number(segment.get("section_name", ""))
        
        node = ASTNode(
            section_id=section_num or segment.get("section_name", ""),
            title=title or segment.get("section_name", ""),
            content=segment.get("content", ""),
            page_start=segment.get("page_start"),
            page_end=segment.get("page_end")
        )
        nodes.append(node)
    
    # Build hierarchy
    for i, node in enumerate(nodes):
        if not node.section_id or node.section_id == node.title:
            # No section number, attach to root
            node.parent = root
            root.children.append(node)
            continue
        
        # Find parent by looking backwards for the most recent suitable parent
        parent_found = False
        for j in range(i - 1, -1, -1):
            potential_parent = nodes[j]
            if potential_parent.section_id and is_child_section(potential_parent.section_id, node.section_id):
                node.parent = potential_parent
                potential_parent.children.append(node)
                parent_found = True
                break
        
        if not parent_found:
            # No direct parent found, attach to root
            node.parent = root
            root.children.append(node)
    
    return root


async def extract_clauses_recursively(
    node: ASTNode, 
    lease_type: LeaseType,
    parent_context: Optional[Dict[str, ClauseExtraction]] = None,
    semaphore: Optional[asyncio.Semaphore] = None
) -> Dict[str, ClauseExtraction]:
    """
    Recursively extract clauses from AST nodes with parent context propagation
    """
    if semaphore is None:
        semaphore = asyncio.Semaphore(5)  # Default concurrency limit
    
    # Import here to avoid circular imports
    from app.core.gpt_extract import process_segment_enhanced
    
    # Prepare segment data for GPT extraction
    segment_data = {
        "section_name": f"{node.section_id} {node.title}".strip(),
        "content": node.content,
        "page_start": node.page_start,
        "page_end": node.page_end
    }
    
    # Extract clauses for current node
    logger.info(f"Extracting clauses for node: {node.section_id} - {node.title}")
    
    # Add parent context to the segment if available
    if parent_context:
        # Create a context summary from parent clauses
        context_summary = "Parent section context:\n"
        for clause_key, parent_clause in parent_context.items():
            clause_type = parent_clause.structured_data.get("clause_type", clause_key.replace("_data", ""))
            summary = parent_clause.summary_bullet or f"{clause_type} information"
            context_summary += f"- {clause_type}: {summary}\n"
        
        # Prepend context to content for better GPT understanding
        segment_data["content"] = context_summary + "\n---\nCurrent section:\n" + segment_data["content"]
    
    # Extract clauses for this node
    node_clauses = await process_segment_enhanced(segment_data, lease_type, semaphore)
    
    # Store extracted clauses in the node
    node.extracted_clauses = node_clauses
    
    # Process children recursively
    if node.children:
        # Process children in parallel
        child_tasks = []
        for child in node.children:
            task = extract_clauses_recursively(
                child, 
                lease_type, 
                node_clauses,  # Pass current node's clauses as context
                semaphore
            )
            child_tasks.append(task)
        
        child_results = await asyncio.gather(*child_tasks)
        
        # Merge child results
        for child, child_clauses in zip(node.children, child_results):
            # Reconcile child clauses with parent clauses
            reconciled = reconcile_clauses(
                node_clauses, 
                child_clauses, 
                parent_hierarchy=node.get_hierarchy(),
                child_hierarchy=child.get_hierarchy()
            )
            node_clauses.update(reconciled)
    
    # Add section hierarchy to all clauses
    for clause_key, clause in node_clauses.items():
        # Add section hierarchy
        if not hasattr(clause, 'section_hierarchy'):
            clause.section_hierarchy = node.get_hierarchy()
        
        # Update structured data with hierarchy info
        if clause.structured_data is None:
            clause.structured_data = {}
        clause.structured_data['section_hierarchy'] = node.get_hierarchy()
    
    return node_clauses


def reconcile_clauses(
    parent_clauses: Dict[str, ClauseExtraction],
    child_clauses: Dict[str, ClauseExtraction],
    parent_hierarchy: List[str],
    child_hierarchy: List[str]
) -> Dict[str, ClauseExtraction]:
    """
    Reconcile parent and child clauses, merging and resolving conflicts
    """
    reconciled = {}
    
    # Process each clause type found in either parent or child
    all_clause_types = set()
    
    # Extract clause types from keys
    for key in parent_clauses.keys():
        clause_type = key.replace("_data", "").replace("_inferred", "")
        all_clause_types.add(clause_type)
    
    for key in child_clauses.keys():
        clause_type = key.replace("_data", "").replace("_inferred", "")
        all_clause_types.add(clause_type)
    
    # Process each clause type
    for clause_type in all_clause_types:
        parent_clause = None
        child_clause = None
        
        # Find matching clauses
        for key, clause in parent_clauses.items():
            if key.startswith(clause_type):
                parent_clause = clause
                break
        
        for key, clause in child_clauses.items():
            if key.startswith(clause_type):
                child_clause = clause
                break
        
        if parent_clause and child_clause:
            # Both exist - merge based on confidence and completeness
            if child_clause.confidence > parent_clause.confidence:
                # Use child as base
                merged_clause = child_clause
                
                # Merge structured data
                if parent_clause.structured_data and child_clause.structured_data:
                    merged_data = {**parent_clause.structured_data, **child_clause.structured_data}
                    merged_clause.structured_data = merged_data
                
                # Combine risk tags
                all_risks = list(parent_clause.risk_tags) + list(child_clause.risk_tags)
                seen_types = set()
                unique_risks = []
                for risk in all_risks:
                    risk_type = risk.get("type", "")
                    if risk_type not in seen_types:
                        seen_types.add(risk_type)
                        unique_risks.append(risk)
                merged_clause.risk_tags = unique_risks
                
                # Update supporting text
                merged_clause.supporting_text = f"Parent: {parent_clause.raw_excerpt[:100]}... Child: {child_clause.raw_excerpt[:100]}..."
                
                # Mark as reconciled
                merged_clause.detection_method = f"Reconciled from parent section {parent_hierarchy[-1]} and child section {child_hierarchy[-1]}"
                
            else:
                # Use parent as base but note child context
                merged_clause = parent_clause
                merged_clause.detection_method = f"Found in parent section {parent_hierarchy[-1]}, refined in child section {child_hierarchy[-1]}"
            
            # Update section hierarchy to show full path
            merged_clause.section_hierarchy = child_hierarchy
            reconciled[f"{clause_type}_data"] = merged_clause
            
        elif child_clause:
            # Only in child - use it with proper hierarchy
            child_clause.section_hierarchy = child_hierarchy
            child_clause.inferred_from_section = f"{child_hierarchy[-1]} (child of {parent_hierarchy[-1]})"
            reconciled[f"{clause_type}_data"] = child_clause
            
        elif parent_clause:
            # Only in parent - keep it but note it wasn't refined in child
            parent_clause.section_hierarchy = parent_hierarchy
            reconciled[f"{clause_type}_data"] = parent_clause
    
    return reconciled


async def extract_clauses_with_ast(segments: List[Dict[str, Any]], lease_type: LeaseType) -> Dict[str, ClauseExtraction]:
    """
    Main entry point for AST-based clause extraction
    """
    # Build AST from segments
    logger.info("Building lease document AST")
    root = build_lease_ast(segments)
    
    if not root:
        logger.error("Failed to build AST from segments")
        return {}
    
    # Log AST structure
    def log_ast_structure(node: ASTNode, depth: int = 0):
        indent = "  " * depth
        logger.debug(f"{indent}{node.section_id}: {node.title} (pages {node.page_start}-{node.page_end})")
        for child in node.children:
            log_ast_structure(child, depth + 1)
    
    logger.debug("AST Structure:")
    log_ast_structure(root)
    
    # Extract clauses recursively
    logger.info("Starting recursive clause extraction")
    all_clauses = await extract_clauses_recursively(root, lease_type)
    
    logger.info(f"Recursive extraction complete. Total clauses: {len(all_clauses)}")
    
    return all_clauses
