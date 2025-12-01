"""
Component Detection Module using Roboflow YOLOv8 with Slicing

This module connects to Roboflow's serverless API to detect PCB components
using a pre-trained YOLOv8 model. It implements slicing/tiling for accurate
detection of small components on large PCB images.
"""

from inference_sdk import InferenceHTTPClient
from typing import List, Dict, Any
import logging
from PIL import Image
import tempfile
import os

import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CRITICAL: Roboflow Configuration
# API URL and Key for the PCB Components Detection Model
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="eR0Kuw3FILGj8ItY6dVj"
)

# Model ID for PCB Component Detection
MODEL_ID = "pcb-components-mechu/6"

# Detection Parameters
CONFIDENCE_THRESHOLD = 0.25  # Lower threshold to catch small components
IOU_THRESHOLD = 0.4          # For NMS to remove duplicate detections
SLICE_SIZE = 640             # Size of each slice (640x640 pixels)
OVERLAP_RATIO = 0.2          # 20% overlap between slices


def detect_components(image_path: str, use_slicing: bool = True) -> Dict[str, Any]:
    """
    Detect PCB components in an image using Roboflow YOLOv8 model with slicing.
    
    SLICING LOGIC:
    Large PCB images are split into overlapping 640x640 tiles to ensure small
    components (like SMD resistors) are detected accurately without losing
    detail due to resizing. We run inference on each tile separately and then
    merge predictions in the original image coordinate space using a custom
    Non-Maximum Suppression (NMS) implementation.
    
    Args:
        image_path (str): Path to the PCB image file
        use_slicing (bool): Whether to use slicing (default: True for large images)
        
    Returns:
        Dict containing detection results with predictions list
        
    Raises:
        Exception: If detection fails or API call errors
    """
    try:
        logger.info(f"Starting component detection for image: {image_path}")
        
        # Check image size to determine if slicing is needed
        img = Image.open(image_path)
        img_width, img_height = img.size
        logger.info(f"Image dimensions: {img_width}x{img_height}")
        
        # Determine if slicing should be used.
        # Use slicing for images larger than 800x800 or if explicitly requested.
        should_slice = use_slicing and (img_width > 800 or img_height > 800)

        if should_slice:
            logger.info(
                f"Using MANUAL SLICING inference "
                f"(slice_size={SLICE_SIZE}, overlap={OVERLAP_RATIO})"
            )
            logger.info(
                "Splitting image into overlapping tiles and running inference "
                "on each tile separately."
            )

            merged_predictions: List[Dict[str, Any]] = []

            step = int(SLICE_SIZE * (1.0 - OVERLAP_RATIO))
            if step <= 0:
                step = SLICE_SIZE  # Fallback to no overlap if misconfigured

            # Slide a window over the image
            for top in range(0, img_height, step):
                for left in range(0, img_width, step):
                    right = min(left + SLICE_SIZE, img_width)
                    bottom = min(top + SLICE_SIZE, img_height)

                    # Adjust start if at the edge to keep tile size roughly SLICE_SIZE
                    if right - left < SLICE_SIZE and img_width > SLICE_SIZE:
                        left = max(0, right - SLICE_SIZE)
                    if bottom - top < SLICE_SIZE and img_height > SLICE_SIZE:
                        top = max(0, bottom - SLICE_SIZE)

                    tile_box = (left, top, right, bottom)
                    tile = img.crop(tile_box)

                    # Save tile to a temporary file so inference-sdk can read it
                    fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
                    os.close(fd)
                    try:
                        tile.save(tmp_path, format="JPEG")
                        tile_result = CLIENT.infer(tmp_path, model_id=MODEL_ID)
                    finally:
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

                    for pred in tile_result.get("predictions", []):
                        # Convert tile-relative coordinates to image coordinates
                        new_pred = dict(pred)
                        new_pred["x"] = pred.get("x", 0) + left
                        new_pred["y"] = pred.get("y", 0) + top
                        merged_predictions.append(new_pred)

            logger.info(
                f"Slicing complete. Raw predictions collected from all tiles: "
                f"{len(merged_predictions)}"
            )

            final_predictions = _non_max_suppression(
                merged_predictions,
                iou_threshold=IOU_THRESHOLD,
                confidence_threshold=CONFIDENCE_THRESHOLD,
            )

            result = {"predictions": final_predictions}

        else:
            logger.info(
                "Using STANDARD inference (image smaller than 800x800 or "
                "slicing disabled)"
            )

            result = CLIENT.infer(image_path, model_id=MODEL_ID)
            raw_predictions = result.get("predictions", [])
            final_predictions = _non_max_suppression(
                raw_predictions,
                iou_threshold=IOU_THRESHOLD,
                confidence_threshold=CONFIDENCE_THRESHOLD,
            )
            result["predictions"] = final_predictions

        num_detections = len(result.get("predictions", []))
        logger.info(f"Detection complete. Found {num_detections} components")

        if num_detections == 0:
            logger.warning("No components detected. This may indicate:")
            logger.warning("  - PCB image quality issues")
            logger.warning("  - Components too small or unclear")
            logger.warning("  - Wrong image type (not a PCB)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during component detection: {str(e)}")
        raise


def parse_detections(raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse raw Roboflow detection results into structured component list.
    
    Args:
        raw_result (Dict): Raw response from Roboflow API
        
    Returns:
        List of dictionaries containing:
            - class_name (str): Component type (e.g., "Resistor", "IC", "Capacitor")
            - confidence (float): Detection confidence score (0-1)
            - bbox (Dict): Bounding box with keys: x, y, width, height
    """
    components = []
    
    predictions = raw_result.get('predictions', [])
    
    for pred in predictions:
        component = {
            'class_name': pred.get('class', 'Unknown'),
            'confidence': pred.get('confidence', 0.0),
            'bbox': {
                'x': pred.get('x', 0),
                'y': pred.get('y', 0),
                'width': pred.get('width', 0),
                'height': pred.get('height', 0)
            }
        }
        components.append(component)
    
    logger.info(f"Parsed {len(components)} components from detection results")
    
    return components


def _bbox_to_corners(pred: Dict[str, Any]) -> Dict[str, float]:
    """
    Convert a prediction with centre/width/height to corner coordinates.
    
    Roboflow predictions use (x, y, width, height) with (x, y) as the box
    centre. For IoU we convert to (x1, y1, x2, y2).
    """
    x_c = float(pred.get("x", 0.0))
    y_c = float(pred.get("y", 0.0))
    w = float(pred.get("width", 0.0))
    h = float(pred.get("height", 0.0))

    x1 = x_c - w / 2.0
    y1 = y_c - h / 2.0
    x2 = x_c + w / 2.0
    y2 = y_c + h / 2.0

    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _compute_iou(pred1: Dict[str, Any], pred2: Dict[str, Any]) -> float:
    """
    Compute Intersection-over-Union (IoU) between two predictions.
    """
    b1 = _bbox_to_corners(pred1)
    b2 = _bbox_to_corners(pred2)

    x_left = max(b1["x1"], b2["x1"])
    y_top = max(b1["y1"], b2["y1"])
    x_right = min(b1["x2"], b2["x2"])
    y_bottom = min(b1["y2"], b2["y2"])

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    area1 = (b1["x2"] - b1["x1"]) * (b1["y2"] - b1["y1"])
    area2 = (b2["x2"] - b2["x1"]) * (b2["y2"] - b2["y1"])

    if area1 <= 0 or area2 <= 0:
        return 0.0

    union_area = area1 + area2 - intersection_area
    return intersection_area / union_area


def _non_max_suppression(
    predictions: List[Dict[str, Any]],
    iou_threshold: float,
    confidence_threshold: float,
) -> List[Dict[str, Any]]:
    """
    Simple Non-Maximum Suppression (NMS) implementation.
    
    - Filters out predictions below the confidence threshold.
    - Sorts remaining predictions by confidence (high → low).
    - Keeps a prediction only if its IoU with all kept predictions is below
      the IoU threshold.
    """
    # Filter by confidence first
    preds = [
        p for p in predictions
        if float(p.get("confidence", 0.0)) >= confidence_threshold
    ]

    if not preds:
        return []

    # Sort by confidence descending
    preds.sort(key=lambda p: float(p.get("confidence", 0.0)), reverse=True)

    kept: List[Dict[str, Any]] = []
    for cand in preds:
        discard = False
        for kp in kept:
            iou = _compute_iou(cand, kp)
            if iou >= iou_threshold:
                discard = True
                break
        if not discard:
            kept.append(cand)

    logger.info(
        f"NMS reduced {len(predictions)} raw predictions to {len(kept)} "
        f"final predictions (confidence>={confidence_threshold}, IoU<{iou_threshold})"
    )
    return kept


def filter_low_confidence(components: List[Dict[str, Any]], 
                         threshold: float = 0.25) -> List[Dict[str, Any]]:
    """
    Filter out components with confidence below threshold.
    
    Args:
        components (List): List of detected components
        threshold (float): Minimum confidence threshold (default: 0.25)
        
    Returns:
        List of components with confidence >= threshold
    """
    filtered = [comp for comp in components if comp['confidence'] >= threshold]
    
    logger.info(f"Filtered {len(components) - len(filtered)} low-confidence detections")
    
    return filtered

