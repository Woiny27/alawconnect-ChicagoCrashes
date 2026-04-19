#!/usr/bin/env python3
"""
Extract and transform Socrata API schema definitions into usable formats.
"""
import json
import csv
from pathlib import Path

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def extract_crashes_schema():
    """Extract crashes schema from Socrata API."""
    api_file = Path('schema/socrata_columns_api.json')
    if not api_file.exists():
        print(f"⚠️  {api_file} not found")
        return
    
    columns = load_json(api_file)
    
    # Create CSV
    csv_file = Path('schema/crashes_columns.csv')
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'fieldName', 'dataTypeName', 'description'])
        writer.writeheader()
        for col in columns:
            writer.writerow({
                'name': col.get('name', ''),
                'fieldName': col.get('fieldName', ''),
                'dataTypeName': col.get('dataTypeName', ''),
                'description': col.get('description', '')
            })
    print(f"✓ Created {csv_file} ({len(columns)} columns)")

def extract_vehicles_schema():
    """Extract vehicles schema from Socrata API."""
    api_file = Path('schema/socrata_vehicles_api.json')
    if not api_file.exists():
        print(f"⚠️  {api_file} not found")
        return
    
    columns = load_json(api_file)
    
    # Create CSV
    csv_file = Path('schema/vehicles_columns.csv')
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'fieldName', 'dataTypeName', 'description'])
        writer.writeheader()
        for col in columns:
            writer.writerow({
                'name': col.get('name', ''),
                'fieldName': col.get('fieldName', ''),
                'dataTypeName': col.get('dataTypeName', ''),
                'description': col.get('description', '')
            })
    print(f"✓ Created {csv_file} ({len(columns)} columns)")

def create_combined_reference():
    """Create a combined reference document."""
    crashes_file = Path('schema/socrata_columns_api.json')
    vehicles_file = Path('schema/socrata_vehicles_api.json')
    
    if not crashes_file.exists() or not vehicles_file.exists():
        print("⚠️  Schema files not found")
        return
    
    crashes = load_json(crashes_file)
    vehicles = load_json(vehicles_file)
    
    ref_file = Path('schema/SCHEMA_REFERENCE.txt')
    with open(ref_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("CHICAGO CRASHES DATASET SCHEMA REFERENCE\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("CRASHES DATASET\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Columns: {len(crashes)}\n\n")
        for col in crashes:
            f.write(f"Field: {col.get('fieldName')}\n")
            f.write(f"  Name: {col.get('name')}\n")
            f.write(f"  Type: {col.get('dataTypeName')}\n")
            f.write(f"  Description: {col.get('description', 'N/A')}\n\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("VEHICLES DATASET\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Columns: {len(vehicles)}\n\n")
        for col in vehicles:
            f.write(f"Field: {col.get('fieldName')}\n")
            f.write(f"  Name: {col.get('name')}\n")
            f.write(f"  Type: {col.get('dataTypeName')}\n")
            f.write(f"  Description: {col.get('description', 'N/A')}\n\n")
    
    print(f"✓ Created {ref_file}")

if __name__ == '__main__':
    print("🔄 Extracting schema definitions from Socrata API...\n")
    extract_crashes_schema()
    extract_vehicles_schema()
    create_combined_reference()
    print("\n✅ Schema extraction complete!")
