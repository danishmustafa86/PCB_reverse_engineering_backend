# Quick Start Guide - PCB Reverse Engineering System

Get up and running in 5 minutes!

## 🚀 Ultra-Fast Setup

### Windows Users

```cmd
# 1. Setup (5-10 minutes)
setup.bat

# 2. Start server
start.bat
```

### Linux/Mac Users

```bash
# 1. Setup (5-10 minutes)
chmod +x setup.sh
./setup.sh

# 2. Start server
source venv/bin/activate
python run.py
```

---

## ✅ Verify Installation

Once the server starts, you should see:

```
============================================================
PCB Reverse Engineering System - Backend Server
============================================================

Starting FastAPI server...

Server will be available at:
  - API Base:        http://localhost:8000
  - Documentation:   http://localhost:8000/docs
```

### Test the API

**Option 1: Browser**
- Open: http://localhost:8000/docs
- You'll see interactive API documentation

**Option 2: Test Script**
```bash
# In a NEW terminal (keep server running)
python test_api.py
```

---

## 📤 Analyze Your First PCB

### Method 1: Interactive Docs (Easiest)

1. Open http://localhost:8000/docs
2. Click on `POST /analyze`
3. Click "Try it out"
4. Click "Choose File" and select a PCB image
5. Click "Execute"
6. View results below!

### Method 2: Python Script

```python
import requests

# Replace with your image path
image_path = "path/to/your/pcb_image.jpg"

with open(image_path, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/analyze', files=files)
    
result = response.json()
print(f"✅ Detected {result['analysis']['component_count']} components")
print(f"📊 Found {result['analysis']['connection_count']} connections")
print(f"🖼️ Schematic: {result['files']['schematic_url']}")
```

### Method 3: cURL

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@pcb_image.jpg"
```

---

## 📁 Results Location

After analysis, find your results in:

```
static/
├── uploads/
│   └── pcb_20231201_120000.jpg      # Original image
└── results/
    ├── schematic_20231201_120000.png     # Circuit diagram
    ├── annotated_20231201_120000.png     # Image with boxes
    ├── tracks_20231201_120000.png        # Track segmentation
    └── netlist_20231201_120000.txt       # Connection list
```

Access via browser:
- http://localhost:8000/static/results/schematic_20231201_120000.png

---

## 📊 Understanding Results

### Component Detection
```json
"components": [
  {
    "id": "R1",                // Component identifier
    "type": "Resistor",        // Component type
    "confidence": 0.95,        // Detection confidence
    "box": {                   // Position on PCB
      "x": 150, "y": 200,
      "width": 45, "height": 30
    }
  }
]
```

### Netlist (Connections)
```json
"netlist": [
  "R1 -- U1",      // R1 connected to U1
  "U1 -- C1",      // U1 connected to C1
  "C1 -- R2"       // C1 connected to R2
]
```

---

## 🎯 Best Practices

### For Best Results:

1. **Image Quality**
   - ✅ Good lighting, no shadows
   - ✅ Clear focus
   - ✅ Resolution: 1000x1000 to 2000x2000 pixels
   - ❌ Avoid: blurry, dark, or low-resolution images

2. **PCB Orientation**
   - ✅ Flat, perpendicular view
   - ✅ Component labels facing up
   - ❌ Avoid: angled shots

3. **PCB Type**
   - ✅ Single-layer or visible top layer
   - ✅ Standard green PCB
   - ⚠️ Multi-layer boards: only top layer analyzed

---

## 🔧 Common Issues

### "No components detected"
**Solution**: Check image quality, lighting, and ensure components are visible

### "Server not starting"
**Solution**: 
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000  # Windows
lsof -i :8000                # Linux/Mac

# Change port
set PORT=8080                # Windows
PORT=8080 python run.py      # Linux/Mac
```

### "ModuleNotFoundError"
**Solution**: Activate virtual environment
```bash
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
```

### OCR is very slow (first run)
**Normal behavior**: EasyOCR downloads models (~100MB) on first use. Subsequent runs are faster.

---

## 📚 Next Steps

1. **Read Full Documentation**
   - [README.md](README.md) - Main documentation
   - [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API reference
   - [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Architecture details

2. **Test with Your Images**
   - Try different PCB types
   - Compare results
   - Adjust parameters if needed

3. **Integrate into Your Workflow**
   - Use Python SDK
   - Build a frontend
   - Automate batch processing

---

## 💡 Pro Tips

### Speed Up Processing
```python
# In app/services/ocr_service.py, if you have CUDA GPU:
reader = easyocr.Reader(['en'], gpu=True)  # Enable GPU
```

### Adjust Track Detection
```python
# In app/services/tracer.py
binary_track_image = tracer.extract_copper_tracks(
    image_path, 
    use_copper_color=True  # Try this for copper-colored PCBs
)
```

### Batch Processing
```python
import os
import requests

pcb_folder = "path/to/pcb/images"
for filename in os.listdir(pcb_folder):
    if filename.endswith(('.jpg', '.png')):
        with open(os.path.join(pcb_folder, filename), 'rb') as f:
            files = {'file': f}
            response = requests.post('http://localhost:8000/analyze', files=files)
            print(f"Processed {filename}: {response.status_code}")
```

---

## 🎓 Example Workflow

```python
import requests
import json

# 1. Analyze PCB
with open('my_pcb.jpg', 'rb') as f:
    response = requests.post('http://localhost:8000/analyze', files={'file': f})

result = response.json()

# 2. Extract components
components = result['analysis']['components']
print(f"Found {len(components)} components:")
for comp in components:
    print(f"  - {comp['id']}: {comp['type']}")

# 3. Extract netlist
netlist = result['analysis']['netlist']
print(f"\nConnections:")
for conn in netlist:
    print(f"  - {conn}")

# 4. Download schematic
schematic_url = result['files']['schematic_url']
schematic_response = requests.get(f"http://localhost:8000{schematic_url}")
with open('schematic.png', 'wb') as f:
    f.write(schematic_response.content)
print(f"\nSchematic saved to schematic.png")
```

---

## 📞 Getting Help

**Check Documentation**:
- API docs: http://localhost:8000/docs
- This guide: [QUICK_START.md](QUICK_START.md)
- Full guide: [README.md](README.md)
- Installation: [INSTALLATION.md](INSTALLATION.md)

**Common Resources**:
- Requirements: [requirements.txt](requirements.txt)
- Test script: [test_api.py](test_api.py)
- Main code: [app/main.py](app/main.py)

---

## ⚙️ Configuration

### Change Server Settings

Edit `run.py` or set environment variables:

```bash
# Windows
set HOST=0.0.0.0
set PORT=8080
set RELOAD=True
python run.py

# Linux/Mac
HOST=0.0.0.0 PORT=8080 RELOAD=True python run.py
```

### Adjust Detection Confidence

In your analysis request, components with confidence < 0.3 are filtered out.

To adjust, edit `app/main.py`:
```python
detected_components = detector.filter_low_confidence(
    detected_components, 
    threshold=0.5  # Change this value (0.0 to 1.0)
)
```

---

## ✨ Summary

```bash
# Install
setup.bat              # or ./setup.sh on Linux/Mac

# Run
start.bat              # or python run.py

# Test
http://localhost:8000/docs

# Analyze
POST /analyze with PCB image

# Results
static/results/schematic_*.png
```

---

**🎉 You're all set! Happy PCB reverse engineering!**

For detailed documentation, see [README.md](README.md)

