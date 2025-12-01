"""
OCR Service for Component Text Recognition

This module uses EasyOCR to read text on PCB components, specifically for:
- IC part numbers (e.g., "NE555", "LM358")
- Component labels

For small SMD resistors/capacitors, generic IDs are assigned instead.
"""

import easyocr
from PIL import Image
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize EasyOCR Reader (English only for efficiency)
# This is loaded once and reused for all OCR operations
reader = None


def initialize_ocr():
    """
    Initialize the EasyOCR reader. Called once at startup.
    """
    global reader
    if reader is None:
        logger.info("Initializing EasyOCR reader...")
        reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=True if CUDA available
        logger.info("EasyOCR reader initialized successfully")


def crop_component_image(image_path: str, bbox: Dict[str, float]) -> np.ndarray:
    """
    Crop the component region from the full PCB image.
    
    Args:
        image_path (str): Path to the full PCB image
        bbox (Dict): Bounding box with keys: x, y, width, height
                    (x, y are center coordinates)
    
    Returns:
        np.ndarray: Cropped image as numpy array
    """
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # Convert center coordinates to corner coordinates
    x_center = int(bbox['x'])
    y_center = int(bbox['y'])
    width = int(bbox['width'])
    height = int(bbox['height'])
    
    # Calculate crop boundaries
    x1 = max(0, x_center - width // 2)
    y1 = max(0, y_center - height // 2)
    x2 = min(img_array.shape[1], x_center + width // 2)
    y2 = min(img_array.shape[0], y_center + height // 2)
    
    # Crop the image
    cropped = img_array[y1:y2, x1:x2]
    
    return cropped


def should_run_ocr(class_name: str) -> bool:
    """
    Determine if OCR should be run on this component type.
    
    Logic:
    - IC/Integrated Circuit: YES (to read part numbers like "NE555")
    - Diode, LED: YES (may have labels)
    - Resistor/Capacitor (SMD): NO (too small, use generic IDs)
    
    Args:
        class_name (str): Component class name from detection
        
    Returns:
        bool: True if OCR should be attempted
    """
    # Convert to lowercase for case-insensitive matching
    class_lower = class_name.lower()
    
    # Components that typically have readable text
    ocr_components = ['ic', 'chip', 'integrated', 'circuit', 'diode', 'led', 'transistor']
    
    # Components that are typically too small or have no text
    no_ocr_components = ['resistor', 'capacitor', 'smd']
    
    # Check if component should have OCR
    for comp_type in ocr_components:
        if comp_type in class_lower:
            return True
    
    for comp_type in no_ocr_components:
        if comp_type in class_lower:
            return False
    
    # Default: try OCR for unknown component types
    return True


def run_ocr_on_crop(cropped_image: np.ndarray) -> Optional[str]:
    """
    Run EasyOCR on a cropped component image.
    
    Args:
        cropped_image (np.ndarray): Cropped component image
        
    Returns:
        Optional[str]: Detected text or None if no text found
    """
    global reader
    
    if reader is None:
        initialize_ocr()
    
    try:
        # Run OCR
        results = reader.readtext(cropped_image, detail=0)  # detail=0 returns only text
        
        if results and len(results) > 0:
            # Join all detected text with spaces
            text = ' '.join(results).strip()
            logger.info(f"OCR detected text: {text}")
            return text
        else:
            logger.info("OCR: No text detected")
            return None
            
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return None


# Counters for generic component naming
component_counters = {
    'resistor': 0,
    'capacitor': 0,
    'ic': 0,
    'diode': 0,
    'led': 0,
    'transistor': 0,
    'unknown': 0
}


def get_generic_id(class_name: str) -> str:
    """
    Generate a generic component ID with auto-incrementing counter.
    
    Args:
        class_name (str): Component class name
        
    Returns:
        str: Generic ID (e.g., "R1", "C2", "U3")
    """
    global component_counters
    
    class_lower = class_name.lower()
    
    # Map component types to standard prefixes
    if 'resistor' in class_lower:
        component_counters['resistor'] += 1
        return f"R{component_counters['resistor']}"
    elif 'capacitor' in class_lower:
        component_counters['capacitor'] += 1
        return f"C{component_counters['capacitor']}"
    elif 'ic' in class_lower or 'chip' in class_lower or 'integrated' in class_lower:
        component_counters['ic'] += 1
        return f"U{component_counters['ic']}"
    elif 'diode' in class_lower:
        component_counters['diode'] += 1
        return f"D{component_counters['diode']}"
    elif 'led' in class_lower:
        component_counters['led'] += 1
        return f"LED{component_counters['led']}"
    elif 'transistor' in class_lower:
        component_counters['transistor'] += 1
        return f"Q{component_counters['transistor']}"
    else:
        component_counters['unknown'] += 1
        return f"X{component_counters['unknown']}"


def get_component_name(image_path: str, component: Dict[str, Any]) -> str:
    """
    Get the final component name/ID using OCR or generic naming.
    
    Logic Flow:
    1. Check if component type should use OCR
    2. If YES: Crop image, run OCR
       - If OCR successful: return detected text
       - If OCR fails: fallback to generic ID
    3. If NO: directly return generic ID
    
    Args:
        image_path (str): Path to full PCB image
        component (Dict): Component dictionary with 'class_name' and 'bbox'
        
    Returns:
        str: Final component name/ID
    """
    class_name = component['class_name']
    bbox = component['bbox']
    
    logger.info(f"Processing component: {class_name}")
    
    # Check if we should attempt OCR
    if should_run_ocr(class_name):
        try:
            # Crop the component region
            cropped = crop_component_image(image_path, bbox)
            
            # Run OCR
            ocr_result = run_ocr_on_crop(cropped)
            
            # If OCR found text, use it
            if ocr_result:
                logger.info(f"Using OCR result: {ocr_result}")
                return ocr_result
            else:
                # OCR failed, fallback to generic ID
                logger.info(f"OCR failed for {class_name}, using generic ID")
                return get_generic_id(class_name)
                
        except Exception as e:
            logger.error(f"Error during OCR processing: {str(e)}")
            return get_generic_id(class_name)
    else:
        # Component type doesn't need OCR, use generic ID
        logger.info(f"{class_name} doesn't require OCR, using generic ID")
        return get_generic_id(class_name)


def reset_counters():
    """
    Reset component counters (useful for processing a new image).
    """
    global component_counters
    for key in component_counters:
        component_counters[key] = 0
    logger.info("Component counters reset")

