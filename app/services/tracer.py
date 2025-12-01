"""
Copper Track Tracing Module using OpenCV

This module processes PCB images to isolate and segment copper tracks
using color-based masking and morphological operations.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Color bounds for copper track detection (HSV color space)
# These values target light green/gold colors typical of PCB copper tracks
# Adjustable for different PCB colors

# Default bounds for green PCBs
DEFAULT_LOWER_BOUND = np.array([35, 40, 40])    # Lower HSV bound for green PCB
DEFAULT_UPPER_BOUND = np.array([85, 255, 255])  # Upper HSV bound for green PCB

# Alternative bounds for copper/gold colored tracks
COPPER_LOWER_BOUND = np.array([10, 50, 50])     # Lower HSV for copper/gold
COPPER_UPPER_BOUND = np.array([30, 255, 255])   # Upper HSV for copper/gold


def load_image(image_path: str) -> np.ndarray:
    """
    Load an image from file path.
    
    Args:
        image_path (str): Path to image file
        
    Returns:
        np.ndarray: Loaded image in BGR format
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    logger.info(f"Loaded image with shape: {img.shape}")
    return img


def extract_copper_tracks(image_path: str, 
                         lower_bound: Optional[np.ndarray] = None,
                         upper_bound: Optional[np.ndarray] = None,
                         use_copper_color: bool = False) -> np.ndarray:
    """
    Extract copper tracks from PCB image using color-based segmentation.
    
    Process:
    1. Convert image to HSV color space
    2. Apply color mask to isolate copper tracks
    3. Apply morphological operations to remove noise
    4. Return binary image (White tracks on Black background)
    
    Args:
        image_path (str): Path to PCB image
        lower_bound (Optional[np.ndarray]): Custom lower HSV bound
        upper_bound (Optional[np.ndarray]): Custom upper HSV bound
        use_copper_color (bool): If True, use copper/gold color bounds instead of green
        
    Returns:
        np.ndarray: Binary image with tracks in white (255) and background in black (0)
    """
    try:
        # Load the image
        img = load_image(image_path)
        
        # Convert BGR to HSV color space
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        logger.info("Converted image to HSV color space")
        
        # Determine color bounds to use
        if lower_bound is not None and upper_bound is not None:
            lower = lower_bound
            upper = upper_bound
            logger.info("Using custom color bounds")
        elif use_copper_color:
            lower = COPPER_LOWER_BOUND
            upper = COPPER_UPPER_BOUND
            logger.info("Using copper/gold color bounds")
        else:
            lower = DEFAULT_LOWER_BOUND
            upper = DEFAULT_UPPER_BOUND
            logger.info("Using default green PCB bounds")
        
        # Create color mask to isolate copper tracks
        mask = cv2.inRange(hsv, lower, upper)
        logger.info("Applied color mask")
        
        # Apply morphological operations to clean up the mask
        # Opening: removes small noise (erosion followed by dilation)
        kernel_open = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=2)
        logger.info("Applied morphological opening")
        
        # Closing: fills small holes (dilation followed by erosion)
        kernel_close = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        logger.info("Applied morphological closing")
        
        # Invert the mask so tracks are white on black background
        binary_tracks = cv2.bitwise_not(mask)
        
        logger.info(f"Track extraction complete. Binary image shape: {binary_tracks.shape}")
        
        return binary_tracks
        
    except Exception as e:
        logger.error(f"Error during track extraction: {str(e)}")
        raise


def find_track_contours(binary_image: np.ndarray) -> list:
    """
    Find contours of copper tracks in binary image.
    
    Args:
        binary_image (np.ndarray): Binary image with tracks in white
        
    Returns:
        list: List of contours (each contour is an array of points)
    """
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    logger.info(f"Found {len(contours)} track contours")
    return contours


def save_binary_image(binary_image: np.ndarray, output_path: str):
    """
    Save the binary track image to file.
    
    Args:
        binary_image (np.ndarray): Binary image to save
        output_path (str): Path to save the image
    """
    cv2.imwrite(output_path, binary_image)
    logger.info(f"Saved binary track image to {output_path}")


def get_track_mask_at_point(binary_image: np.ndarray, x: int, y: int, 
                           margin: int = 5) -> bool:
    """
    Check if there's a track (white pixel) at or near a specific point.
    
    This is used for checking if a track touches a component bounding box.
    
    Args:
        binary_image (np.ndarray): Binary track image
        x (int): X coordinate
        y (int): Y coordinate
        margin (int): Pixel margin to check around the point
        
    Returns:
        bool: True if track pixel found within margin
    """
    h, w = binary_image.shape
    
    # Check region around the point
    x_min = max(0, x - margin)
    x_max = min(w, x + margin)
    y_min = max(0, y - margin)
    y_max = min(h, y + margin)
    
    # Extract region
    region = binary_image[y_min:y_max, x_min:x_max]
    
    # Check if any white pixels (tracks) exist in region
    return np.any(region > 127)  # 127 is threshold for "white"


def check_track_component_overlap(binary_image: np.ndarray, 
                                  bbox: dict,
                                  sample_points: int = 8,
                                  min_hit_ratio: float = 0.3) -> bool:
    """
    Check if any tracks overlap with a component's bounding box.
    
    Samples multiple points around the bbox perimeter to detect overlap.
    
    Args:
        binary_image (np.ndarray): Binary track image
        bbox (dict): Component bounding box with x, y, width, height
        sample_points (int): Number of points to sample on each edge
        
    Returns:
        bool: True if tracks overlap with component bbox. To reduce false
              positives from noisy masks, this requires that a minimum
              fraction (min_hit_ratio) of sampled perimeter points actually
              touch tracks, instead of accepting a single hit.
    """
    x_center = int(bbox['x'])
    y_center = int(bbox['y'])
    width = int(bbox['width'])
    height = int(bbox['height'])
    
    # Calculate bbox corners
    x1 = x_center - width // 2
    y1 = y_center - height // 2
    x2 = x_center + width // 2
    y2 = y_center + height // 2
    
    # Sample points along each edge of the bounding box
    points_to_check = []
    
    # Top edge
    for i in range(sample_points):
        x = x1 + (x2 - x1) * i // sample_points
        points_to_check.append((x, y1))
    
    # Bottom edge
    for i in range(sample_points):
        x = x1 + (x2 - x1) * i // sample_points
        points_to_check.append((x, y2))
    
    # Left edge
    for i in range(sample_points):
        y = y1 + (y2 - y1) * i // sample_points
        points_to_check.append((x1, y))
    
    # Right edge
    for i in range(sample_points):
        y = y1 + (y2 - y1) * i // sample_points
        points_to_check.append((x2, y))
    
    # Check how many points have a track
    track_hits = 0
    for x, y in points_to_check:
        if get_track_mask_at_point(binary_image, x, y):
            track_hits += 1
    
    if not points_to_check:
        return False
    
    hit_ratio = track_hits / len(points_to_check)
    return hit_ratio >= min_hit_ratio

