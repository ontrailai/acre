"""
Fixed Enhanced GPT Extraction Module

This fixes the specialized extractor issue where DateTimeExtractor 
was being called with extract_base_rent method.
"""

# This is a partial fix for the _process_segment_production method
# Replace the existing method in enhanced_gpt_extract.py with this one

async def _process_segment_production(self, segment: Dict[str, Any], 
                                    semaphore: asyncio.Semaphore) -> Dict[str, ClauseExtraction]:
    """
    Process segment with all production enhancements
    """
    async with semaphore:
        # Track performance
        op_id = self.performance_monitor.start_operation("segment_processing")
        
        try:
            # Get appropriate specialized extractor
            segment_type = self._determine_segment_type(segment)
            specialized_extractor = create_specialized_extractor(segment_type)
            
            # Extract using specialized extractor if available
            if specialized_extractor and segment_type:
                try:
                    segment_content = segment.get("content", "")
                    result = None
                    
                    # Call the appropriate method based on extractor type
                    if segment_type == "financial":
                        # Try multiple financial extraction methods
                        if hasattr(specialized_extractor, 'extract_base_rent'):
                            result = specialized_extractor.extract_base_rent(segment_content)
                        if not result or not result.extracted_data:
                            if hasattr(specialized_extractor, 'extract_percentage_rent'):
                                result = specialized_extractor.extract_percentage_rent(segment_content)
                        if not result or not result.extracted_data:
                            if hasattr(specialized_extractor, 'extract_cam_charges'):
                                result = specialized_extractor.extract_cam_charges(segment_content)
                                
                    elif segment_type == "datetime":
                        # Try multiple datetime extraction methods
                        if hasattr(specialized_extractor, 'extract_critical_dates'):
                            result = specialized_extractor.extract_critical_dates(segment_content)
                        if not result or not result.extracted_data:
                            if hasattr(specialized_extractor, 'extract_notice_periods'):
                                result = specialized_extractor.extract_notice_periods(segment_content)
                                
                    elif segment_type == "conditional":
                        # Try conditional extraction methods
                        if hasattr(specialized_extractor, 'extract_conditional_rights'):
                            result = specialized_extractor.extract_conditional_rights(segment_content)
                        if not result or not result.extracted_data:
                            if hasattr(specialized_extractor, 'extract_co_tenancy_provisions'):
                                result = specialized_extractor.extract_co_tenancy_provisions(segment_content)
                                
                    elif segment_type == "rights":
                        # Try rights extraction methods
                        if hasattr(specialized_extractor, 'extract_renewal_options'):
                            result = specialized_extractor.extract_renewal_options(segment_content)
                        if not result or not result.extracted_data:
                            if hasattr(specialized_extractor, 'extract_expansion_rights'):
                                result = specialized_extractor.extract_expansion_rights(segment_content)
                    
                    # If specialized extraction succeeded, convert and return
                    if result and result.extracted_data:
                        return self._convert_specialized_result(result, segment)
                        
                except Exception as e:
                    logger.warning(f"Specialized extractor failed for {segment_type}: {e}")
                    
            # Fall back to GPT extraction
            return await self._gpt_extract_segment(segment)
            
        except Exception as e:
            logger.error(f"Segment processing error: {e}")
            return {}
            
        finally:
            duration = self.performance_monitor.end_operation(op_id)
            logger.debug(f"Segment processed in {duration}ms")
