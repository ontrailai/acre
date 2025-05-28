"""
Audit Trail and Monitoring System

This module provides comprehensive audit logging, monitoring, and debugging
capabilities for the lease extraction system.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json
import uuid
import os
from enum import Enum
from app.utils.logger import logger


class AuditEventType(Enum):
    """Types of audit events"""
    DOCUMENT_UPLOADED = "document_uploaded"
    OCR_PERFORMED = "ocr_performed"
    CHUNKING_STARTED = "chunking_started"
    CHUNKING_COMPLETED = "chunking_completed"
    GPT_CALL_STARTED = "gpt_call_started"
    GPT_CALL_COMPLETED = "gpt_call_completed"
    GPT_CALL_FAILED = "gpt_call_failed"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_PERFORMED = "validation_performed"
    RISK_IDENTIFIED = "risk_identified"
    AMENDMENT_APPLIED = "amendment_applied"
    EXPORT_GENERATED = "export_generated"
    ERROR_OCCURRED = "error_occurred"
    USER_FEEDBACK = "user_feedback"
    

@dataclass
class AuditEvent:
    """Represents a single audit event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: AuditEventType = None
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value if self.event_type else None
        return data


@dataclass
class ExtractionMetrics:
    """Metrics for an extraction operation"""
    total_pages: int = 0
    total_chunks: int = 0
    total_clauses_extracted: int = 0
    gpt_calls_made: int = 0
    gpt_tokens_used: int = 0
    extraction_time_ms: int = 0
    validation_issues: int = 0
    risk_flags_raised: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score"""
        return sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0.0
        

class AuditTrail:
    """
    Main audit trail system for tracking all operations
    """
    
    def __init__(self, storage_path: str = "app/storage/audit"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.current_session_id = str(uuid.uuid4())
        self.events: List[AuditEvent] = []
        self.metrics: Dict[str, ExtractionMetrics] = {}
        
    def log_event(self, event_type: AuditEventType, **kwargs):
        """Log an audit event"""
        event = AuditEvent(
            event_type=event_type,
            session_id=self.current_session_id,
            **kwargs
        )
        
        self.events.append(event)
        
        # Also log to file immediately
        self._persist_event(event)
        
        # Log to standard logger for real-time monitoring
        logger.info(f"Audit: {event_type.value} - {kwargs.get('details', {})}")
        
        return event.event_id
        
    def log_extraction_decision(self, chunk_id: str, extraction: Dict[str, Any], 
                              reasoning: str, confidence: float):
        """Log why a specific extraction decision was made"""
        self.log_event(
            AuditEventType.EXTRACTION_COMPLETED,
            details={
                "chunk_id": chunk_id,
                "extraction_summary": {
                    "type": extraction.get("clause_type"),
                    "key_values": extraction.get("key_values", {})
                },
                "reasoning": reasoning,
                "confidence": confidence,
                "extraction_method": extraction.get("method", "gpt")
            }
        )
        
    def log_gpt_interaction(self, prompt: str, response: str, 
                          tokens_used: int, duration_ms: int,
                          success: bool = True, error: Optional[str] = None):
        """Log GPT API interaction"""
        event_type = AuditEventType.GPT_CALL_COMPLETED if success else AuditEventType.GPT_CALL_FAILED
        
        self.log_event(
            event_type,
            details={
                "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "response_preview": response[:200] + "..." if response and len(response) > 200 else response,
                "tokens_used": tokens_used,
                "model": "gpt-4-turbo"
            },
            duration_ms=duration_ms,
            success=success,
            error_message=error
        )
        
    def log_validation_result(self, document_id: str, validation_report: Dict[str, Any]):
        """Log validation results"""
        self.log_event(
            AuditEventType.VALIDATION_PERFORMED,
            document_id=document_id,
            details={
                "total_issues": len(validation_report.get("issues", [])),
                "high_severity_issues": sum(1 for i in validation_report.get("issues", []) 
                                          if i.get("severity") == "high"),
                "validation_score": validation_report.get("overall_score", 0)
            }
        )
        
    def log_risk(self, document_id: str, clause_id: str, 
                risk_type: str, severity: str, description: str):
        """Log identified risk"""
        self.log_event(
            AuditEventType.RISK_IDENTIFIED,
            document_id=document_id,
            details={
                "clause_id": clause_id,
                "risk_type": risk_type,
                "severity": severity,
                "description": description
            }
        )
        
    def start_document_processing(self, document_id: str, filename: str,
                                file_size: int, user_id: Optional[str] = None):
        """Mark start of document processing"""
        self.log_event(
            AuditEventType.DOCUMENT_UPLOADED,
            document_id=document_id,
            user_id=user_id,
            details={
                "filename": filename,
                "file_size_bytes": file_size,
                "processing_started": datetime.now().isoformat()
            }
        )
        
        # Initialize metrics for this document
        self.metrics[document_id] = ExtractionMetrics()
        
    def complete_document_processing(self, document_id: str, success: bool = True,
                                   error: Optional[str] = None):
        """Mark completion of document processing"""
        if document_id in self.metrics:
            metrics = self.metrics[document_id]
            
            self.log_event(
                AuditEventType.EXTRACTION_COMPLETED,
                document_id=document_id,
                success=success,
                error_message=error,
                details={
                    "metrics": asdict(metrics),
                    "processing_completed": datetime.now().isoformat()
                }
            )
            
    def get_document_timeline(self, document_id: str) -> List[Dict[str, Any]]:
        """Get timeline of events for a document"""
        timeline = []
        
        for event in self.events:
            if event.document_id == document_id:
                timeline.append({
                    "timestamp": event.timestamp.isoformat(),
                    "event": event.event_type.value,
                    "details": event.details,
                    "duration_ms": event.duration_ms,
                    "success": event.success
                })
                
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        return timeline
        
    def get_processing_stats(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Get processing statistics"""
        if document_id and document_id in self.metrics:
            metrics = self.metrics[document_id]
            return {
                "document_id": document_id,
                "total_pages": metrics.total_pages,
                "total_chunks": metrics.total_chunks,
                "total_clauses": metrics.total_clauses_extracted,
                "gpt_calls": metrics.gpt_calls_made,
                "tokens_used": metrics.gpt_tokens_used,
                "processing_time_ms": metrics.extraction_time_ms,
                "average_confidence": metrics.average_confidence,
                "validation_issues": metrics.validation_issues,
                "risk_flags": metrics.risk_flags_raised
            }
        else:
            # Aggregate stats
            total_docs = len(self.metrics)
            total_clauses = sum(m.total_clauses_extracted for m in self.metrics.values())
            total_gpt_calls = sum(m.gpt_calls_made for m in self.metrics.values())
            total_tokens = sum(m.gpt_tokens_used for m in self.metrics.values())
            
            return {
                "total_documents": total_docs,
                "total_clauses_extracted": total_clauses,
                "total_gpt_calls": total_gpt_calls,
                "total_tokens_used": total_tokens,
                "average_clauses_per_doc": total_clauses / total_docs if total_docs > 0 else 0
            }
            
    def export_audit_log(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> str:
        """Export audit log for date range"""
        filtered_events = self.events
        
        if start_date:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_date]
        if end_date:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_date]
            
        # Convert to JSON
        export_data = {
            "export_date": datetime.now().isoformat(),
            "session_id": self.current_session_id,
            "total_events": len(filtered_events),
            "events": [e.to_dict() for e in filtered_events]
        }
        
        # Save to file
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        return filepath
        
    def _persist_event(self, event: AuditEvent):
        """Persist event to storage"""
        # Daily log files
        date_str = event.timestamp.strftime("%Y-%m-%d")
        filename = f"audit_log_{date_str}.jsonl"
        filepath = os.path.join(self.storage_path, filename)
        
        # Append to file (JSONL format)
        with open(filepath, 'a') as f:
            f.write(json.dumps(event.to_dict()) + '\n')
            

class PerformanceMonitor:
    """
    Monitor system performance and resource usage
    """
    
    def __init__(self):
        self.operation_times: Dict[str, List[int]] = {}
        self.resource_usage: List[Dict[str, Any]] = []
        
    def start_operation(self, operation_name: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation_name}_{uuid.uuid4()}"
        start_time = datetime.now()
        
        # Store start time
        self._operation_starts[operation_id] = start_time
        
        return operation_id
        
    def end_operation(self, operation_id: str) -> int:
        """End timing an operation and return duration in ms"""
        if operation_id not in self._operation_starts:
            return 0
            
        start_time = self._operation_starts[operation_id]
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Extract operation name
        operation_name = operation_id.split('_')[0]
        
        if operation_name not in self.operation_times:
            self.operation_times[operation_name] = []
            
        self.operation_times[operation_name].append(duration_ms)
        
        # Clean up
        del self._operation_starts[operation_id]
        
        return duration_ms
        
    def record_resource_usage(self):
        """Record current resource usage"""
        import psutil
        
        usage = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024
        }
        
        self.resource_usage.append(usage)
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {}
        
        for operation, times in self.operation_times.items():
            if times:
                summary[operation] = {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "total_ms": sum(times)
                }
                
        # Add resource usage stats
        if self.resource_usage:
            cpu_values = [u["cpu_percent"] for u in self.resource_usage]
            memory_values = [u["memory_percent"] for u in self.resource_usage]
            
            summary["resource_usage"] = {
                "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
                "max_cpu_percent": max(cpu_values),
                "avg_memory_percent": sum(memory_values) / len(memory_values),
                "max_memory_percent": max(memory_values)
            }
            
        return summary
        
    def __init__(self):
        self.operation_times: Dict[str, List[int]] = {}
        self.resource_usage: List[Dict[str, Any]] = []
        self._operation_starts: Dict[str, datetime] = {}


class DebugLogger:
    """
    Enhanced debug logging for development and troubleshooting
    """
    
    def __init__(self, debug_path: str = "app/storage/debug"):
        self.debug_path = debug_path
        os.makedirs(debug_path, exist_ok=True)
        
    def save_extraction_debug(self, document_id: str, stage: str, data: Any):
        """Save debug data for extraction stages"""
        stage_path = os.path.join(self.debug_path, document_id, stage)
        os.makedirs(stage_path, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if isinstance(data, dict) or isinstance(data, list):
            filename = f"{stage}_{timestamp}.json"
            filepath = os.path.join(stage_path, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            filename = f"{stage}_{timestamp}.txt"
            filepath = os.path.join(stage_path, filename)
            with open(filepath, 'w') as f:
                f.write(str(data))
                
    def save_gpt_interaction(self, document_id: str, interaction_id: str,
                           prompt: str, response: str, metadata: Dict[str, Any]):
        """Save GPT interaction for debugging"""
        gpt_path = os.path.join(self.debug_path, document_id, "gpt_interactions")
        os.makedirs(gpt_path, exist_ok=True)
        
        interaction_data = {
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
            "prompt": prompt,
            "response": response
        }
        
        filename = f"gpt_{interaction_id}.json"
        filepath = os.path.join(gpt_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(interaction_data, f, indent=2)
