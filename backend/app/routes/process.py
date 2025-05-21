from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import os
import time
import uuid
import aiofiles
from app.schemas import LeaseType, SummaryStyle, ProcessResponse
from app.core.ocr import perform_ocr
from app.core.segmenter import segment_lease
from app.core.gpt_extract import extract_clauses
from app.core.smart_summary_generator import generate_summary
from app.core.risk_analyzer import analyze_risks
from app.utils.logger import logger

router = APIRouter()

@router.post("/process", response_model=ProcessResponse)
async def process_lease(
    background_tasks: BackgroundTasks,
    lease_file: UploadFile = File(...),
    lease_type: LeaseType = Form(...),
    company_id: Optional[str] = Form(None),
    summary_style: SummaryStyle = Form(SummaryStyle.EXECUTIVE)
):
    """
    Process a lease PDF file in one seamless step:
    1. Upload and store the PDF
    2. Run OCR if needed
    3. Segment the document
    4. Extract clauses using GPT
    5. Generate a summary
    6. Analyze risks
    7. Return the complete results
    
    All of this happens in a single API call - no second extraction step required.
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
        
        # Segment the lease into sections
        logger.info(f"Segmenting lease {lease_id}")
        segments = segment_lease(text_content, lease_type)
        logger.info(f"Lease segmentation completed for {lease_id}. Found {len(segments)} segments")
        
        # Save the segments
        segments_file_path = os.path.join(processed_dir, "segments.json")
        async with aiofiles.open(segments_file_path, 'w', encoding='utf-8') as segments_file:
            import json
            await segments_file.write(json.dumps(segments, indent=2))
        
        # Extract clauses using GPT with section-specific prompting
        logger.info(f"Extracting clauses using GPT for lease {lease_id}")
        try:
            clauses = await extract_clauses(segments, lease_type)
            logger.info(f"Clause extraction completed for lease {lease_id}. Found {len(clauses)} clauses")
            
            # Check for template document
            is_template = False
            for segment in segments:
                if segment.get("content") and len(segment.get("content", "")) > 100:
                    from app.core.gpt_extract import is_template_lease
                    if is_template_lease(segment.get("content")):
                        is_template = True
                        break
            
            if not clauses:
                logger.warning(f"No clauses extracted for lease {lease_id}")
                
                # Don't raise exception, instead continue with empty clauses
                # The summary generator will handle this gracefully
                if is_template:
                    logger.info(f"Detected template lease document for {lease_id}, continuing with empty clauses")
                else:
                    logger.error(f"Critical failure: No clauses extracted for lease {lease_id} and not a template")
                    # Only raise exception if not a template
                    raise HTTPException(
                        status_code=500, 
                        detail={
                            "error": "No lease clauses were extracted",
                            "possible_causes": [
                                "PDF may contain minimal or unreadable text",
                                "Document format may not be recognized as a lease",
                                "Text extraction may have failed - check debug logs"
                            ],
                            "debug_location": "storage/debug/"
                        }
                    )
        except Exception as e:
            logger.error(f"Error during clause extraction: {str(e)}")
            # Save segments for debugging
            debug_dir = os.path.join("app", "storage", "debug")
            with open(os.path.join(debug_dir, f"{lease_id}_segments.json"), "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=2, default=str)
            raise
        
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
        
        # Generate summary
        logger.info(f"Generating summary for lease {lease_id}")
        summary_markdown, traceability, confidence_scores = generate_summary(
            clauses, 
            lease_type, 
            summary_style
        )
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
