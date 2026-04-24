#!/usr/bin/env python3
"""
Texas OSOW Permit Parser with TxDMV Official Map Integration
Uses the QR code link to show the official route map
"""

import re
import json
from typing import List, Dict, Optional
import sys
import os

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF"""
    try:
        import pypdf
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def parse_permit_info(text: str) -> Dict:
    """Extract basic permit information"""
    info = {}
    
    permit_match = re.search(r'Permit Number:\s*(\d+)', text)
    if permit_match:
        info['permit_number'] = permit_match.group(1)
    
    origin_match = re.search(r'Origin:\s*([^\n]+?)(?:\s*Destination:|\s*Route Conditions:)', text, re.DOTALL)
    if origin_match:
        info['origin'] = origin_match.group(1).strip()
    
    dest_match = re.search(r'Destination:\s*([^\n]+?)(?:\s*Route Conditions:|\s*Amendments:)', text, re.DOTALL)
    if dest_match:
        info['destination'] = dest_match.group(1).strip()
    
    width_match = re.search(r"Max\.\s*Width:\s*([\d'\"]+)", text)
    height_match = re.search(r"Max\.\s*Height:\s*([\d'\"]+)", text)
    length_match = re.search(r"Max\.\s*Length:\s*([\d'\"]+)", text)
    
    if width_match:
        info['max_width'] = width_match.group(1)
    if height_match:
        info['max_height'] = height_match.group(1)
    if length_match:
        info['max_length'] = length_match.group(1)
    
    return info

def parse_route_table(text: str) -> List[Dict]:
    """Parse the route table from permit"""
    steps = []
    
    table_start = text.find('Miles') + text[text.find('Miles'):].find('Route')
    if table_start == -1:
        return steps
    
    table_end = text.find('Final Destination:', table_start)
    if table_end == -1:
        table_end = text.find('*Permit loads', table_start)
    
    table_section = text[table_start:table_end]
    lines = table_section.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Miles') or line.startswith('[Loaded Route'):
            continue
        
        match = re.match(r'^([\d<.]+)\s+([A-Z0-9]+[A-Za-z\s]*?)\s+(.*?)\s+([\d.]+)\s+\d{2}:\d{2}', line)
        
        if match:
            miles_str = match.group(1).replace('<', '').strip()
            try:
                miles = float(miles_str)
            except:
                miles = 0.1
            
            road = match.group(2).strip()
            direction = match.group(3).strip()
            cumulative = float(match.group(4))
            
            steps.append({
                'miles': miles,
                'road': road,
                'direction': direction,
                'cumulative': cumulative
            })
    
    return steps

def generate_txdmv_urls(permit_number: str) -> Dict[str, str]:
    """
    Generate URLs to official TxDMV permit page (from QR code)
    
    Pattern discovered:
    - Full permit: 260406820529 (12 digits: YYMMDD + 6-digit ID)
    - QR URL uses: PermitID=14820529 (8 digits: "14" prefix + last 6 digits)
    
    Example: 260406820529 → https://txpros.txdmv.gov/PermitDetails02.aspx?PermitID=14820529&QRUSER=1
    """
    # Extract last 6 digits and add "14" prefix
    if len(permit_number) >= 6:
        last_six = permit_number[-6:]
        permit_id = "14" + last_six
    else:
        # Unusual format - use as-is
        permit_id = permit_number
    
    base_url = "https://txpros.txdmv.gov/PermitDetails02.aspx"
    permit_url = f"{base_url}?PermitID={permit_id}&QRUSER=1"
    
    return {
        'txdmv_permit_url': permit_url,
        'txdmv_map_url': permit_url,  # Same URL - page has tabs for details/route/map
    }

def parse_permit(pdf_path: str) -> Dict:
    """Main parsing function"""
    print(f"📄 Reading permit: {pdf_path}")
    
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {"error": "Could not extract text from PDF"}
    
    print("✓ Text extracted")
    
    # Parse permit info
    permit_info = parse_permit_info(text)
    print(f"✓ Permit #{permit_info.get('permit_number', 'Unknown')}")
    print(f"  Origin: {permit_info.get('origin', 'Unknown')}")
    print(f"  Destination: {permit_info.get('destination', 'Unknown')}")
    
    # Parse route steps
    steps = parse_route_table(text)
    print(f"✓ Found {len(steps)} route steps")
    
    if steps:
        total_miles = steps[-1]['cumulative']
        print(f"  Total distance: {total_miles} miles")
    
    # Generate TxDMV URLs (from QR code)
    permit_number = permit_info.get('permit_number', '')
    txdmv_urls = generate_txdmv_urls(permit_number)
    
    print(f"✓ Generated official TxDMV map link")
    
    result = {
        'permit_info': permit_info,
        'steps': steps,
        'txdmv_permit_url': txdmv_urls['txdmv_permit_url'],
        'txdmv_map_url': txdmv_urls['txdmv_map_url'],
        # For backwards compatibility
        'google_maps_url': txdmv_urls['txdmv_map_url'],  
        'apple_maps_url': txdmv_urls['txdmv_map_url']
    }
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_permit_txdmv.py <permit.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = parse_permit(pdf_path)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("📍 OFFICIAL TxDMV LINKS (from QR code):")
    print("="*80)
    print(f"\n🗺️  Official Route Map:\n{result['txdmv_map_url']}\n")
    print(f"📄 Full Permit Details:\n{result['txdmv_permit_url']}\n")
    
    print("\n" + "="*80)
    print("🛣️  ROUTE STEPS:")
    print("="*80)
    for i, step in enumerate(result['steps'], 1):
        print(f"\n{i}. {step['road']}")
        print(f"   {step['direction']}")
        print(f"   {step['miles']} miles (total: {step['cumulative']} miles)")
    
    # Save to JSON
    output_file = os.path.basename(pdf_path).replace('.pdf', '_route.json')
    output_path = os.path.join('/home/claude', output_file)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Saved to: {output_path}")

if __name__ == "__main__":
    main()
