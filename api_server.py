#!/usr/bin/env python3
"""
Flask API for Texas OSOW Permit Parser
Handles PDF uploads and returns GPS-ready route data
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import tempfile
import sys

# Import our parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_permit import parse_permit

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Get port from environment variable (for deployment)
PORT = int(os.environ.get('PORT', 5000))

@app.route('/api/parse-permit', methods=['POST'])
def parse_permit_api():
    """
    API endpoint to parse uploaded permit PDF
    
    Returns:
        JSON with permit info, route steps, waypoints, and GPS URLs
    """
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Parse the permit
        result = parse_permit(temp_path)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        # Check for errors
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'Texas OSOW Permit Parser'})

@app.route('/')
def index():
    """Serve the main app"""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_path, 'permit_converter_app.html'), 'r') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({'error': 'Frontend not found'}), 404

if __name__ == '__main__':
    print("🚛 Texas OSOW Permit Parser API")
    print("================================")
    print(f"Starting server on http://0.0.0.0:{PORT}")
    print("\nEndpoints:")
    print("  GET  /              - Web interface")
    print("  POST /api/parse-permit - Upload permit PDF")
    print("  GET  /api/health    - Health check")
    print("\nReady to process permits! 🎯\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
