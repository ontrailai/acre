from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import uuid

class LeaseType(str, Enum):
    RETAIL = "retail"
    OFFICE = "office"
    INDUSTRIAL = "industrial"

class SummaryStyle(str, Enum):
    EXECUTIVE = "executive"
    LEGAL = "legal"

class ExportFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    JSON = "json"
    MARKDOWN = "markdown"

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LeaseUploadRequest(BaseModel):
    lease_type: LeaseType
    company_id: Optional[str] = None
    summary_style: SummaryStyle = SummaryStyle.EXECUTIVE
    
class ProcessResponse(BaseModel):
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    summary_markdown: str
    risk_flags: List[Dict[str, Any]]
    traceability: Dict[str, Any]
    confidence_scores: Dict[str, float]
    missing_clauses: List[str] = []
    processing_time: float
    raw_clauses: Optional[Dict[str, Any]] = None  # For frontend access to structured data
    enhanced_results: Optional[Dict[str, Any]] = None  # Results from enhanced extraction system
    
class FeedbackRequest(BaseModel):
    lease_id: str
    field_id: str  # Added structured field ID for better tracking
    original: str
    corrected: str
    user_id: Optional[str] = None
    clause_name: Optional[str] = None
    additional_notes: Optional[str] = None
    
class FeedbackResponse(BaseModel):
    success: bool
    feedback_id: str
    
class RiskFlag(BaseModel):
    clause_key: str
    clause_name: str
    level: RiskLevel
    description: str
    source: str
    related_text: Optional[str] = None
    page_number: Optional[int] = None
    
class ClauseExtraction(BaseModel):
    content: str
    raw_excerpt: str
    confidence: float
    page_number: Optional[int] = None
    page_range: Optional[str] = None
    risk_tags: List[Dict[str, Any]] = []
    summary_bullet: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = {}
    needs_review: Optional[bool] = False
    field_id: Optional[str] = None  # Unique identifier for this field/clause
    inferred_from_section: Optional[str] = None  # Track when clause is inferred from different section
    section_hierarchy: Optional[List[str]] = None  # Full section hierarchy path
    detection_method: Optional[str] = None  # How the clause was detected/reconciled
    
class LeaseSummary(BaseModel):
    lease_id: str
    lease_type: LeaseType
    processed_at: datetime = Field(default_factory=datetime.now)
    overview: Dict[str, Any]
    term: Dict[str, Any]
    rent: Dict[str, Any]
    additional_charges: Dict[str, Any]
    maintenance: Dict[str, Any]
    use: Dict[str, Any]
    assignment: Dict[str, Any]
    insurance: Dict[str, Any]
    casualty: Dict[str, Any]
    eminent_domain: Dict[str, Any]
    legal: Dict[str, Any]
    entry: Dict[str, Any]
    miscellaneous: Dict[str, Any]
    risk_flags: List[Dict[str, Any]]
    missing_clauses: List[str]
    traceability: Dict[str, Any]
