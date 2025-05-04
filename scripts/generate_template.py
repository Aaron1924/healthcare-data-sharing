#!/usr/bin/env python3
"""
Generate a template for purchasing medical records.

This script creates a template that can be used to request medical records
matching specific criteria.
"""

import os
import json
import argparse
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_template(category=None, diagnosis=None, age_range=None, gender=None, location=None):
    """Generate a template for purchasing medical records."""
    template = {
        "category": category if category else "General",
        "time_period": "1 year",
        "min_records": 5,
        "demographics": {
            "age": True,
            "gender": True,
            "location": True,
            "ethnicity": True
        },
        "medical_data": {
            "diagnosis": True,
            "treatment": True,
            "medications": True,
            "lab_results": True
        },
        "filters": {}
    }
    
    # Add filters based on parameters
    if category:
        template["filters"]["category"] = category
    
    if diagnosis:
        template["filters"]["diagnosis"] = diagnosis
    
    if age_range:
        min_age, max_age = map(int, age_range.split('-'))
        template["filters"]["age"] = {"min": min_age, "max": max_age}
    
    if gender:
        template["filters"]["gender"] = gender
    
    if location:
        template["filters"]["location"] = location
    
    return template

def calculate_template_hash(template):
    """Calculate a hash of the template for use in purchase requests."""
    template_str = json.dumps(template, sort_keys=True)
    return "0x" + hashlib.sha256(template_str.encode()).hexdigest()

def main():
    """Main function to generate a template."""
    parser = argparse.ArgumentParser(description="Generate a template for purchasing medical records")
    parser.add_argument("--category", type=str, help="Medical category (e.g., Cardiology, Oncology)")
    parser.add_argument("--diagnosis", type=str, help="Specific diagnosis to filter for")
    parser.add_argument("--age", type=str, help="Age range (e.g., 18-65)")
    parser.add_argument("--gender", type=str, help="Gender filter (Male, Female, Other)")
    parser.add_argument("--location", type=str, help="Location filter (e.g., 'New York, USA')")
    parser.add_argument("--output", type=str, help="Output file for template (optional)")
    
    args = parser.parse_args()
    
    # Generate the template
    template = generate_template(
        category=args.category,
        diagnosis=args.diagnosis,
        age_range=args.age,
        gender=args.gender,
        location=args.location
    )
    
    # Calculate template hash
    template_hash = calculate_template_hash(template)
    
    # Print the template and hash
    print("\nGenerated Template:")
    print(json.dumps(template, indent=2))
    print(f"\nTemplate Hash: {template_hash}")
    print("\nUse this hash when creating a purchase request.")
    
    # Save template to file if requested
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"\nSaved template to {args.output}")

if __name__ == "__main__":
    main()
