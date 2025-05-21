import os
import json
import datetime
from typing import Optional, Dict, Any
import aiofiles
from app.utils.logger import logger

async def store_feedback(
    feedback_id: str,
    lease_id: str,
    field_id: str,
    original: str,
    corrected: str,
    user_id: Optional[str] = None,
    clause_name: Optional[str] = None,
    additional_notes: Optional[str] = None
):
    """
    Store user feedback for future training and improvement.
    The field_id provides clear traceability to the exact data field/clause.
    """
    try:
        # Create the feedback directory if it doesn't exist
        feedback_dir = os.path.join("app", "storage", "feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        
        # Create the lease feedback directory if it doesn't exist
        lease_feedback_dir = os.path.join(feedback_dir, lease_id)
        os.makedirs(lease_feedback_dir, exist_ok=True)
        
        # Create feedback data with enhanced structure
        feedback_data = {
            "feedback_id": feedback_id,
            "lease_id": lease_id,
            "field_id": field_id,  # Structured field ID (section.clause_name)
            "clause_name": clause_name or field_id.split(".")[-1] if "." in field_id else field_id,
            "original": original,
            "corrected": corrected,
            "user_id": user_id,
            "additional_notes": additional_notes,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Save feedback to a JSON file
        feedback_file = os.path.join(lease_feedback_dir, f"{feedback_id}.json")
        async with aiofiles.open(feedback_file, 'w') as f:
            await f.write(json.dumps(feedback_data, indent=2))
            
        # Also append to a consolidated feedback file for easier processing
        consolidated_file = os.path.join(feedback_dir, "consolidated_feedback.jsonl")
        async with aiofiles.open(consolidated_file, 'a') as f:
            await f.write(json.dumps(feedback_data) + "\n")
        
        # Also create a field-specific consolidated file to track changes to the same field across leases
        field_file = os.path.join(feedback_dir, f"field_{field_id.replace('.', '_')}.jsonl") 
        async with aiofiles.open(field_file, 'a') as f:
            await f.write(json.dumps(feedback_data) + "\n")
            
        logger.info(f"Stored feedback {feedback_id} for lease {lease_id}, field {field_id}")
        
        # Track the feedback history for this particular lease
        await update_lease_feedback_history(lease_id, feedback_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error storing feedback: {str(e)}")
        raise


async def update_lease_feedback_history(lease_id: str, feedback_data: Dict[str, Any]):
    """Maintain a history of all feedback for a specific lease"""
    try:
        history_file = os.path.join("app", "storage", "feedback", lease_id, "feedback_history.jsonl")
        
        async with aiofiles.open(history_file, 'a') as f:
            await f.write(json.dumps(feedback_data) + "\n")
            
    except Exception as e:
        logger.error(f"Error updating lease feedback history: {str(e)}")


async def get_lease_feedback(lease_id: str):
    """Get all feedback for a specific lease"""
    try:
        feedback_list = []
        
        # Check if the lease feedback directory exists
        lease_feedback_dir = os.path.join("app", "storage", "feedback", lease_id)
        if not os.path.exists(lease_feedback_dir):
            return []
            
        # Get all feedback files for this lease
        for filename in os.listdir(lease_feedback_dir):
            if filename.endswith(".json") and filename != "feedback_history.jsonl":
                file_path = os.path.join(lease_feedback_dir, filename)
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    feedback_data = json.loads(content)
                    feedback_list.append(feedback_data)
                    
        # Sort by timestamp
        feedback_list.sort(key=lambda x: x.get("timestamp", ""))
        
        return feedback_list
        
    except Exception as e:
        logger.error(f"Error retrieving feedback for lease {lease_id}: {str(e)}")
        return []


async def get_feedback_by_field_id(field_id: str):
    """Get all feedback history for a specific field across all leases"""
    try:
        feedback_list = []
        
        # Check if the field-specific feedback file exists
        field_file = os.path.join("app", "storage", "feedback", f"field_{field_id.replace('.', '_')}.jsonl")
        if not os.path.exists(field_file):
            return []
            
        # Read all feedback for this field
        async with aiofiles.open(field_file, 'r') as f:
            lines = await f.readlines()
            for line in lines:
                feedback_data = json.loads(line.strip())
                feedback_list.append(feedback_data)
                    
        # Sort by timestamp
        feedback_list.sort(key=lambda x: x.get("timestamp", ""))
        
        return feedback_list
        
    except Exception as e:
        logger.error(f"Error retrieving feedback for field {field_id}: {str(e)}")
        return []


async def get_feedback_statistics():
    """Get statistics about collected feedback"""
    try:
        # Initialize statistics
        stats = {
            "total_feedback_count": 0,
            "lease_count": 0,
            "field_counts": {},
            "recent_feedback": []
        }
        
        # Check if the feedback directory exists
        feedback_dir = os.path.join("app", "storage", "feedback")
        if not os.path.exists(feedback_dir):
            return stats
            
        # Count unique leases
        lease_dirs = [d for d in os.listdir(feedback_dir) 
                     if os.path.isdir(os.path.join(feedback_dir, d)) and d != "field_specific"]
        
        stats["lease_count"] = len(lease_dirs)
        
        # Process consolidated feedback
        consolidated_file = os.path.join(feedback_dir, "consolidated_feedback.jsonl")
        if os.path.exists(consolidated_file):
            async with aiofiles.open(consolidated_file, 'r') as f:
                lines = await f.readlines()
                
                stats["total_feedback_count"] = len(lines)
                
                # Process the most recent feedback (last 10)
                for line in lines[-10:]:
                    feedback_data = json.loads(line.strip())
                    stats["recent_feedback"].append({
                        "feedback_id": feedback_data.get("feedback_id"),
                        "lease_id": feedback_data.get("lease_id"),
                        "field_id": feedback_data.get("field_id"),
                        "timestamp": feedback_data.get("timestamp")
                    })
                
                # Count feedback by field type
                for line in lines:
                    feedback_data = json.loads(line.strip())
                    field_id = feedback_data.get("field_id", "unknown")
                    
                    # Get the base field type (before the dot)
                    field_type = field_id.split(".")[0] if "." in field_id else field_id
                    
                    if field_type not in stats["field_counts"]:
                        stats["field_counts"][field_type] = 0
                        
                    stats["field_counts"][field_type] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving feedback statistics: {str(e)}")
        return {"error": str(e)}
