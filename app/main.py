"""
FastAPI Backend for AI-based PCB Reverse Engineering System

This is the main entry point for the FastAPI application.
It orchestrates the entire PCB analysis pipeline:
1. Component Detection (Roboflow YOLOv8)
2. OCR Text Recognition (EasyOCR)
3. Copper Track Tracing (OpenCV)
4. Circuit Graph Building (NetworkX)
5. Schematic Generation (Schemdraw)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any
import logging

# Import our custom services
from app.services import detector, ocr_service, tracer, schematic_builder
from app.utils import image_processing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PCB Reverse Engineering API",
    description="AI-based system for PCB component detection, track tracing, and schematic generation",
    version="1.0.0"
)

# Enable CORS (for frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Directory for uploaded images
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Directory for generated results
RESULTS_DIR = os.path.join(STATIC_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup.
    """
    logger.info("Starting PCB Reverse Engineering API...")
    
    # Initialize EasyOCR reader (can take a few seconds)
    logger.info("Initializing OCR service...")
    ocr_service.initialize_ocr()
    
    logger.info("API startup complete. Ready to process PCB images.")


@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "message": "PCB Reverse Engineering API",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze": "Analyze PCB image and generate schematic",
            "GET /health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/analyze")
async def analyze_pcb(file: UploadFile = File(...)):
    """
    Main endpoint: Analyze PCB image and generate schematic.
    
    This endpoint orchestrates the entire PCB analysis pipeline:
    1. Save uploaded image
    2. Detect components using Roboflow YOLOv8
    3. Run OCR on detected components to get names/values
    4. Trace copper tracks using OpenCV
    5. Build circuit graph and generate netlist
    6. Draw schematic diagram
    
    Args:
        file (UploadFile): PCB image file
        
    Returns:
        JSONResponse: Analysis results including components, netlist, and schematic URL
    """
    try:
        logger.info(f"Received PCB image: {file.filename}")
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, 
                              detail="File must be an image (JPEG, PNG, etc.)")
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"pcb_{timestamp}{file_extension}"
        image_path = os.path.join(UPLOAD_DIR, saved_filename)
        
        # Save uploaded file
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded image to {image_path}")
        
        # ===== STEP 1: Component Detection =====
        logger.info("STEP 1: Detecting components with Roboflow YOLOv8 + Slicing...")
        raw_detection_result = detector.detect_components(image_path)
        detected_components = detector.parse_detections(raw_detection_result)
        
        # Filter low-confidence detections (lower threshold for small components)
        detected_components = detector.filter_low_confidence(detected_components, threshold=0.25)
        
        logger.info(f"Detected {len(detected_components)} components")
        
        if len(detected_components) == 0:
            logger.warning("No components detected in image")
            return JSONResponse(
                status_code=200,
                content={
                    "message": "No components detected in the image",
                    "components": [],
                    "netlist": [],
                    "schematic_url": None
                }
            )
        
        # ===== STEP 2: OCR and Component Naming =====
        logger.info("STEP 2: Running OCR and assigning component names...")
        
        # Reset component counters for new analysis
        ocr_service.reset_counters()
        
        # Process each component to get final names
        components_with_names = []
        for comp in detected_components:
            # Get component name using OCR or generic ID
            component_name = ocr_service.get_component_name(image_path, comp)
            
            components_with_names.append({
                'id': component_name,
                'type': comp['class_name'],
                'confidence': comp['confidence'],
                'bbox': comp['bbox']
            })
        
        logger.info(f"Component naming complete: {[c['id'] for c in components_with_names]}")
        
        # ===== STEP 3: Copper Track Tracing =====
        logger.info("STEP 3: Tracing copper tracks with OpenCV...")
        binary_track_image = tracer.extract_copper_tracks(image_path, use_copper_color=False)
        
        # Save binary track image for debugging
        track_image_path = os.path.join(RESULTS_DIR, f"tracks_{timestamp}.png")
        tracer.save_binary_image(binary_track_image, track_image_path)
        logger.info(f"Saved track image to {track_image_path}")
        
        # ===== STEP 4: Build Circuit Graph =====
        logger.info("STEP 4: Building circuit graph and netlist...")
        circuit_graph = schematic_builder.build_circuit_graph(
            components_with_names, 
            binary_track_image
        )
        
        netlist = circuit_graph.get_netlist()
        logger.info(f"Generated netlist with {len(netlist)} connections")
        
        # ===== STEP 5: Generate Schematic =====
        logger.info("STEP 5: Generating schematic diagram...")
        schematic_path = os.path.join(RESULTS_DIR, f"schematic_{timestamp}.png")
        schematic_builder.draw_schematic(circuit_graph, schematic_path)
        
        # Generate netlist text file
        netlist_path = os.path.join(RESULTS_DIR, f"netlist_{timestamp}.txt")
        schematic_builder.generate_netlist_report(circuit_graph, netlist_path)
        
        # Create annotated image with bounding boxes
        original_image = image_processing.load_image(image_path)
        annotated_image = image_processing.draw_bounding_boxes(
            original_image, 
            components_with_names,
            color=(0, 255, 0),
            thickness=3
        )
        annotated_path = os.path.join(RESULTS_DIR, f"annotated_{timestamp}.png")
        image_processing.save_image(annotated_image, annotated_path)
        
        logger.info("PCB analysis complete!")
        
        # ===== Prepare Response =====
        # Format components for response
        components_response = []
        for comp in components_with_names:
            components_response.append({
                'id': comp['id'],
                'type': comp['type'],
                'confidence': round(comp['confidence'], 3),
                'box': {
                    'x': int(comp['bbox']['x']),
                    'y': int(comp['bbox']['y']),
                    'width': int(comp['bbox']['width']),
                    'height': int(comp['bbox']['height'])
                }
            })
        
        # Build response
        response_data = {
            "success": True,
            "message": "PCB analysis completed successfully",
            "analysis": {
                "components": components_response,
                "component_count": len(components_response),
                "netlist": netlist,
                "connection_count": len(netlist)
            },
            "files": {
                "schematic_url": f"/static/results/{os.path.basename(schematic_path)}",
                "annotated_image_url": f"/static/results/{os.path.basename(annotated_path)}",
                "track_image_url": f"/static/results/{os.path.basename(track_image_path)}",
                "netlist_file_url": f"/static/results/{os.path.basename(netlist_path)}",
                "original_image_url": f"/static/uploads/{saved_filename}"
            },
            "timestamp": timestamp
        }
        
        logger.info("Returning analysis results to client")
        
        return JSONResponse(status_code=200, content=response_data)
        
    except Exception as e:
        logger.error(f"Error during PCB analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during analysis: {str(e)}"
        )


@app.get("/results/{filename}")
async def get_result_file(filename: str):
    """
    Download a result file (schematic, netlist, etc.)
    
    Args:
        filename (str): Name of the file
        
    Returns:
        FileResponse: The requested file
    """
    file_path = os.path.join(RESULTS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


@app.delete("/cleanup")
async def cleanup_old_files(max_age_hours: int = 24):
    """
    Clean up old uploaded and result files.
    
    Args:
        max_age_hours (int): Maximum age of files to keep in hours
        
    Returns:
        Dict: Cleanup statistics
    """
    try:
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        
        # Clean upload directory
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    deleted_count += 1
        
        # Clean results directory
        for filename in os.listdir(RESULTS_DIR):
            file_path = os.path.join(RESULTS_DIR, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    deleted_count += 1
        
        logger.info(f"Cleanup complete: deleted {deleted_count} old files")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")


# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

