# Installation Guide - PCB Reverse Engineering System

Complete step-by-step installation guide for Windows, Linux, and macOS.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Windows Installation](#windows-installation)
- [Linux/Mac Installation](#linuxmac-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - **Important for Windows**: Check "Add Python to PATH" during installation

2. **pip** (Python package manager)
   - Usually comes with Python
   - Verify: `python -m pip --version`

3. **Git** (optional, for cloning)
   - Download from: https://git-scm.com/

### System Requirements

- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 2GB free space (for Python packages and models)
- **Internet**: Required for first-time model downloads (EasyOCR)

---

## Windows Installation

### Method 1: Automated Setup (Recommended)

1. **Open Command Prompt** in the project directory
   - Right-click folder → "Open in Terminal" or "Open PowerShell here"

2. **Run setup script**:
   ```cmd
   setup.bat
   ```

3. **Wait for installation** (5-10 minutes)
   - Script will create virtual environment
   - Install all dependencies

4. **Start the server**:
   ```cmd
   start.bat
   ```

### Method 2: Manual Setup

1. **Open Command Prompt** in project directory

2. **Create virtual environment**:
   ```cmd
   python -m venv venv
   ```

3. **Activate virtual environment**:
   ```cmd
   venv\Scripts\activate
   ```
   
   Your prompt should now show `(venv)` prefix.

4. **Upgrade pip**:
   ```cmd
   python -m pip install --upgrade pip
   ```

5. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```
   
   This will take 5-10 minutes.

6. **Start the server**:
   ```cmd
   python run.py
   ```

---

## Linux/Mac Installation

### Method 1: Using bash script

1. **Open Terminal** in project directory

2. **Create and run setup script**:
   ```bash
   chmod +x setup.sh  # Make executable
   ./setup.sh
   ```

### Method 2: Manual Setup

1. **Open Terminal** in project directory

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment**:
   ```bash
   # Linux/Mac
   source venv/bin/activate
   ```
   
   Your prompt should now show `(venv)` prefix.

4. **Upgrade pip**:
   ```bash
   pip install --upgrade pip
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Start the server**:
   ```bash
   python run.py
   ```

---

## Verification

### 1. Check Installation

After installation completes, verify packages:

```bash
python -c "import fastapi, inference_sdk, easyocr, cv2, networkx, schemdraw; print('✓ All packages installed successfully!')"
```

Expected output: `✓ All packages installed successfully!`

### 2. Start the Server

```bash
python run.py
```

You should see:
```
PCB Reverse Engineering System - Backend Server
============================================================
Starting FastAPI server...

Server will be available at:
  - API Base:        http://localhost:8000
  - Documentation:   http://localhost:8000/docs
  - Alternative:     http://localhost:8000/redoc
```

### 3. Test the API

Open your browser and visit:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the interactive API documentation.

### 4. Run Test Script

In a **new terminal** (keep server running), activate venv and run:

```bash
# Windows
venv\Scripts\activate
python test_api.py

# Linux/Mac
source venv/bin/activate
python test_api.py
```

---

## Troubleshooting

### Issue: "Python is not recognized"

**Windows**:
1. Reinstall Python and check "Add Python to PATH"
2. Or manually add to PATH:
   - Search "Environment Variables" in Start Menu
   - Add Python install directory to PATH

**Linux/Mac**:
```bash
# Use python3 instead of python
python3 --version
```

### Issue: "pip is not recognized"

```bash
# Use python -m pip instead
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Issue: "Permission Denied" (Linux/Mac)

```bash
# Use sudo or fix permissions
sudo pip install -r requirements.txt

# Or use --user flag
pip install --user -r requirements.txt
```

### Issue: "Failed to install opencv-python"

**Windows**: Install Visual C++ Redistributable
- Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

**Linux**:
```bash
sudo apt-get update
sudo apt-get install python3-opencv
```

**Mac**:
```bash
brew install opencv
```

### Issue: "EasyOCR is very slow"

**Normal behavior**: First run downloads models (~100MB) and takes time.

**Enable GPU** (if you have NVIDIA GPU with CUDA):
1. Install CUDA Toolkit
2. Install PyTorch with CUDA:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```
3. In `app/services/ocr_service.py`, change:
   ```python
   reader = easyocr.Reader(['en'], gpu=True)  # Enable GPU
   ```

### Issue: Port 8000 already in use

Change port in `run.py` or use environment variable:

```bash
# Windows
set PORT=8080
python run.py

# Linux/Mac
PORT=8080 python run.py
```

### Issue: "ModuleNotFoundError: No module named 'app'"

Make sure you're in the project root directory and virtual environment is activated:

```bash
# Check current directory
pwd  # Linux/Mac
cd   # Windows

# Should show: .../PCB_reverse_engineering
```

### Issue: Requirements installation fails

Try installing packages individually:

```bash
pip install fastapi uvicorn
pip install python-multipart
pip install inference-sdk
pip install easyocr
pip install opencv-python numpy Pillow
pip install networkx
pip install schemdraw matplotlib
```

### Issue: "Address already in use"

Kill process using port 8000:

**Windows**:
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac**:
```bash
lsof -ti:8000 | xargs kill -9
```

---

## Post-Installation

### Optional: Configure for Production

1. **Set environment variables**:
   ```bash
   # .env file
   HOST=0.0.0.0
   PORT=8000
   RELOAD=False
   ```

2. **Use production ASGI server**:
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Optional: Enable HTTPS

For production deployment, use a reverse proxy like Nginx or use Caddy.

---

## Getting Help

If you encounter issues not covered here:

1. Check the main [README.md](README.md)
2. Review server logs for detailed error messages
3. Ensure all prerequisites are met
4. Try reinstalling in a fresh virtual environment

---

## Next Steps

Once installation is complete:

1. Read the [README.md](README.md) for API usage
2. Try the `/docs` endpoint for interactive testing
3. Use `test_api.py` to test with your PCB images
4. Review code in `app/` directory to understand the pipeline

---

**Installation complete! Happy PCB reverse engineering! 🔧🔍**

