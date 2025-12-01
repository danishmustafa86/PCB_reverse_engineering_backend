# API Documentation - PCB Reverse Engineering System

Complete API reference for the PCB Reverse Engineering System backend.

## Base URL

```
http://localhost:8000
```

For production, replace with your deployed server URL.

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [GET /](#get-)
  - [GET /health](#get-health)
  - [POST /analyze](#post-analyze)
  - [GET /results/{filename}](#get-resultsfilename)
  - [DELETE /cleanup](#delete-cleanup)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)

---

## Authentication

Currently, the API does not require authentication. For production deployment, consider implementing:
- API Key authentication
- OAuth2
- JWT tokens

---

## Endpoints

### GET /

**Description**: Get API information and available endpoints.

**Request**:
```http
GET / HTTP/1.1
Host: localhost:8000
```

**Response** (200 OK):
```json
{
  "message": "PCB Reverse Engineering API",
  "version": "1.0.0",
  "endpoints": {
    "POST /analyze": "Analyze PCB image and generate schematic",
    "GET /health": "Health check endpoint"
  }
}
```

---

### GET /health

**Description**: Health check endpoint to verify API status.

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T12:00:00.000000"
}
```

---

### POST /analyze

**Description**: Main endpoint to analyze PCB image. This endpoint:
1. Detects components using YOLOv8
2. Recognizes text using OCR
3. Traces copper tracks
4. Builds circuit graph
5. Generates schematic

**Request**:
```http
POST /analyze HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="pcb.jpg"
Content-Type: image/jpeg

[Binary image data]
------WebKitFormBoundary--
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | File | Yes | PCB image file (JPEG, PNG, etc.) |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "PCB analysis completed successfully",
  "analysis": {
    "components": [
      {
        "id": "R1",
        "type": "Resistor",
        "confidence": 0.952,
        "box": {
          "x": 150,
          "y": 200,
          "width": 45,
          "height": 30
        }
      },
      {
        "id": "NE555",
        "type": "IC",
        "confidence": 0.987,
        "box": {
          "x": 300,
          "y": 250,
          "width": 80,
          "height": 60
        }
      }
    ],
    "component_count": 15,
    "netlist": [
      "R1 -- U1",
      "U1 -- C1",
      "C1 -- R2"
    ],
    "connection_count": 12
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

**Response** (400 Bad Request):
```json
{
  "detail": "File must be an image (JPEG, PNG, etc.)"
}
```

**Response** (500 Internal Server Error):
```json
{
  "detail": "Internal server error during analysis: [error message]"
}
```

**Processing Time**:
- First request: 10-20 seconds (OCR model loading)
- Subsequent requests: 3-5 seconds per image

---

### GET /results/{filename}

**Description**: Download a specific result file (schematic, netlist, etc.)

**Request**:
```http
GET /results/schematic_20231201_120000.png HTTP/1.1
Host: localhost:8000
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | string | Yes | Name of the result file |

**Response** (200 OK):
- Returns the file with appropriate content-type

**Response** (404 Not Found):
```json
{
  "detail": "File not found"
}
```

---

### DELETE /cleanup

**Description**: Clean up old uploaded and result files.

**Request**:
```http
DELETE /cleanup?max_age_hours=24 HTTP/1.1
Host: localhost:8000
```

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| max_age_hours | integer | No | 24 | Maximum age of files to keep (in hours) |

**Response** (200 OK):
```json
{
  "success": true,
  "deleted_count": 15,
  "max_age_hours": 24
}
```

**Response** (500 Internal Server Error):
```json
{
  "detail": "Cleanup error: [error message]"
}
```

---

## Data Models

### Component Object

```typescript
{
  id: string,          // Component identifier (e.g., "R1", "NE555")
  type: string,        // Component type (e.g., "Resistor", "IC")
  confidence: number,  // Detection confidence (0.0 - 1.0)
  box: {
    x: number,         // Center X coordinate
    y: number,         // Center Y coordinate
    width: number,     // Bounding box width
    height: number     // Bounding box height
  }
}
```

### Analysis Object

```typescript
{
  components: Component[],     // Array of detected components
  component_count: number,     // Total number of components
  netlist: string[],          // Array of connections (e.g., "R1 -- U1")
  connection_count: number    // Total number of connections
}
```

### Files Object

```typescript
{
  schematic_url: string,        // URL to schematic diagram PNG
  annotated_image_url: string,  // URL to image with bounding boxes
  track_image_url: string,      // URL to binary track image
  netlist_file_url: string,     // URL to netlist text file
  original_image_url: string    // URL to original uploaded image
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input (e.g., not an image) |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server-side error during processing |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Code Examples

### Python (requests)

```python
import requests
import json

# Health check
response = requests.get('http://localhost:8000/health')
print(response.json())

# Analyze PCB image
with open('pcb_image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/analyze', files=files)
    
if response.status_code == 200:
    result = response.json()
    print(f"Detected {result['analysis']['component_count']} components")
    print(f"Schematic: {result['files']['schematic_url']}")
else:
    print(f"Error: {response.json()['detail']}")
```

### JavaScript (fetch)

```javascript
// Health check
fetch('http://localhost:8000/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Analyze PCB image
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/analyze', {
  method: 'POST',
  body: formData
})
  .then(response => response.json())
  .then(data => {
    console.log(`Detected ${data.analysis.component_count} components`);
    console.log(`Schematic: ${data.files.schematic_url}`);
  })
  .catch(error => console.error('Error:', error));
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Analyze PCB image
curl -X POST "http://localhost:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@pcb_image.jpg"

# Download schematic
curl -O "http://localhost:8000/results/schematic_20231201_120000.png"

# Cleanup old files
curl -X DELETE "http://localhost:8000/cleanup?max_age_hours=24"
```

### Python (httpx - async)

```python
import httpx
import asyncio

async def analyze_pcb(image_path: str):
    async with httpx.AsyncClient() as client:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = await client.post(
                'http://localhost:8000/analyze',
                files=files,
                timeout=30.0
            )
            
        return response.json()

# Run
result = asyncio.run(analyze_pcb('pcb_image.jpg'))
print(result)
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production:
- Consider implementing rate limiting per IP
- Recommended: 10 requests per minute per IP
- Use libraries like `slowapi`

---

## File Size Limits

**Default**: No explicit limit set by the API.

**Recommended**: Configure in production:
- Max file size: 10MB
- Supported formats: JPEG, PNG, BMP, TIFF
- Recommended resolution: 500x500 to 2000x2000 pixels

---

## CORS Configuration

**Current**: All origins allowed (`*`)

**Production**: Configure specific allowed origins in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

---

## Interactive Documentation

The API includes built-in interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Test endpoints directly in the browser
- View request/response schemas
- Download OpenAPI specification

---

## Performance Notes

### First Request
- Takes 10-20 seconds
- EasyOCR downloads and loads models (~100MB)
- Models are cached for subsequent requests

### Subsequent Requests
- 3-5 seconds per image
- Depends on:
  - Image size and complexity
  - Number of components
  - System resources

### Optimization Tips
1. Use GPU for OCR if available
2. Resize large images before upload
3. Use faster storage (SSD) for model cache
4. Consider batch processing for multiple images

---

## WebSocket Support

Currently not implemented. For real-time updates during processing:
- Consider adding WebSocket endpoint
- Stream progress updates for long-running analyses
- Notify when processing stages complete

---

## Versioning

Current version: **1.0.0**

Future versions may include:
- `/v1/analyze` endpoint for version-specific API
- Breaking changes will increment major version
- Backward compatibility maintained for minor versions

---

## Support & Issues

For API-related questions:
1. Check this documentation
2. Review interactive docs at `/docs`
3. Check server logs for detailed errors
4. Review the main README.md

---

**Last Updated**: December 2023  
**API Version**: 1.0.0

