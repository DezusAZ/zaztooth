#!/usr/bin/env python3
from flask import Flask, render_template, jsonify
import threading
import time
import scanner

app = Flask(__name__)

# Start the scanner
scanner_thread = None
last_cleanup = time.time()

def start_services():
    """Start all background services"""
    global scanner_thread
    scanner_thread = scanner.start()
    print("BLE scanner started")

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/data')
def get_data():
    """API endpoint for device data"""
    global last_cleanup
    
    # Periodically clean up old devices
    current_time = time.time()
    if current_time - last_cleanup > 60:  # Every minute
        scanner.cleanup_old_devices()
        last_cleanup = current_time
    
    # Get and return device data
    return jsonify(scanner.get_devices())

@app.route('/status')
def get_status():
    """API endpoint for scanner status"""
    return jsonify({
        "running": scanner_thread is not None and scanner_thread.is_alive(),
        "device_count": len(scanner.ble_devices),
        "timestamp": time.time()
    })

if __name__ == '__main__':
    try:
        # Start scanner
        start_services()
        
        # Run Flask app
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")
