#!/usr/bin/env python3
"""
Texas OSOW Permit Route Parser
Extracts route data from permit PDFs and generates GPS-ready waypoints
"""

import re
import json
from typing import List, Dict, Optional
import sys

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    try:
        import pypdf
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
            return text
    except ImportError:
        # Fallback: use pdftotext if available
        import subprocess
        result = subprocess.run(['pdftotext', pdf_path, '-'], 
                              capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def parse_permit_info(text: str) -> Dict:
    """Extract basic permit information"""
    info = {}
    
    # Extract permit number
    permit_match = re.search(r'Permit Number:\s*(\d+)', text)
    if permit_match:
        info['permit_number'] = permit_match.group(1)
    
    # Extract origin
    origin_match = re.search(r'Origin:\s*([^\n]+)', text)
    if origin_match:
        info['origin'] = origin_match.group(1).strip()
    
    # Extract destination
    dest_match = re.search(r'Destination:\s*([^\n]+?)(?:\s*Route Conditions:|\s*Amendments:)', text, re.DOTALL)
    if dest_match:
        info['destination'] = dest_match.group(1).strip()
    
    # Extract load dimensions
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
    """Parse the route table from permit text"""
    steps = []
    
    # Find the route table section (starts after "Origin:" line with miles/route/to)
    # and ends at "Final Destination:"
    
    # Look for the table header pattern
    table_start = text.find('Miles') + text[text.find('Miles'):].find('Route')
    if table_start == -1:
        return steps
    
    # Find where table ends
    table_end = text.find('Final Destination:', table_start)
    if table_end == -1:
        table_end = text.find('*Permit loads', table_start)
    
    table_section = text[table_start:table_end]
    
    # Split into lines and parse each route entry
    lines = table_section.split('\n')
    
    current_miles = None
    current_road = None
    current_direction = None
    current_cumulative = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Miles') or line.startswith('[Loaded Route'):
            continue
        
        # Try to parse route line - format: MILES ROAD DIRECTION DISTANCE TIME
        # Example: "3.70 SL8NFR w Bear right onto SH249EFR nw [TOMBALLEFR] 3.70 00:05"
        
        # Pattern: starts with number (miles)
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

def normalize_road_name(road: str) -> str:
    """Convert abbreviated road names to full names"""
    # Remove directional suffixes
    road = re.sub(r'\s+(nw|ne|sw|se|n|s|e|w)$', '', road, flags=re.IGNORECASE)
    
    # Convert abbreviations
    road = re.sub(r'^IH', 'I-', road)
    road = re.sub(r'^SH', 'TX-', road)
    road = re.sub(r'^US', 'US-', road)
    road = re.sub(r'^FM', 'FM ', road)
    road = re.sub(r'EFR$', ' Frontage Road', road)
    road = re.sub(r'NFR$', ' Frontage Road', road)
    
    return road.strip()

def extract_location_from_direction(direction: str, road: str) -> Optional[str]:
    """Try to extract a usable location from direction text"""
    # Look for city names
    cities = ['Houston', 'Beaumont', 'Angleton', 'Lake Jackson', 'Freeport', 
              'Tomball', 'Rosharon', 'Alvin', 'Pearland']
    
    for city in cities:
        if city.lower() in direction.lower():
            return f"{normalize_road_name(road)}, {city}, TX"
    
    # Look for highway intersections
    highway_match = re.search(r'(IH|SH|US|FM)[\s-]?(\d+)', direction)
    if highway_match:
        return f"{normalize_road_name(road)}, TX"
    
    return None

def generate_waypoints(permit_info: Dict, steps: List[Dict]) -> List[str]:
    """Generate GPS waypoints from route steps"""
    waypoints = []
    
    # Add origin
    origin = permit_info.get('origin', '')
    if origin:
        # Try to make it more specific
        if 'HOUSTON' in origin.upper():
            waypoints.append(origin.replace('in HOUSTON', ', Houston, TX'))
        elif 'LAKE JACKSON' in origin.upper():
            waypoints.append(origin.replace('in LAKE JACKSON', ', Lake Jackson, TX'))
        else:
            waypoints.append(origin + ', TX')
    
    # Add key waypoints from major highway changes
    major_highways = []
    last_major_road = None
    
    for step in steps:
        road = step['road']
        direction = step['direction']
        
        # Identify major highways (IH, US, major SH)
        if any(x in road.upper() for x in ['IH', 'US69', 'SH288', 'SH249', 'SH36']):
            if road != last_major_road:
                location = extract_location_from_direction(direction, road)
                if location:
                    waypoints.append(location)
                    major_highways.append(road)
                last_major_road = road
    
    # Add destination
    destination = permit_info.get('destination', '')
    if destination:
        if 'HOUSTON' in destination.upper():
            waypoints.append(destination.replace('in HOUSTON', ', Houston, TX'))
        elif 'LAKE JACKSON' in destination.upper():
            waypoints.append(destination.replace('in LAKE JACKSON', ', Lake Jackson, TX'))
        else:
            waypoints.append(destination + ', TX')
    
    return waypoints

def generate_google_maps_url(waypoints: List[str]) -> str:
    """Generate Google Maps URL with waypoints"""
    if len(waypoints) < 2:
        return ""
    
    from urllib.parse import quote
    
    origin = quote(waypoints[0])
    destination = quote(waypoints[-1])
    
    if len(waypoints) > 2:
        waypoint_str = '|'.join([quote(w) for w in waypoints[1:-1]])
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoint_str}&travelmode=driving"
    else:
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"
    
    return url

def generate_apple_maps_url(waypoints: List[str]) -> str:
    """Generate Apple Maps URL"""
    if len(waypoints) < 2:
        return ""
    
    from urllib.parse import quote
    origin = quote(waypoints[0])
    destination = quote(waypoints[-1])
    
    return f"http://maps.apple.com/?saddr={origin}&daddr={destination}"

def parse_permit(pdf_path: str) -> Dict:
    """Main function to parse permit and return structured data"""
    print(f"📄 Reading permit: {pdf_path}")
    
    # Extract text
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
    
    # Generate waypoints
    waypoints = generate_waypoints(permit_info, steps)
    print(f"✓ Generated {len(waypoints)} GPS waypoints")
    
    # Generate URLs
    google_url = generate_google_maps_url(waypoints)
    apple_url = generate_apple_maps_url(waypoints)
    
    result = {
        'permit_info': permit_info,
        'steps': steps,
        'waypoints': waypoints,
        'google_maps_url': google_url,
        'apple_maps_url': apple_url
    }
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_permit.py <permit.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = parse_permit(pdf_path)
    
    print("\n" + "="*80)
    print("📍 GPS LINKS:")
    print("="*80)
    print(f"\n🗺️  Google Maps:\n{result['google_maps_url']}\n")
    print(f"🍎 Apple Maps:\n{result['apple_maps_url']}\n")
    
    print("\n" + "="*80)
    print("🛣️  ROUTE STEPS:")
    print("="*80)
    for i, step in enumerate(result['steps'], 1):
        print(f"\n{i}. {step['road']}")
        print(f"   {step['direction']}")
        print(f"   {step['miles']} miles (total: {step['cumulative']} miles)")
    
    # Save to JSON
    import os
    filename = os.path.basename(pdf_path).replace('.pdf', '_route.json')
    output_file = os.path.join('/home/claude', filename)
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Saved route data to: {output_file}")

if __name__ == "__main__":
    main()
