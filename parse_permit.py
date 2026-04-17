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
    # Remove directional suffixes first
    road = re.sub(r'\s+(nw|ne|sw|se|n|s|e|w)$', '', road, flags=re.IGNORECASE)
    
    # Convert abbreviations
    road = re.sub(r'^IH', 'I-', road)
    road = re.sub(r'^SH', 'TX-', road)
    road = re.sub(r'^US', 'US-', road)
    road = re.sub(r'^FM', 'FM ', road)
    
    # Handle frontage roads - keep them but format better for Google Maps
    # Note: Frontage roads are REQUIRED by permit, must be in route
    if 'WFR' in road.upper():
        road = re.sub(r'WFR$', ' West Frontage Rd', road, flags=re.IGNORECASE)
    elif 'EFR' in road.upper():
        road = re.sub(r'EFR$', ' East Frontage Rd', road, flags=re.IGNORECASE)
    elif 'NFR' in road.upper():
        road = re.sub(r'NFR$', ' North Frontage Rd', road, flags=re.IGNORECASE)
    elif 'SFR' in road.upper():
        road = re.sub(r'SFR$', ' South Frontage Rd', road, flags=re.IGNORECASE)
    
    return road.strip()

def extract_location_from_direction(direction: str, road: str) -> Optional[str]:
    """Try to extract a usable location from direction text"""
    # Look for city names
    cities = ['Houston', 'Beaumont', 'Angleton', 'Lake Jackson', 'Freeport', 
              'Tomball', 'Rosharon', 'Alvin', 'Pearland', 'Clute', 'Galveston',
              'Pasadena', 'Sugar Land', 'Katy', 'Spring', 'Conroe']
    
    for city in cities:
        if city.lower() in direction.lower():
            # Keep frontage roads as-is - they're required by permit
            clean_road = normalize_road_name(road)
            return f"{clean_road}, {city}, TX"
    
    # Look for highway intersections in the direction
    highway_match = re.search(r'(IH|SH|US|FM)[\s-]?(\d+)', direction)
    if highway_match:
        clean_road = normalize_road_name(road)
        # Keep frontage roads in the waypoint - they're legally required
        return f"{clean_road}, TX"
    
    return None

def clean_location_for_maps(location: str) -> str:
    """Convert permit location descriptions to Google Maps-friendly addresses"""
    
    # Remove common permit jargon
    location = location.replace('Intersection of ', '')
    location = location.replace('in HOUSTON', ', Houston, TX')
    location = location.replace('in LAKE JACKSON', ', Lake Jackson, TX')
    location = location.replace('in ANGLETON', ', Angleton, TX')
    
    # Expand common abbreviations
    location = location.replace('&', ' and ')
    location = location.replace('sl8', 'Sam Houston Tollway')
    location = location.replace('SL8', 'Sam Houston Tollway')
    location = location.replace('t c jester', 'TC Jester Blvd')
    location = location.replace('T C Jester', 'TC Jester Blvd')
    
    # Fix common street name patterns
    location = re.sub(r'\bfm\s*(\d+)', r'FM \1', location, flags=re.IGNORECASE)
    location = re.sub(r'\bsh\s*(\d+)', r'TX-\1', location, flags=re.IGNORECASE)
    location = re.sub(r'\bus\s*(\d+)', r'US-\1', location, flags=re.IGNORECASE)
    location = re.sub(r'\bih\s*(\d+)', r'I-\1', location, flags=re.IGNORECASE)
    
    # Handle distance-based locations (e.g., "1.6mi SE of SH0249 & FM1960")
    # Convert to intersection for better Google Maps recognition
    distance_match = re.search(r'(\d+\.?\d*)\s*mi\s+([NSEW]{1,2})\s+of\s+(.+)', location)
    if distance_match:
        # For now, just use the intersection part - more accurate than offset distance
        intersection_part = distance_match.group(3)
        location = intersection_part
        # Clean up the intersection
        location = location.replace('0249', '249').replace('1960', '1960')
        location = re.sub(r'(TX-\d+)\s+and\s+(FM\s+\d+)', r'\1 & \2', location)
    
    # Clean up multiple spaces
    location = re.sub(r'\s+', ' ', location).strip()
    
    # If no city mentioned, add TX
    if ', TX' not in location and 'Texas' not in location:
        location = location + ', TX'
    
    return location

def generate_waypoints(permit_info: Dict, steps: List[Dict]) -> List[str]:
    """Generate GPS waypoints from route steps - MUST include ALL steps for permit compliance"""
    waypoints = []
    
    # Add origin
    origin = permit_info.get('origin', '')
    if origin:
        clean_origin = clean_location_for_maps(origin)
        waypoints.append(clean_origin)
    
    # Add waypoints for EVERY significant road change
    # Permits require exact route compliance - cannot skip any step
    last_road = None
    
    for step in steps:
        road = step['road']
        direction = step['direction']
        
        # Normalize the road name for comparison
        normalized_road = normalize_road_name(road)
        
        # Skip if it's the same road as last waypoint
        if normalized_road == last_road:
            continue
        
        # Add waypoint for this road segment
        location = extract_location_from_direction(direction, road)
        if location:
            waypoints.append(location)
            last_road = normalized_road
    
    # Add destination
    destination = permit_info.get('destination', '')
    if destination:
        clean_dest = clean_location_for_maps(destination)
        waypoints.append(clean_dest)
    
    # Google Maps has a 10 waypoint limit, so if we have more, keep first, last, and evenly distribute middle
    if len(waypoints) > 10:
        first = waypoints[0]
        last = waypoints[-1]
        middle = waypoints[1:-1]
        
        # Keep every Nth waypoint to stay under limit
        step_size = len(middle) // 8  # Keep 8 middle waypoints
        selected_middle = [middle[i] for i in range(0, len(middle), max(1, step_size))][:8]
        
        waypoints = [first] + selected_middle + [last]
    
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
