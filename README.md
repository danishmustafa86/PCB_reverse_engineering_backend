# PCB Reverse Engineering System - Backend

AI-based PCB Reverse Engineering System using FastAPI, YOLOv8, EasyOCR, and OpenCV.

## Features

- **Component Detection**: Detect PCB components using Roboflow YOLOv8 model
- **OCR Recognition**: Read component values and part numbers using EasyOCR
- **Track Tracing**: Segment copper tracks using OpenCV color masking
- **Circuit Graph**: Build netlist using NetworkX graph analysis
- **Schematic Generation**: Generate visual schematics using Schemdraw

## Technology Stack

- **FastAPI**: Modern Python web framework
- **Roboflow**: YOLOv8 component detection API
- **EasyOCR**: Optical character recognition
- **OpenCV**: Image processing and track tracing
- **NetworkX**: Circuit graph building
- **Schemdraw**: Schematic diagram generation
- **Matplotlib**: Visualization

## Project Structure

```
PCB_reverse_engineering/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   ├── services/
│   │   ├── __init__.py
│   │   ├── detector.py              # Roboflow YOLOv8 detection
│   │   ├── ocr_service.py           # EasyOCR text recognition
│   │   ├── tracer.py                # OpenCV track tracing
│   │   └── schematic_builder.py    # NetworkX + Schemdraw
│   └── utils/
│       ├── __init__.py
│       └── image_processing.py      # Image utility functions
├── static/
│   ├── uploads/                     # Uploaded PCB images
│   └── results/                     # Generated schematics and results
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── run.py                          # Application runner script
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the repository**:
   ```bash
   cd PCB_reverse_engineering
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # Activate on Windows:
   venv\Scripts\activate
   
   # Activate on Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python -c "import fastapi, inference_sdk, easyocr, cv2; print('All dependencies installed successfully!')"
   ```

## Running the Application

### Method 1: Using Python directly

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 2: Using the run script

```bash
python run.py
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## API Endpoints

### 1. Root Endpoint
```http
GET /
```
Returns API information and available endpoints.

### 2. Health Check
```http
GET /health
```
Returns API health status.

### 3. Analyze PCB (Main Endpoint)
```http
POST /analyze
Content-Type: multipart/form-data

Parameters:
  - file: PCB image file (JPEG, PNG, etc.)
```

**Response**:
```json
{
  "success": true,
  "message": "PCB analysis completed successfully",
  "analysis": {
    "components": [
      {
        "id": "R1",
        "type": "Resistor",
        "confidence": 0.95,
        "box": {"x": 100, "y": 150, "width": 50, "height": 30}
      }
    ],
    "component_count": 10,
    "netlist": [
      "R1 -- U1",
      "U1 -- C1"
    ],
    "connection_count": 5
  },
  "files": {
    "schematic_url": "/static/results/schematic_20231201_120000.png",
    "annotated_image_url": "/static/results/annotated_20231201_120000.png",
    "track_image_url": "/static/results/tracks_20231201_120000.png",
    "netlist_file_url": "/static/results/netlist_20231201_120000.txt",
    "original_image_url": "/static/uploads/pcb_20231201_120000.jpg"
  },
  "timestamp": "20231201_120000"
}
```

### 4. Get Result File
```http
GET /results/{filename}
```
Download a specific result file.

### 5. Cleanup Old Files
```http
DELETE /cleanup?max_age_hours=24
```
Remove files older than specified hours.

## Usage Example

### Using cURL

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/pcb_image.jpg"
```

### Using Python requests

```python
import requests

url = "http://localhost:8000/analyze"
files = {'file': open('pcb_image.jpg', 'rb')}

response = requests.post(url, files=files)
result = response.json()

print(f"Detected {result['analysis']['component_count']} components")
print(f"Schematic: {result['files']['schematic_url']}")
```

## Pipeline Overview

The system processes PCB images through a 5-step pipeline:

1. **Component Detection**
   - Uses Roboflow YOLOv8 model (ID: pcb-components-r8l8r/13)
   - Detects: Resistors, Capacitors, ICs, Diodes, LEDs, Transistors, etc.
   - Returns bounding boxes and confidence scores

2. **OCR & Component Naming**
   - ICs: Uses EasyOCR to read part numbers (e.g., "NE555")
   - Small components (R/C): Assigns generic IDs (R1, R2, C1, etc.)
   - Fallback to generic IDs if OCR fails

3. **Copper Track Tracing**
   - Converts image to HSV color space
   - Applies color mask for copper/green PCB tracks
   - Uses morphological operations (opening/closing) to clean noise
   - Returns binary image (white tracks on black background)

4. **Circuit Graph Building**
   - Uses NetworkX to create component graph
   - **Intersection Logic**: Checks if tracks connect components
   - Samples bbox perimeters to detect track overlaps
   - Generates netlist of connections

5. **Schematic Generation**
   - Draws schematic using Schemdraw library
   - Fallback to NetworkX graph visualization if needed
   - Exports as PNG image
   - Generates text netlist report

## Configuration

### Roboflow API Configuration

The system uses the following Roboflow configuration (in `app/services/detector.py`):

```python
API_URL = "https://serverless.roboflow.com"
API_KEY = "eR0Kuw3FILGj8ItY6dVj"
MODEL_ID = "pcb-components-r8l8r/13"
```

### Track Color Bounds

Adjust HSV color bounds for different PCB colors in `app/services/tracer.py`:

```python
# Green PCBs (default)
DEFAULT_LOWER_BOUND = np.array([35, 40, 40])
DEFAULT_UPPER_BOUND = np.array([85, 255, 255])

# Copper/Gold colored tracks
COPPER_LOWER_BOUND = np.array([10, 50, 50])
COPPER_UPPER_BOUND = np.array([30, 255, 255])
```

## Troubleshooting

### Issue: EasyOCR is slow on first run
**Solution**: EasyOCR downloads models on first use. Subsequent runs will be faster.

### Issue: No components detected
**Solution**: 
- Ensure good image quality and lighting
- Try different PCB images
- Check that components are clearly visible
- Adjust confidence threshold in detector

### Issue: Track tracing not working
**Solution**: 
- Adjust HSV color bounds for your specific PCB color
- Try `use_copper_color=True` parameter
- Ensure good contrast between tracks and background

### Issue: ImportError or ModuleNotFoundError
**Solution**: 
```bash
pip install --upgrade -r requirements.txt
```

## Performance Notes

- **First request**: Takes 10-20 seconds (EasyOCR model loading)
- **Subsequent requests**: 3-5 seconds per image
- **GPU support**: Set `gpu=True` in OCR initialization for faster processing
- **Image size**: Works best with images 500x500 to 2000x2000 pixels

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (if test suite is created)
pytest tests/
```

## License

This project is for educational and research purposes.

## Acknowledgments

- **Roboflow**: PCB component detection model
- **EasyOCR**: OCR capabilities
- **FastAPI**: Modern web framework
- **OpenCV**: Image processing
- **NetworkX**: Graph algorithms
- **Schemdraw**: Circuit schematic drawing

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Examine log output for detailed error messages

---

**Built with ❤️ for PCB Reverse Engineering**

