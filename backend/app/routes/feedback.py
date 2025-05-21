from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas import FeedbackRequest, FeedbackResponse
from app.training.feedback_manager import store_feedback, get_lease_feedback, get_feedback_by_field_id, get_feedback_statistics
from app.utils.logger import logger
import uuid

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit feedback for a lease extraction field.
    This feedback will be used to improve the model over time.
    """
    try:
        # Generate a unique ID for this feedback
        feedback_id = str(uuid.uuid4())
        
        # Store the feedback with enhanced field identification
        await store_feedback(
            feedback_id=feedback_id,
            lease_id=feedback.lease_id,
            field_id=feedback.field_id,
            original=feedback.original,
            corrected=feedback.corrected,
            user_id=feedback.user_id,
            clause_name=feedback.clause_name,
            additional_notes=feedback.additional_notes
        )
        
        logger.info(f"Feedback submitted for lease {feedback.lease_id}, field {feedback.field_id}")
        
        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id
        )
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")


@router.get("/feedback/{lease_id}")
async def get_lease_feedback_endpoint(lease_id: str):
    """
    Get all feedback submitted for a specific lease
    """
    try:
        # Fetch feedback from the feedback manager
        feedback = await get_lease_feedback(lease_id)
        
        return {
            "lease_id": lease_id,
            "feedback_count": len(feedback),
            "feedback": feedback
        }
        
    except Exception as e:
        logger.error(f"Error retrieving feedback for lease {lease_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback: {str(e)}")


@router.get("/feedback/field/{field_id}")
async def get_field_feedback(
    field_id: str,
    limit: int = Query(50, description="Maximum number of feedback items to return")
):
    """
    Get all feedback history for a specific field across all leases
    """
    try:
        # Fetch feedback by field ID
        feedback = await get_feedback_by_field_id(field_id)
        
        # Limit the number of items returned
        limited_feedback = feedback[-limit:] if len(feedback) > limit else feedback
        
        return {
            "field_id": field_id,
            "feedback_count": len(feedback),
            "returned_count": len(limited_feedback),
            "feedback": limited_feedback
        }
        
    except Exception as e:
        logger.error(f"Error retrieving feedback for field {field_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving field feedback: {str(e)}")


@router.get("/feedback/statistics")
async def get_feedback_stats():
    """
    Get statistics about collected feedback
    """
    try:
        # Fetch feedback statistics
        stats = await get_feedback_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving feedback statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback statistics: {str(e)}")
