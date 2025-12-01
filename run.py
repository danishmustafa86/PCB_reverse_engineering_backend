"""
Application Runner Script

Simple script to start the FastAPI server with optimal settings.
"""

import uvicorn
import os
import sys

def main():
    """
    Run the FastAPI application with uvicorn.
    """
    print("=" * 60)
    print("PCB Reverse Engineering System - Backend Server")
    print("=" * 60)
    print()
    print("Starting FastAPI server...")
    print()
    print("Server will be available at:")
    print("  - API Base:        http://localhost:8000")
    print("  - Documentation:   http://localhost:8000/docs")
    print("  - Alternative:     http://localhost:8000/redoc")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    try:
        # Run the application
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError starting server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

