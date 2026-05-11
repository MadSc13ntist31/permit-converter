#!/usr/bin/env python3
"""
Texas OSOW Permit Parser with Geocoding
Converts permit roads to actual GPS coordinates
"""

import re
import json
from typing import List, Dict, Optional, Tuple
import sys
import os
import time
import urllib.request
import urllib.parse

def geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Geocode a location to lat/long using Nominatim (free OpenStreetMap)
    Returns (latitude, longitude) or None
    """
    try:
        # Clean up the location string
        location = location.strip()
        
        # Nominatim API (free, no API key needed)
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us'
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'TexasOSOWPermitParser/1.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                print(f"  ✓ Geocoded: {location[:50]} → {lat:.4f}, {lon:.4f}")
                return (lat, lon)
            else:
                print(f"  ✗ Could not geocode: {location[:50]}")
                return None
                
    except Exception as e:
        print(f"  ✗ Geocoding error for {location[:30]}: {str(e)}")
        return None

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

def clean_location_for_geocoding(location: str) -> str:
    """Clean up location text for better geocoding"""
    # Remove "Intersection of"
    location = location.replace('Intersection of ', '')
    location = location.replace('in HOUSTON', ', Houston')
    location = location.replace('in LAKE JACKSON', ', Lake Jackson')
    location = location.replace('in ANGLETON', ', Angleton')
    
    # Fix common abbreviations
    location = location.replace('&', ' and ')
    location = location.replace('sl8', 'Sam Houston Tollway')
    location = location.replace('SL8', 'Sam Houston Tollway')
    location = location.replace('t c jester', 'TC Jester Boulevard')
    
    # Fix highway names
    location = re.sub(r'\bSH\s*(\d+)', r'TX-\1', location)
    location = re.sub(r'\bFM\s*(\d+)', r'FM \1', location)
    location = re.sub(r'\bIH\s*(\d+)', r'I-\1', location)
    location = re.sub(r'\bUS\s*(\d+)', r'US-\1', location)
    
    # Always add Texas
    if ', TX' not in location and 'Texas' not in location:
        location = location + ', Texas'
    
    return location.strip()

def generate_geocoded_waypoints(permit_info: Dict, steps: List[Dict]) -> List[Dict]:
    """
    Generate waypoints with geocoded coordinates
    Returns list of dicts with 'location', 'lat', 'lon'
    """
    waypoints = []
    
    print("\n🌍 Geocoding waypoints...")
    
    # Geocode origin
    origin = permit_info.get('origin', '')
    if origin:
        clean_origin = clean_location_for_geocoding(origin)
        coords = geocode_location(clean_origin)
        if coords:
            waypoints.append({
                'location': origin,
                'lat': coords[0],
                'lon': coords[1]
            })
        time.sleep(1)  # Rate limiting - be nice to free API
    
    # Geocode key turns (not every single step - too many)
    # Focus on major highway changes
    last_road_type = None
    
    for i, step in enumerate(steps):
        # Skip last step (arrival)
        if 'arrive' in step['direction'].lower():
            continue
        
        road = step['road']
        direction = step['direction']
        
        # Identify road type (highway, frontage, etc)
        road_type = None
        if any(x in road.upper() for x in ['IH', 'US', 'SH']):
            road_type = 'highway'
        elif 'FM' in road.upper():
            road_type = 'fm'
        
        # Only geocode when changing road types or major turns
        if road_type != last_road_type or i % 3 == 0:  # Every 3rd step or road type change
            # Extract target location from direction
            target = None
            
            # Look for "onto X"
            onto_match = re.search(r'onto\s+([A-Z][A-Za-z0-9\s]+?)(?:\s+[nsew]{1,2}|\s*\[|$)', direction, re.IGNORECASE)
            if onto_match:
                target = onto_match.group(1).strip()
                # If there's a location in brackets, use it
                loc_match = re.search(r'\[([A-Z]+)\]', direction)
                if loc_match:
                    place = loc_match.group(1)
                    # Clean up place name
                    place = re.sub(r'(EFR|WFR|NFR|SFR)$', '', place, flags=re.IGNORECASE)
                    target = f"{target}, {place}, Texas"
                else:
                    target = f"{target}, Texas"
            
            # Look for "toward X"
            if not target:
                toward_match = re.search(r'toward\s+([A-Za-z][A-Za-z0-9\s/\-]+)', direction, re.IGNORECASE)
                if toward_match:
                    target = toward_match.group(1).strip()
                    if '/' in target:
                        target = target.split('/')[0].strip()
                    target = f"{target}, Texas"
            
            if target:
                target_clean = clean_location_for_geocoding(target)
                coords = geocode_location(target_clean)
                if coords:
                    waypoints.append({
                        'location': target,
                        'lat': coords[0],
                        'lon': coords[1]
                    })
                time.sleep(1)  # Rate limiting
        
        last_road_type = road_type
    
    # Geocode destination
    destination = permit_info.get('destination', '')
    if destination:
        clean_dest = clean_location_for_geocoding(destination)
        coords = geocode_location(clean_dest)
        if coords:
            waypoints.append({
                'location': destination,
                'lat': coords[0],
                'lon': coords[1]
            })
    
    # Limit to 10 waypoints for Google Maps
    if len(waypoints) > 10:
        # Keep first, last, and evenly distribute middle
        first = waypoints[0]
        last = waypoints[-1]
        middle = waypoints[1:-1]
        step_size = max(1, len(middle) // 8)
        selected_middle = [middle[i] for i in range(0, len(middle), step_size)][:8]
        waypoints = [first] + selected_middle + [last]
    
    return waypoints

def generate_google_maps_url_with_coords(waypoints: List[Dict]) -> str:
    """Generate Google Maps URL using lat/long coordinates"""
    if len(waypoints) < 2:
        return ""
    
    # Google Maps URL with coordinates: lat,lon
    origin = f"{waypoints[0]['lat']},{waypoints[0]['lon']}"
    destination = f"{waypoints[-1]['lat']},{waypoints[-1]['lon']}"
    
    if len(waypoints) > 2:
        # Waypoints as lat,lon pairs
        waypoint_coords = [f"{wp['lat']},{wp['lon']}" for wp in waypoints[1:-1]]
        waypoint_str = '|'.join(waypoint_coords)
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoint_str}&travelmode=driving"
    else:
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"
    
    return url

def parse_permit(pdf_path: str) -> Dict:
    """Main parsing function with geocoding"""
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
    
    # Generate geocoded waypoints
    waypoints = generate_geocoded_waypoints(permit_info, steps)
    print(f"\n✓ Geocoded {len(waypoints)} waypoints successfully")
    
    # Generate Google Maps URL
    google_url = generate_google_maps_url_with_coords(waypoints)
    
    result = {
        'permit_info': permit_info,
        'steps': steps,
        'waypoints': waypoints,
        'google_maps_url': google_url
    }
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_permit_geocoded.py <permit.pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = parse_permit(pdf_path)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("📍 GPS LINK (with coordinates):")
    print("="*80)
    print(f"\n🗺️  Google Maps:\n{result['google_maps_url']}\n")
    
    print("\n" + "="*80)
    print("🗺️  GEOCODED WAYPOINTS:")
    print("="*80)
    for i, wp in enumerate(result['waypoints'], 1):
        print(f"{i}. {wp['location'][:60]}")
        print(f"   → {wp['lat']:.6f}, {wp['lon']:.6f}")
    
    # Save to JSON
    output_file = os.path.basename(pdf_path).replace('.pdf', '_geocoded.json')
    output_path = os.path.join('/home/claude', output_file)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Saved to: {output_path}")

if __name__ == "__main__":
    main()
