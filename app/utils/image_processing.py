"""
Image Processing Utility Functions

Helper functions for image manipulation, conversion, and preprocessing.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_image(image_path: str) -> np.ndarray:
    """
    Load an image from file path using OpenCV.
    
    Args:
        image_path (str): Path to image file
        
    Returns:
        np.ndarray: Loaded image in BGR format
        
    Raises:
        ValueError: If image cannot be loaded
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    logger.info(f"Loaded image: {image_path}, shape: {img.shape}")
    return img


def load_image_pil(image_path: str) -> Image.Image:
    """
    Load an image using PIL/Pillow.
    
    Args:
        image_path (str): Path to image file
        
    Returns:
        Image.Image: PIL Image object
    """
    img = Image.open(image_path)
    logger.info(f"Loaded PIL image: {image_path}, size: {img.size}, mode: {img.mode}")
    return img


def crop_image(image: np.ndarray, bbox: dict) -> np.ndarray:
    """
    Crop a region from an image using bounding box.
    
    Args:
        image (np.ndarray): Source image
        bbox (dict): Bounding box with keys: x, y, width, height
                    (x, y are center coordinates)
    
    Returns:
        np.ndarray: Cropped image region
    """
    # Convert center coordinates to corner coordinates
    x_center = int(bbox['x'])
    y_center = int(bbox['y'])
    width = int(bbox['width'])
    height = int(bbox['height'])
    
    # Calculate crop boundaries
    x1 = max(0, x_center - width // 2)
    y1 = max(0, y_center - height // 2)
    x2 = min(image.shape[1], x_center + width // 2)
    y2 = min(image.shape[0], y_center + height // 2)
    
    # Crop the image
    cropped = image[y1:y2, x1:x2]
    
    logger.debug(f"Cropped region: ({x1}, {y1}) to ({x2}, {y2})")
    
    return cropped


def resize_image(image: np.ndarray, width: Optional[int] = None, 
                height: Optional[int] = None, 
                scale: Optional[float] = None) -> np.ndarray:
    """
    Resize an image to specified dimensions or scale.
    
    Args:
        image (np.ndarray): Source image
        width (Optional[int]): Target width (if height not provided, maintains aspect ratio)
        height (Optional[int]): Target height (if width not provided, maintains aspect ratio)
        scale (Optional[float]): Scale factor (e.g., 0.5 for half size)
        
    Returns:
        np.ndarray: Resized image
    """
    if scale is not None:
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
    elif width is not None and height is not None:
        new_width = width
        new_height = height
    elif width is not None:
        aspect_ratio = image.shape[0] / image.shape[1]
        new_width = width
        new_height = int(width * aspect_ratio)
    elif height is not None:
        aspect_ratio = image.shape[1] / image.shape[0]
        new_height = height
        new_width = int(height * aspect_ratio)
    else:
        return image  # No resize parameters provided
    
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    logger.debug(f"Resized image from {image.shape} to {resized.shape}")
    
    return resized


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert an image to grayscale.
    
    Args:
        image (np.ndarray): Source image (BGR or RGB)
        
    Returns:
        np.ndarray: Grayscale image
    """
    if len(image.shape) == 2:
        return image  # Already grayscale
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    logger.debug("Converted image to grayscale")
    return gray


def enhance_contrast(image: np.ndarray, clip_limit: float = 2.0, 
                    tile_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image (np.ndarray): Source image (grayscale)
        clip_limit (float): Threshold for contrast limiting
        tile_size (Tuple[int, int]): Size of grid for histogram equalization
        
    Returns:
        np.ndarray: Contrast-enhanced image
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    enhanced = clahe.apply(image)
    
    logger.debug("Applied CLAHE contrast enhancement")
    
    return enhanced


def apply_gaussian_blur(image: np.ndarray, kernel_size: Tuple[int, int] = (5, 5),
                       sigma: float = 0) -> np.ndarray:
    """
    Apply Gaussian blur to an image.
    
    Args:
        image (np.ndarray): Source image
        kernel_size (Tuple[int, int]): Kernel size (must be odd numbers)
        sigma (float): Standard deviation (0 = auto-calculate from kernel size)
        
    Returns:
        np.ndarray: Blurred image
    """
    blurred = cv2.GaussianBlur(image, kernel_size, sigma)
    logger.debug(f"Applied Gaussian blur with kernel {kernel_size}")
    return blurred


def save_image(image: np.ndarray, output_path: str):
    """
    Save an image to file.
    
    Args:
        image (np.ndarray): Image to save
        output_path (str): Destination file path
    """
    cv2.imwrite(output_path, image)
    logger.info(f"Saved image to {output_path}")


def numpy_to_pil(image: np.ndarray) -> Image.Image:
    """
    Convert numpy array to PIL Image.
    
    Args:
        image (np.ndarray): Numpy image array (BGR or RGB)
        
    Returns:
        Image.Image: PIL Image
    """
    if len(image.shape) == 2:
        # Grayscale
        return Image.fromarray(image, mode='L')
    else:
        # Convert BGR to RGB for PIL
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """
    Convert PIL Image to numpy array.
    
    Args:
        image (Image.Image): PIL Image
        
    Returns:
        np.ndarray: Numpy array (RGB format)
    """
    return np.array(image)


def draw_bounding_boxes(image: np.ndarray, components: list, 
                       color: Tuple[int, int, int] = (0, 255, 0),
                       thickness: int = 2) -> np.ndarray:
    """
    Draw bounding boxes on an image.
    
    Args:
        image (np.ndarray): Source image
        components (list): List of components with 'bbox' dict
        color (Tuple[int, int, int]): Box color in BGR
        thickness (int): Line thickness
        
    Returns:
        np.ndarray: Image with drawn bounding boxes
    """
    img_with_boxes = image.copy()
    
    for comp in components:
        bbox = comp['bbox']
        x_center = int(bbox['x'])
        y_center = int(bbox['y'])
        width = int(bbox['width'])
        height = int(bbox['height'])
        
        # Calculate corners
        x1 = x_center - width // 2
        y1 = y_center - height // 2
        x2 = x_center + width // 2
        y2 = y_center + height // 2
        
        # Draw rectangle
        cv2.rectangle(img_with_boxes, (x1, y1), (x2, y2), color, thickness)
        
        # Draw label if available
        if 'id' in comp:
            label = comp['id']
            cv2.putText(img_with_boxes, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    logger.debug(f"Drew {len(components)} bounding boxes")
    
    return img_with_boxes


def create_overlay(base_image: np.ndarray, overlay_image: np.ndarray, 
                  alpha: float = 0.5) -> np.ndarray:
    """
    Create an overlay of two images with transparency.
    
    Args:
        base_image (np.ndarray): Base image
        overlay_image (np.ndarray): Image to overlay
        alpha (float): Transparency (0.0 = fully transparent, 1.0 = fully opaque)
        
    Returns:
        np.ndarray: Blended image
    """
    # Ensure images have same shape
    if base_image.shape != overlay_image.shape:
        overlay_image = cv2.resize(overlay_image, 
                                   (base_image.shape[1], base_image.shape[0]))
    
    blended = cv2.addWeighted(base_image, 1 - alpha, overlay_image, alpha, 0)
    
    logger.debug(f"Created overlay with alpha {alpha}")
    
    return blended

