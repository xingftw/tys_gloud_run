#!/usr/bin/env python3
"""
Test script to check the CSV parsing and column handling.
This script creates a test CSV file with and without the 'credit_tips' column
to verify that the code handles missing columns correctly.
"""

import os
import pandas as pd
from datetime import datetime

# Import functions from main.py
from main import parse_wage

def create_test_csv_with_credit_tips():
    """Create a test CSV file with the 'credit_tips' column."""
    csv_content = """Restore Round Rock Timesheet,May 5 2025 To May 18 2025,,,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,,
Name,Clock in date,Clock in time,Clock out date,Clock out time,Break start,Break end,Break length,Break type,Payroll ID,Role,Wage rate,Scheduled hours,Actual vs. scheduled,Total paid hours,Regular hours,Unpaid breaks,OT hours,Estimated wages,Cash tips,Credit tips,No show reason,Employee note,Manager note
John Doe,May 5 2025,9:00am,May 5 2025,5:00pm,12:00pm,1:00pm,1:00,Unpaid,12345,Technician,$15.00,8.00,0.00,7.00,7.00,1.00,0.00,$105.00,$10.00,$15.00,,,
Jane Smith,May 6 2025,8:00am,May 6 2025,4:30pm,12:00pm,12:30pm,0:30,Unpaid,67890,Manager,$20.00,8.00,0.50,8.00,8.00,0.50,0.00,$160.00,$5.00,$20.00,,,
"""
    
    with open("test_with_credit_tips.csv", "w") as f:
        f.write(csv_content)
    
    return "test_with_credit_tips.csv"

def create_test_csv_without_credit_tips():
    """Create a test CSV file without the 'credit_tips' column."""
    csv_content = """Restore Round Rock Timesheet,May 5 2025 To May 18 2025,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,
Name,Clock in date,Clock in time,Clock out date,Clock out time,Break start,Break end,Break length,Break type,Payroll ID,Role,Wage rate,Scheduled hours,Actual vs. scheduled,Total paid hours,Regular hours,Unpaid breaks,OT hours,Estimated wages,Cash tips,No show reason,Employee note,Manager note
John Doe,May 5 2025,9:00am,May 5 2025,5:00pm,12:00pm,1:00pm,1:00,Unpaid,12345,Technician,$15.00,8.00,0.00,7.00,7.00,1.00,0.00,$105.00,$10.00,,,
Jane Smith,May 6 2025,8:00am,May 6 2025,4:30pm,12:00pm,12:30pm,0:30,Unpaid,67890,Manager,$20.00,8.00,0.50,8.00,8.00,0.50,0.00,$160.00,$5.00,,,
"""
    
    with open("test_without_credit_tips.csv", "w") as f:
        f.write(csv_content)
    
    return "test_without_credit_tips.csv"

def test_with_credit_tips():
    """Test parsing a CSV file with the 'credit_tips' column."""
    print("\n=== Testing CSV with 'credit_tips' column ===")
    
    # Create test file
    test_file = create_test_csv_with_credit_tips()
    print(f"Created test file: {test_file}")
    
    try:
        # Read the CSV file
        df = pd.read_csv(test_file)
        
        print(f"CSV loaded with {len(df)} rows and {len(df.columns)} columns")
        print("Columns:", df.columns.tolist())
        
        # Check if 'credit_tips' exists
        if 'credit_tips' in df.columns:
            print("'credit_tips' column found in CSV")
            
            # Parse credit_tips
            df['credit_tips_numeric'] = df['credit_tips'].apply(parse_wage)
            print("Parsed 'credit_tips' to 'credit_tips_numeric'")
            print("Sample values:", df['credit_tips_numeric'].tolist())
        else:
            print("ERROR: 'credit_tips' column not found in CSV")
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"Removed test file: {test_file}")

def test_without_credit_tips():
    """Test parsing a CSV file without the 'credit_tips' column."""
    print("\n=== Testing CSV without 'credit_tips' column ===")
    
    # Create test file
    test_file = create_test_csv_without_credit_tips()
    print(f"Created test file: {test_file}")
    
    try:
        # Read the CSV file
        df = pd.read_csv(test_file)
        
        print(f"CSV loaded with {len(df)} rows and {len(df.columns)} columns")
        print("Columns:", df.columns.tolist())
        
        # Check if 'credit_tips' exists
        if 'credit_tips' in df.columns:
            print("'credit_tips' column found in CSV")
            
            # Parse credit_tips
            df['credit_tips_numeric'] = df['credit_tips'].apply(parse_wage)
            print("Parsed 'credit_tips' to 'credit_tips_numeric'")
            print("Sample values:", df['credit_tips_numeric'].tolist())
        else:
            print("'credit_tips' column not found in CSV")
            
            # Add credit_tips_numeric with None values
            df['credit_tips_numeric'] = None
            print("Added 'credit_tips_numeric' column with None values")
            print("Sample values:", df['credit_tips_numeric'].tolist())
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"Removed test file: {test_file}")

def main():
    """Run all tests."""
    print("=== Testing CSV Parsing and Column Handling ===")
    
    # Test with credit_tips column
    test_with_credit_tips()
    
    # Test without credit_tips column
    test_without_credit_tips()
    
    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    main()
