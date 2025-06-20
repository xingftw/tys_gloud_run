#!/usr/bin/env python3
"""
Simple test script to call the process_homebase_files function directly.
This simulates how the function would be called from Google Cloud Platform.
"""

import os
import sys
from flask import Request
from werkzeug.test import EnvironBuilder

# Import the function from main.py
from main import process_homebase_files

def create_mock_request():
    """Create a mock Flask request object."""
    builder = EnvironBuilder(
        method='POST',
        data={},  # Empty data since our function doesn't use request data
    )
    env = builder.get_environ()
    request = Request(env)
    return request

def main():
    """Main function to test process_homebase_files."""
    print("Testing process_homebase_files function...")
    
    # Create a mock request
    request = create_mock_request()
    
    # Call the function
    try:
        result = process_homebase_files(request)
        print(f"Function executed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error executing function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
