import os
import json
import glob
from typing import List, Dict, Any
from app.utils.logger import logger

class TrainingManager:
    """
    Manages the collection and preparation of training data for improving
    the lease extraction and summarization models.
    """
    
    def __init__(self):
        self.feedback_dir = os.path.join("app", "storage", "feedback")
        self.processed_dir = os.path.join("app", "storage", "processed")
        self.training_dir = os.path.join("app", "storage", "training")
        
        # Create directories if they don't exist
        os.makedirs(self.feedback_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
    
    def generate_training_dataset(self):
        """
        Generate a training dataset from feedback and processed leases.
        This is meant to be run as a batch process, not during normal operation.
        """
        try:
            logger.info("Starting training dataset generation")
            
            # Collect all consolidated feedback
            feedback_data = self._collect_feedback()
            logger.info(f"Collected {len(feedback_data)} feedback entries")
            
            # Organize feedback by lease
            feedback_by_lease = self._organize_feedback_by_lease(feedback_data)
            
            # Generate extraction training examples
            extraction_examples = self._generate_extraction_examples(feedback_by_lease)
            logger.info(f"Generated {len(extraction_examples)} extraction examples")
            
            # Generate summarization training examples
            summarization_examples = self._generate_summarization_examples(feedback_by_lease)
            logger.info(f"Generated {len(summarization_examples)} summarization examples")
            
            # Save training datasets
            self._save_training_dataset(extraction_examples, "extraction_examples.jsonl")
            self._save_training_dataset(summarization_examples, "summarization_examples.jsonl")
            
            logger.info("Training dataset generation completed")
            return True
            
        except Exception as e:
            logger.error(f"Error generating training dataset: {str(e)}")
            return False
    
    def _collect_feedback(self) -> List[Dict[str, Any]]:
        """Collect all feedback from the consolidated file"""
        feedback_data = []
        
        consolidated_file = os.path.join(self.feedback_dir, "consolidated_feedback.jsonl")
        if os.path.exists(consolidated_file):
            with open(consolidated_file, 'r') as f:
                for line in f:
                    try:
                        feedback = json.loads(line.strip())
                        feedback_data.append(feedback)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in feedback file: {line}")
        
        return feedback_data
    
    def _organize_feedback_by_lease(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize feedback by lease ID"""
        feedback_by_lease = {}
        
        for feedback in feedback_data:
            lease_id = feedback.get("lease_id")
            if lease_id:
                if lease_id not in feedback_by_lease:
                    feedback_by_lease[lease_id] = []
                feedback_by_lease[lease_id].append(feedback)
        
        return feedback_by_lease
    
    def _generate_extraction_examples(self, feedback_by_lease: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Generate examples for improving the extraction model"""
        extraction_examples = []
        
        for lease_id, feedback_list in feedback_by_lease.items():
            # Try to get the original text for this lease
            text_path = os.path.join(self.processed_dir, lease_id, "text.txt")
            if not os.path.exists(text_path):
                logger.warning(f"Original text not found for lease {lease_id}")
                continue
                
            with open(text_path, 'r') as f:
                original_text = f.read()
                
            # Get the segments for this lease
            segments_path = os.path.join(self.processed_dir, lease_id, "segments.json")
            if not os.path.exists(segments_path):
                logger.warning(f"Segments not found for lease {lease_id}")
                continue
                
            with open(segments_path, 'r') as f:
                segments = json.load(f)
                
            # Create extraction examples from feedback
            for feedback in feedback_list:
                field = feedback.get("field")
                original = feedback.get("original")
                corrected = feedback.get("corrected")
                
                # Find the relevant segment for this field
                relevant_segment = None
                for segment in segments:
                    # Check if field name is related to this segment
                    segment_name = segment.get("section_name", "").lower()
                    field_lower = field.lower()
                    
                    if segment_name in field_lower or any(
                        term in field_lower for term in segment_name.split("_")
                    ):
                        relevant_segment = segment
                        break
                
                if relevant_segment:
                    example = {
                        "lease_id": lease_id,
                        "field": field,
                        "segment_name": relevant_segment.get("section_name"),
                        "segment_content": relevant_segment.get("content"),
                        "original_extraction": original,
                        "corrected_extraction": corrected,
                        "timestamp": feedback.get("timestamp")
                    }
                    extraction_examples.append(example)
        
        return extraction_examples
    
    def _generate_summarization_examples(self, feedback_by_lease: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Generate examples for improving the summarization model"""
        summarization_examples = []
        
        for lease_id, feedback_list in feedback_by_lease.items():
            # Try to get the response data for this lease
            response_path = os.path.join(self.processed_dir, lease_id, "response.json")
            if not os.path.exists(response_path):
                logger.warning(f"Response data not found for lease {lease_id}")
                continue
                
            with open(response_path, 'r') as f:
                response_data = json.load(f)
                
            # Get the original summary
            original_summary = response_data.get("summary_markdown", "")
            
            # Create a modified summary incorporating all feedback
            modified_summary = original_summary
            
            # Track all modifications to avoid conflicts
            modifications = []
            
            for feedback in feedback_list:
                field = feedback.get("field")
                original = feedback.get("original")
                corrected = feedback.get("corrected")
                
                # Try to find and replace the content in the summary
                if original in modified_summary:
                    # Check if this section overlaps with previous modifications
                    overlap = False
                    for start, end in modifications:
                        orig_start = modified_summary.find(original)
                        orig_end = orig_start + len(original)
                        
                        if (orig_start <= start and orig_end > start) or (orig_start < end and orig_end >= end):
                            overlap = True
                            break
                    
                    if not overlap:
                        # Track this modification
                        orig_start = modified_summary.find(original)
                        orig_end = orig_start + len(original)
                        modifications.append((orig_start, orig_end))
                        
                        # Apply the modification
                        modified_summary = modified_summary.replace(original, corrected)
            
            # Create a summarization example
            if modified_summary != original_summary:
                example = {
                    "lease_id": lease_id,
                    "original_summary": original_summary,
                    "corrected_summary": modified_summary,
                    "feedback_count": len(feedback_list),
                    "timestamp": max(feedback.get("timestamp", "") for feedback in feedback_list)
                }
                summarization_examples.append(example)
        
        return summarization_examples
    
    def _save_training_dataset(self, examples: List[Dict[str, Any]], filename: str):
        """Save training examples to a JSONL file"""
        if not examples:
            logger.warning(f"No examples to save for {filename}")
            return
            
        output_path = os.path.join(self.training_dir, filename)
        
        with open(output_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
                
        logger.info(f"Saved {len(examples)} examples to {output_path}")
    
    def bulk_process_leases(self, input_dir: str):
        """
        Process a directory of lease PDFs for model training.
        This is meant to be run as a batch process, not during normal operation.
        """
        # This would be a more complex implementation that would:
        # 1. Find all PDFs in the input directory
        # 2. Process each one using the extraction pipeline
        # 3. Store the results for future training
        # For simplicity, we'll just log a placeholder message
        logger.info(f"Bulk processing of leases from {input_dir} would go here")
        return True
