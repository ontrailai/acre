import os
import re
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from app.utils.logger import logger
import tempfile

async def perform_ocr(file_path: str) -> tuple:
    """
    Check if the PDF needs OCR and perform it if necessary.
    Returns a tuple (is_scanned, text_content).
    """
    try:
        # First try to extract text directly from PDF
        text_content = extract_text_from_pdf(file_path)
        
        # Save extracted text to a debug file
        debug_dir = os.path.join("app", "storage", "debug")
        os.makedirs(debug_dir, exist_ok=True)
        base_filename = os.path.basename(file_path)
        debug_path = os.path.join(debug_dir, f"{base_filename}_extracted.txt")
        
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        # Log text extraction statistics
        char_count = len(text_content)
        non_whitespace_count = len(re.sub(r'\s', '', text_content))
        lines_count = len(text_content.splitlines())
        
        logger.info(f"PDF text extraction: {char_count} chars, {non_whitespace_count} non-whitespace chars, {lines_count} lines")
        logger.info(f"Text sample: {text_content[:200].replace(chr(0), '[NUL]')}...")
        
        # Check for specific issues
        if chr(0) in text_content:
            logger.warning(f"PDF contains null bytes, which may indicate corruption or encoding issues")
        
        if non_whitespace_count < 50:  # Very little actual content
            logger.warning(f"Very little content extracted, likely a scanned document or has text extraction limitations")
        
        # Enhanced check for meaningful content 
        min_chars_required = 200  # Increased threshold
        min_non_whitespace_required = 100  # New threshold for non-whitespace
        min_lines_required = 5  # New threshold for number of lines
        
        has_meaningful_content = (
            char_count > min_chars_required and 
            non_whitespace_count > min_non_whitespace_required and
            lines_count > min_lines_required
        )
        
        if has_meaningful_content:
            logger.info(f"PDF contains extractable text, no OCR needed for {file_path}")
            return False, text_content
            
        # If not, it's likely a scanned document, so perform OCR
        logger.info(f"PDF appears to be scanned or lacks extractable text, performing OCR for {file_path}")
        ocr_text = perform_full_ocr(file_path)
        
        # Save OCR text to a debug file
        ocr_debug_path = os.path.join(debug_dir, f"{base_filename}_ocr.txt")
        with open(ocr_debug_path, "w", encoding="utf-8") as f:
            f.write(ocr_text)
            
        # Log OCR statistics
        logger.info(f"OCR extracted {len(ocr_text)} characters, {len(ocr_text.splitlines())} lines")
        logger.info(f"OCR sample: {ocr_text[:200]}...")
        
        return True, ocr_text
        
    except Exception as e:
        logger.error(f"Error in OCR process: {str(e)}")
        # Fallback to full OCR in case of any error
        try:
            ocr_text = perform_full_ocr(file_path)
            return True, ocr_text
        except Exception as inner_e:
            logger.error(f"Critical OCR failure: {str(inner_e)}")
            raise


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text directly from a native PDF file with enhanced error reporting"""
    text = ""
    page_stats = []
    
    try:
        # Open the PDF
        doc = fitz.open(file_path)
        
        logger.info(f"PDF has {len(doc)} pages")
        
        # Try to extract document metadata
        metadata = doc.metadata
        if metadata:
            logger.info(f"PDF metadata: Title='{metadata.get('title', 'None')}', Author='{metadata.get('author', 'None')}', Creator='{metadata.get('creator', 'None')}', Producer='{metadata.get('producer', 'None')}', Encryption={doc.is_encrypted}")
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text += page_text
            
            # Collect statistics for this page
            non_ws_count = len(re.sub(r'\s', '', page_text))
            lines_count = len(page_text.splitlines())
            page_stats.append({
                "page": page_num + 1,
                "chars": len(page_text),
                "non_whitespace": non_ws_count,
                "lines": lines_count
            })
            
        # Log page statistics for debugging
        empty_pages = [p["page"] for p in page_stats if p["non_whitespace"] < 20]
        if empty_pages:
            logger.warning(f"Pages with little or no text content: {empty_pages}")
            
        # Check if first few pages are empty (possibly a cover letter)
        if page_stats and all(p["non_whitespace"] < 20 for p in page_stats[:min(3, len(page_stats))]):
            logger.warning("First few pages appear to have little textual content")
            
        return text
        
    except fitz.EmptyFileError:
        logger.error(f"Empty or invalid PDF file: {file_path}")
        return ""
    except fitz.FileDataError:
        logger.error(f"PDF file data error - possibly corrupted: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""


def perform_full_ocr(file_path: str) -> str:
    """Perform OCR on a scanned PDF document with better error handling and diagnostics"""
    try:
        # Use a proper temp directory that auto-cleans
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Starting OCR process for {file_path} using temp dir: {temp_dir}")
            
            # Set higher DPI for better OCR results
            dpi = 300  # Increased from default 200
            logger.info(f"Converting PDF to images at {dpi} DPI")
            
            try:
                # Convert PDF to images with higher DPI
                images = convert_from_path(file_path, dpi=dpi)
                logger.info(f"Successfully converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"PDF to image conversion failed: {str(e)}")
                raise
            
            # Perform OCR on each image
            text = ""
            page_stats = []
            
            for i, image in enumerate(images):
                try:
                    # Save the image temporarily
                    image_path = os.path.join(temp_dir, f"page_{i}.png")
                    image.save(image_path, "PNG")
                    
                    # Log image dimensions for debugging
                    logger.info(f"Page {i+1} image dimensions: {image.width}x{image.height}")
                    
                    # Try OCR with different configurations if needed
                    page_text = pytesseract.image_to_string(image_path)
                    
                    # Check if OCR returned sufficient text
                    non_ws_count = len(re.sub(r'\s', '', page_text))
                    lines_count = len(page_text.splitlines())
                    
                    page_stats.append({
                        "page": i + 1,
                        "chars": len(page_text),
                        "non_whitespace": non_ws_count,
                        "lines": lines_count
                    })
                    
                    # If OCR returned very little text, try again with different config
                    if non_ws_count < 20 and i < 5:  # Only retry for first few pages to save time
                        logger.warning(f"OCR returned minimal text for page {i+1}, trying alternate config")
                        alt_config = "--psm 1 --oem 1"  # Automatic page segmentation with LSTM OCR
                        page_text = pytesseract.image_to_string(image_path, config=alt_config)
                        
                        # Update stats after retry
                        non_ws_count = len(re.sub(r'\s', '', page_text))
                        logger.info(f"Alternate OCR returned {non_ws_count} non-whitespace chars")
                    
                    text += f"\n--- PAGE {i+1} ---\n{page_text}\n"
                    
                except Exception as page_e:
                    logger.error(f"OCR failed for page {i+1}: {str(page_e)}")
                    text += f"\n--- PAGE {i+1} - OCR ERROR ---\n"
            
            # Log OCR statistics
            empty_pages = [p["page"] for p in page_stats if p["non_whitespace"] < 20]
            if empty_pages:
                logger.warning(f"OCR found little or no text content on pages: {empty_pages}")
            
            if not text.strip():
                logger.error("OCR produced no text content from any page")
            
            return text
    
    except Exception as e:
        logger.error(f"Error performing OCR: {str(e)}")
        # Return minimal content rather than raising - allows downstream processing to continue
        return "\n--- OCR FAILED - SEE LOGS ---\n"
        
