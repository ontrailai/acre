from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import os
import time
import uuid
import json
import aiofiles
from app.schemas import LeaseType, SummaryStyle, ProcessResponse, ClauseExtraction
from app.core.ocr import perform_ocr
from app.core.segmenter import segment_lease
from app.core.enhanced_gpt_extract import EnhancedLeaseExtractor, extract_clauses
from app.core.summary_generator_v2 import generate_markdown_summary, generate_csv_rows
from app.core.risk_analyzer import analyze_risks
from app.core.consistency_checker import ConsistencyChecker
from app.core.document_validator import DocumentValidator
from app.utils.logger import logger

router = APIRouter()


def convert_clauses_to_chunks(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType = None) -> List[Dict[str, Any]]:
    """
    Convert ClauseExtraction objects to the chunk format expected by summary_generator_v2.
    
    Args:
        clauses: Dictionary of ClauseExtraction objects from GPT extraction
        
    Returns:
        List of chunk dictionaries compatible with summary_generator_v2
    """
    chunks = []
    risk_deduplication = {}  # Track risks by clause type for deduplication
    
    for key, clause in clauses.items():
        # Extract clause hint from the key (remove common suffixes)
        clause_hint = key.lower()
        if clause_hint.endswith("_data"):
            clause_hint = clause_hint[:-5]  # Remove "_data" suffix
        
        # Determine the actual clause type from structured data if available
        clause_type = clause_hint
        if clause.structured_data and isinstance(clause.structured_data, dict):
            if 'clause_type' in clause.structured_data:
                clause_type = clause.structured_data['clause_type']
        
        # Convert and deduplicate risk_tags to risk_flags format
        risk_flags = []
        seen_risk_types = set()
        
        if clause.risk_tags:
            for risk in clause.risk_tags:
                risk_type = risk.get("type", "unknown")
                
                # Skip if we've already seen this risk type for this clause
                if risk_type in seen_risk_types:
                    continue
                seen_risk_types.add(risk_type)
                
                # Create consolidated risk description
                description = risk.get("description", "Risk identified")
                if "placeholder" in risk_type and clause.structured_data:
                    # Add specific placeholder info if available
                    for k, v in clause.structured_data.items():
                        if isinstance(v, str) and ("[" in v or "{" in v):
                            description = f"Placeholder value in {k}: {v}"
                            break
                
                risk_flag = {
                    "risk_level": risk.get("level", "medium"),
                    "description": description
                }
                risk_flags.append(risk_flag)
        
        # Extract key_values from structured_data if available
        key_values = {}
        if clause.structured_data:
            key_values = clause.structured_data
        elif clause.content:
            # If no structured data, create a general content entry
            key_values = {"extracted_content": clause.content}
        
        # Create chunk in the expected format
        chunk = {
            "chunk_id": f"C-{len(chunks)+1:03d}",
            "clause_hint": clause_hint,
            "key_values": key_values,
            "risk_flags": risk_flags,
            "confidence": getattr(clause, 'confidence', 0.8),
            "page_start": clause.page_number,
            "page_end": clause.page_number,  # Single page for most clauses
            "truncated": getattr(clause, 'needs_review', False)
        }
        
        # Add lease type if provided
        if lease_type:
            chunk["lease_type"] = lease_type.value if hasattr(lease_type, 'value') else str(lease_type)
        
        # Handle page range if available
        if hasattr(clause, 'page_range') and clause.page_range:
            try:
                if '–' in clause.page_range or '-' in clause.page_range:
                    separator = '–' if '–' in clause.page_range else '-'
                    start_str, end_str = clause.page_range.split(separator)
                    chunk["page_start"] = int(start_str.strip())
                    chunk["page_end"] = int(end_str.strip())
            except (ValueError, AttributeError):
                pass  # Keep single page format
        
        chunks.append(chunk)
    
    return chunks

@router.post("/process", response_model=ProcessResponse)
async def process_lease(
    background_tasks: BackgroundTasks,
    lease_file: UploadFile = File(...),
    lease_type: LeaseType = Form(...),
    company_id: Optional[str] = Form(None),
    summary_style: SummaryStyle = Form(SummaryStyle.EXECUTIVE),
    use_enhanced_extraction: bool = Form(True)
):
    """
    Process a lease PDF file with production-scale enhancements:
    1. Upload and store the PDF
    2. Run OCR if needed
    3. Segment the document
    4. Extract clauses using enhanced GPT system
    5. Validate consistency
    6. Generate a summary
    7. Analyze risks
    8. Return the complete results
    
    All of this happens in a single API call with full audit trail.
    """
    start_time = time.time()
    
    try:
        # Generate a unique ID for this lease
        lease_id = str(uuid.uuid4())
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join("app", "storage", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Create processed directory for this lease
        processed_dir = os.path.join("app", "storage", "processed", lease_id)
        os.makedirs(processed_dir, exist_ok=True)
        
        # Save the uploaded file
        file_extension = os.path.splitext(lease_file.filename)[1].lower()
        if file_extension not in ['.pdf', '.PDF']:
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
        file_path = os.path.join(upload_dir, f"{lease_id}{file_extension}")
        
        # Save the uploaded file
        logger.info(f"Saving uploaded file to {file_path}")
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await lease_file.read()
            await out_file.write(content)
            
        # Check if OCR is needed and perform it
        logger.info(f"Performing OCR analysis for lease {lease_id}")
        is_scanned, text_content = await perform_ocr(file_path)
        logger.info(f"OCR completed for lease {lease_id}. Is scanned: {is_scanned}")
        
        # Save the extracted text
        text_file_path = os.path.join(processed_dir, "text.txt")
        async with aiofiles.open(text_file_path, 'w', encoding='utf-8') as text_file:
            await text_file.write(text_content)
        
        # Validate document before processing
        validator = DocumentValidator()
        is_lease, doc_type, confidence, warnings = validator.validate_document(text_content, lease_file.filename)
        
        if not is_lease:
            logger.warning(f"Document {lease_id} does not appear to be a lease. Type: {doc_type}, Confidence: {confidence:.2f}")
            
            # Return error with helpful information
            processing_suggestion = validator.suggest_processing_method(doc_type)
            basic_info = validator.extract_basic_info(text_content)
            
            error_detail = {
                "error": "Document does not appear to be a lease agreement",
                "detected_type": doc_type,
                "confidence": confidence,
                "warnings": warnings,
                "suggestion": processing_suggestion,
                "document_info": basic_info,
                "possible_causes": [
                    f"Document appears to be a {doc_type.replace('_', ' ')}",
                    "Missing essential lease terms (landlord, tenant, rent, term, premises)",
                    "Document may be a property report or financial statement instead"
                ]
            }
            
            # Save validation result for debugging
            validation_file_path = os.path.join(processed_dir, "validation_failed.json")
            async with aiofiles.open(validation_file_path, 'w', encoding='utf-8') as val_file:
                await val_file.write(json.dumps(error_detail, indent=2))
                
            raise HTTPException(status_code=400, detail=error_detail)
        
        # Log validation warnings if any
        if warnings:
            logger.info(f"Document validation warnings for {lease_id}: {warnings}")
        
        # Segment the lease into sections
        logger.info(f"Segmenting lease {lease_id}")
        segments = segment_lease(text_content, lease_type)
        logger.info(f"Lease segmentation completed for {lease_id}. Found {len(segments)} segments")
        
        # Save the segments
        segments_file_path = os.path.join(processed_dir, "segments.json")
        async with aiofiles.open(segments_file_path, 'w', encoding='utf-8') as segments_file:
            import json
            await segments_file.write(json.dumps(segments, indent=2))
        
        # Extract clauses using enhanced system if enabled
        logger.info(f"Extracting clauses using {'enhanced' if use_enhanced_extraction else 'standard'} system for lease {lease_id}")
        
        extraction_result = None
        validation_report = None
        insights = None
        
        if use_enhanced_extraction:
            # Use the enhanced extraction system
            extractor = EnhancedLeaseExtractor(lease_type)
            
            # Create a single document for extraction
            extraction_result = await extractor.extract_from_single_document(
                text_content,
                segments,
                doc_id=lease_id
            )
            
            clauses = extraction_result.get("clauses", {})
            validation_report = extraction_result.get("validation")
            insights = extraction_result.get("insights", {})
            
            # Log additional results
            logger.info(f"Enhanced extraction complete: {len(clauses)} clauses, "
                       f"{len(extraction_result.get('tables', []))} tables, "
                       f"{validation_report.overall_score if validation_report else 0:.1f}% validation score")
        else:
            # Use standard extraction for backward compatibility
            clauses = await extract_clauses(segments, lease_type)
            
        logger.info(f"Clause extraction completed for lease {lease_id}. Found {len(clauses)} clauses")
        
        # Post-process clauses to apply confidence-based needs_review
        for key, clause in clauses.items():
            # If confidence is low and no risk tags, mark for review
            if hasattr(clause, 'confidence') and clause.confidence < 0.6:
                if not clause.risk_tags or len(clause.risk_tags) == 0:
                    clause.needs_review = True
                    logger.info(f"Marked clause {key} for review due to low confidence ({clause.confidence})")
        
        # Check for template document
        is_template = False
        for segment in segments:
            if segment.get("content") and len(segment.get("content", "")) > 100:
                from app.core.gpt_extract import is_template_lease
                if is_template_lease(segment.get("content")):
                    is_template = True
                    break
        
        # If no clauses were extracted at all, create a minimal result
        if not clauses:
            logger.warning(f"No clauses extracted for lease {lease_id}")
            
            # Create a minimal extraction with document info
            clauses = {
                "document_info": ClauseExtraction(
                    content=json.dumps({
                        "document_type": "lease",
                        "extraction_status": "failed",
                        "is_template": is_template,
                        "total_segments": len(segments),
                        "text_length": len(text_content)
                    }, indent=2),
                    raw_excerpt=text_content[:500] + "..." if len(text_content) > 500 else text_content,
                    confidence=0.1,
                    page_number=1,
                    risk_tags=[{
                        "type": "extraction_failed",
                        "level": "high",
                        "description": "Automated extraction failed - manual review required"
                    }],
                    summary_bullet="Document information",
                    structured_data={"extraction_failed": True},
                    needs_review=True,
                    field_id="document_info"
                )
            }
            
            logger.info(f"Created minimal extraction result for lease {lease_id}")
        
        # Save the extracted clauses
        clauses_file_path = os.path.join(processed_dir, "clauses.json")
        async with aiofiles.open(clauses_file_path, 'w', encoding='utf-8') as clauses_file:
            json_data = {}
            for k, v in clauses.items():
                # Use model_dump() for Pydantic v2+
                try:
                    json_data[k] = v.model_dump()
                except AttributeError:
                    # Fallback for Pydantic v1
                    json_data[k] = v.dict()
            await clauses_file.write(json.dumps(json_data, indent=2, default=str))
        
        # Analyze risks
        logger.info(f"Analyzing risks for lease {lease_id}")
        risk_flags, missing_clauses = analyze_risks(clauses, lease_type)
        logger.info(f"Risk analysis completed for lease {lease_id}. Found {len(risk_flags)} risks and {len(missing_clauses)} missing clauses")
        
        # Generate summary using the new v2 module
        logger.info(f"Generating summary for lease {lease_id}")
        
        # Convert clauses to chunks format for v2 module
        chunks = convert_clauses_to_chunks(clauses, lease_type)
        logger.info(f"Converted {len(clauses)} clauses to {len(chunks)} chunks for v2 processing")
        
        # Generate markdown summary using v2 module
        summary_markdown = generate_markdown_summary(chunks)
        
        # Generate CSV data for potential export
        csv_data = generate_csv_rows(chunks)
        
        # For backward compatibility, create traceability and confidence scores
        traceability = {}
        confidence_scores = {}
        for key, clause in clauses.items():
            if hasattr(clause, 'page_number') and clause.page_number:
                traceability[key] = {
                    "page_number": clause.page_number,
                    "excerpt": clause.raw_excerpt[:200] + "..." if len(clause.raw_excerpt) > 200 else clause.raw_excerpt
                }
            if hasattr(clause, 'confidence') and clause.confidence:
                confidence_scores[key] = clause.confidence
        
        logger.info(f"Summary generation completed for lease {lease_id}")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Total processing time for lease {lease_id}: {processing_time:.2f} seconds")
        
        # Save raw clauses for frontend display (convert to dict for serialization)
        raw_clauses = {}
        for key, clause in clauses.items():
            # Use model_dump() for Pydantic v2+
            try:
                raw_clauses[key] = clause.model_dump()
            except AttributeError:
                # Fallback for Pydantic v1
                raw_clauses[key] = clause.dict()
        
        # Create the response
        response = ProcessResponse(
            lease_id=lease_id,
            summary_markdown=summary_markdown,
            risk_flags=[risk.model_dump() if hasattr(risk, 'model_dump') else risk.dict() for risk in risk_flags],
            traceability=traceability,
            confidence_scores=confidence_scores,
            missing_clauses=missing_clauses,
            processing_time=processing_time,
            raw_clauses=raw_clauses  # Include raw extracted clauses for detailed frontend access
        )
        
        # Add enhanced extraction results if available
        if use_enhanced_extraction and extraction_result:
            response.enhanced_results = {
                "validation_score": validation_report.overall_score if validation_report else None,
                "tables_found": len(extraction_result.get("tables", [])),
                "insights": insights,
                "clause_relationships": extraction_result.get("clause_graph", {}).get("hub_clauses", []) if extraction_result.get("clause_graph") else [],
                "duplicate_clauses": extraction_result.get("similar_clauses", []),
                "outlier_clauses": extraction_result.get("outlier_clauses", [])
            }
        
        # Save CSV data for potential export
        csv_file_path = os.path.join(processed_dir, "export.csv")
        async with aiofiles.open(csv_file_path, 'w', encoding='utf-8') as csv_file:
            import csv
            import io
            
            # Create CSV content in memory first
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)
            
            # Write all rows (headers + data)
            for row in csv_data:
                csv_writer.writerow(row)
            
            # Write to file
            await csv_file.write(csv_buffer.getvalue())
        
        # Save the final response
        response_file_path = os.path.join(processed_dir, "response.json")
        async with aiofiles.open(response_file_path, 'w', encoding='utf-8') as response_file:
            # Convert Pydantic model to dict and then use standard json.dumps
            try:
                # Use model_dump() for Pydantic v2+
                response_dict = response.model_dump(exclude={"raw_clauses"})
            except AttributeError:
                # Fallback for Pydantic v1
                response_dict = response.dict(exclude={"raw_clauses"})
            await response_file.write(json.dumps(response_dict, indent=2, default=str))
        
        # Schedule background tasks (if any)
        background_tasks.add_task(cleanup_temp_files, lease_id, file_path)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing lease: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing lease: {str(e)}")


@router.post("/process-multi-document")
async def process_multi_document(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    lease_type: LeaseType = Form(...),
    company_id: Optional[str] = Form(None)
):
    """
    Process multiple related documents (base lease, amendments, exhibits, etc.)
    with cross-document analysis.
    """
    start_time = time.time()
    
    try:
        # Generate a unique ID for this document set
        doc_set_id = str(uuid.uuid4())
        
        # Create directories
        upload_dir = os.path.join("app", "storage", "uploads", doc_set_id)
        processed_dir = os.path.join("app", "storage", "processed", doc_set_id)
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        
        # Process each uploaded file
        documents = []
        
        for i, file in enumerate(files):
            # Validate file type
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension not in ['.pdf', '.PDF']:
                continue
                
            # Save file
            file_path = os.path.join(upload_dir, f"doc_{i}_{file.filename}")
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
                
            # OCR and extract text
            is_scanned, text_content = await perform_ocr(file_path)
            
            # Determine document type from filename or content
            doc_type = "BASE_LEASE"
            if "amendment" in file.filename.lower():
                doc_type = "AMENDMENT"
            elif "exhibit" in file.filename.lower():
                doc_type = "EXHIBIT"
                
            documents.append({
                "id": f"doc_{i}",
                "type": doc_type,
                "filename": file.filename,
                "content": text_content,
                "title": file.filename.rsplit('.', 1)[0]
            })
            
        # Use enhanced extractor for multi-document processing
        extractor = EnhancedLeaseExtractor(lease_type)
        result = await extractor.extract_from_document_set(documents)
        
        # Save results
        result_file_path = os.path.join(processed_dir, "multi_doc_result.json")
        async with aiofiles.open(result_file_path, 'w', encoding='utf-8') as result_file:
            await result_file.write(json.dumps(result, indent=2, default=str))
            
        processing_time = time.time() - start_time
        
        return {
            "doc_set_id": doc_set_id,
            "documents_processed": len(documents),
            "processing_time": processing_time,
            "summary": result.get("cross_document_analysis"),
            "current_states": result.get("current_states"),
            "validation_results": result.get("validation_results"),
            "document_graph": result.get("document_graph")
        }
        
    except Exception as e:
        logger.error(f"Error processing multi-document set: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")


async def cleanup_temp_files(lease_id: str, file_path: str):
    """Background task to clean up temporary files that are no longer needed"""
    try:
        # After processing is complete and data is saved, we could clean up temp files
        # For now, we'll keep the files for debugging, but in production you might want to:
        
        # 1. Keep only the processed response and extracted text
        # 2. Delete large temporary files
        # 3. Update database records etc.
        
        logger.info(f"Cleanup completed for lease {lease_id}")
    except Exception as e:
        logger.error(f"Error in cleanup for lease {lease_id}: {str(e)}")


@router.get("/export/{lease_id}/csv")
async def download_csv_export(lease_id: str):
    """
    Download the CSV export for a processed lease.
    
    Args:
        lease_id: The unique lease ID from processing
        
    Returns:
        CSV file download response
    """
    try:
        # Check if the CSV file exists
        csv_file_path = os.path.join("app", "storage", "processed", lease_id, "export.csv")
        
        if not os.path.exists(csv_file_path):
            raise HTTPException(status_code=404, detail="CSV export not found for this lease")
        
        # Read the CSV file
        async with aiofiles.open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            csv_content = await csv_file.read()
        
        # Return as downloadable file
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=lease_{lease_id}_export.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading CSV for lease {lease_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating CSV export: {str(e)}")


@router.get("/lease/{lease_id}")
async def get_lease_data(lease_id: str):
    """
    Get the processed lease data for display in the frontend.
    
    Args:
        lease_id: The unique lease ID from processing
        
    Returns:
        Processed lease data including summary, clauses, risks, etc.
    """
    try:
        # Check if the processed response file exists
        response_file_path = os.path.join("app", "storage", "processed", lease_id, "response.json")
        
        if not os.path.exists(response_file_path):
            raise HTTPException(status_code=404, detail="Lease data not found")
        
        # Read the response file
        async with aiofiles.open(response_file_path, 'r', encoding='utf-8') as response_file:
            response_data = json.loads(await response_file.read())
        
        # Read the clauses file for raw_clauses
        clauses_file_path = os.path.join("app", "storage", "processed", lease_id, "clauses.json")
        raw_clauses = {}
        
        if os.path.exists(clauses_file_path):
            async with aiofiles.open(clauses_file_path, 'r', encoding='utf-8') as clauses_file:
                raw_clauses = json.loads(await clauses_file.read())
        
        # Add raw clauses to response
        response_data["raw_clauses"] = raw_clauses
        
        # Extract some key information from clauses for the frontend
        if raw_clauses:
            # Try to extract property address
            for key, clause in raw_clauses.items():
                if "premises" in key.lower() and clause.get("structured_data"):
                    if "address" in clause["structured_data"]:
                        response_data["property_address"] = clause["structured_data"]["address"]
                        break
                        
            # Try to extract tenant and landlord names
            for key, clause in raw_clauses.items():
                if clause.get("structured_data"):
                    data = clause["structured_data"]
                    if "tenant_name" in data:
                        response_data["tenant_name"] = data["tenant_name"]
                    if "landlord_name" in data:
                        response_data["landlord_name"] = data["landlord_name"]
                        
        # Ensure lease_type is included
        if "lease_type" not in response_data:
            # Try to read from segments file
            segments_file_path = os.path.join("app", "storage", "processed", lease_id, "segments.json")
            if os.path.exists(segments_file_path):
                # For now, default to "Unknown"
                response_data["lease_type"] = "Unknown"
        
        return response_data
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Lease data not found")
    except Exception as e:
        logger.error(f"Error retrieving lease data for {lease_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving lease data: {str(e)}")
