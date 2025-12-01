"""
Test Script for PCB Reverse Engineering API

This script tests the API endpoints to ensure everything is working correctly.
"""

import requests
import json
import time
from pathlib import Path


def test_health_check(base_url: str = "http://localhost:8000"):
    """
    Test the health check endpoint.
    """
    print("\n" + "=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/health")
        
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error connecting to server: {str(e)}")
        print("Make sure the server is running: python run.py")
        return False


def test_root_endpoint(base_url: str = "http://localhost:8000"):
    """
    Test the root endpoint.
    """
    print("\n" + "=" * 60)
    print("Testing Root Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/")
        
        if response.status_code == 200:
            print("✓ Root endpoint passed")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"✗ Root endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_analyze_endpoint(image_path: str, base_url: str = "http://localhost:8000"):
    """
    Test the analyze endpoint with a PCB image.
    """
    print("\n" + "=" * 60)
    print("Testing Analyze Endpoint")
    print("=" * 60)
    
    # Check if image file exists
    if not Path(image_path).exists():
        print(f"✗ Image file not found: {image_path}")
        print("Please provide a valid PCB image path")
        return False
    
    print(f"Using image: {image_path}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (Path(image_path).name, f, 'image/jpeg')}
            
            print("Sending request to server...")
            print("(This may take 10-20 seconds on first run due to OCR model loading)")
            
            start_time = time.time()
            response = requests.post(f"{base_url}/analyze", files=files)
            elapsed_time = time.time() - start_time
            
            print(f"Request completed in {elapsed_time:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n✓ Analysis completed successfully!")
                print("\nResults:")
                print("-" * 60)
                print(f"Components detected: {result['analysis']['component_count']}")
                print(f"Connections found: {result['analysis']['connection_count']}")
                
                print("\nComponents:")
                for comp in result['analysis']['components'][:5]:  # Show first 5
                    print(f"  - {comp['id']}: {comp['type']} (confidence: {comp['confidence']})")
                
                if len(result['analysis']['components']) > 5:
                    print(f"  ... and {len(result['analysis']['components']) - 5} more")
                
                print("\nConnections (Netlist):")
                for conn in result['analysis']['netlist'][:5]:  # Show first 5
                    print(f"  - {conn}")
                
                if len(result['analysis']['netlist']) > 5:
                    print(f"  ... and {len(result['analysis']['netlist']) - 5} more")
                
                print("\nGenerated Files:")
                for file_type, url in result['files'].items():
                    print(f"  - {file_type}: {url}")
                
                print("\nYou can access these files at:")
                print(f"  {base_url}{result['files']['schematic_url']}")
                
                return True
            else:
                print(f"✗ Analysis failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Error during analysis: {str(e)}")
        return False


def main():
    """
    Run all tests.
    """
    print("\n" + "=" * 60)
    print("PCB Reverse Engineering API - Test Suite")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Health Check
    health_ok = test_health_check(base_url)
    
    if not health_ok:
        print("\n✗ Server is not running or not accessible")
        print("Please start the server first: python run.py")
        return
    
    # Test 2: Root Endpoint
    root_ok = test_root_endpoint(base_url)
    
    # Test 3: Analyze Endpoint (if image path provided)
    print("\n" + "=" * 60)
    print("PCB Image Analysis Test")
    print("=" * 60)
    
    image_path = input("\nEnter path to PCB image (or press Enter to skip): ").strip()
    
    if image_path:
        analyze_ok = test_analyze_endpoint(image_path, base_url)
    else:
        print("Skipping analysis test (no image provided)")
        analyze_ok = None
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Health Check: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Root Endpoint: {'✓ PASS' if root_ok else '✗ FAIL'}")
    if analyze_ok is not None:
        print(f"Analyze Endpoint: {'✓ PASS' if analyze_ok else '✗ FAIL'}")
    else:
        print(f"Analyze Endpoint: SKIPPED")
    print("=" * 60)
    
    print("\nFor interactive API testing, visit:")
    print(f"  - {base_url}/docs")


if __name__ == "__main__":
    main()

