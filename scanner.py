#!/usr/bin/env python3
import subprocess
import threading
import time
import os

# Global dictionary to store device info.
# Keys will be the (final) MAC addresses, values are dicts with first_seen, last_seen, rssi, and raw data.
ble_devices = {}

def verify_ubertooth():
    """Check if Ubertooth is available"""
    try:
        # Check device version
        result = subprocess.run(
            ["ubertooth-util", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"Ubertooth available: {result.stdout.strip()}")
            return True
        else:
            print(f"Ubertooth check failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error checking Ubertooth: {e}")
        return False

def scan_ble():
    """Run Ubertooth in follow mode and process output"""
    # Run Ubertooth in follow mode.
    # Adjust the command path if needed.
    cmd = ["ubertooth-btle", "-f"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print(f"Started Ubertooth scanner process with PID: {process.pid}")
    
    # Thread to log any stderr from Ubertooth.
    def log_errors():
        for err_line in process.stderr:
            print("STDERR:", err_line.strip())
    
    threading.Thread(target=log_errors, daemon=True).start()
    
    current_block = None  # Will hold info for the current block of output.
    for line in process.stdout:
        line = line.strip()
        print("DEBUG:", line)  # Debug print to view raw output.
        
        # Check for the start of a new block.
        if line.startswith("systime="):
            # If we already have a block in progress, flush it.
            if current_block is not None and "mac" in current_block and "rssi" in current_block:
                mac = current_block["mac"]
                timestamp = current_block.get("time", time.strftime("%Y-%m-%d %H:%M:%S"))
                rssi = current_block["rssi"]
                
                # Update our device dictionary.
                if mac not in ble_devices:
                    ble_devices[mac] = {
                        "mac": mac,
                        "first_seen": timestamp, 
                        "last_seen": timestamp, 
                        "rssi": rssi, 
                        "raw": current_block.get("raw", ""),
                        "count": 1
                    }
                    print(f"New device found: {mac} with RSSI: {rssi}")
                else:
                    ble_devices[mac]["last_seen"] = timestamp
                    ble_devices[mac]["rssi"] = rssi
                    ble_devices[mac]["raw"] = current_block.get("raw", "")
                    ble_devices[mac]["count"] = ble_devices[mac].get("count", 0) + 1
                    print(f"Updated device: {mac} with RSSI: {rssi}, count: {ble_devices[mac]['count']}")
            
            # Start a new block.
            current_block = {}
            current_block["raw"] = line
            current_block["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tokens = line.split()
            for token in tokens:
                if token.startswith("addr="):
                    current_block["mac"] = token.split("=", 1)[1]
                elif token.startswith("rssi="):
                    current_block["rssi"] = token.split("=", 1)[1]
        
        # If the line starts with "AdvA:" (advertiser address), update the MAC to use this address.
        elif line.startswith("AdvA:"):
            parts = line.split()
            if len(parts) >= 2:
                adv_mac = parts[1]
                current_block["mac"] = adv_mac
            current_block["raw"] += " | " + line
        
        # Look for device information
        elif "Company:" in line:
            company_parts = line.split("Company:", 1)
            if len(company_parts) > 1:
                company = company_parts[1].strip()
                if current_block is not None:
                    current_block["company"] = company
        
        else:
            # For any other line, append its content to the current block's raw data.
            if current_block is not None:
                current_block["raw"] += " | " + line
    
    # Flush the last block if present.
    if current_block is not None and "mac" in current_block and "rssi" in current_block:
        mac = current_block["mac"]
        timestamp = current_block.get("time", time.strftime("%Y-%m-%d %H:%M:%S"))
        rssi = current_block["rssi"]
        company = current_block.get("company", "Unknown")
        
        if mac not in ble_devices:
            ble_devices[mac] = {
                "mac": mac,
                "first_seen": timestamp, 
                "last_seen": timestamp, 
                "rssi": rssi, 
                "raw": current_block.get("raw", ""),
                "company": company,
                "count": 1
            }
        else:
            ble_devices[mac]["last_seen"] = timestamp
            ble_devices[mac]["rssi"] = rssi
            ble_devices[mac]["raw"] = current_block.get("raw", "")
            if "company" in current_block:
                ble_devices[mac]["company"] = company
            ble_devices[mac]["count"] = ble_devices[mac].get("count", 0) + 1

def cleanup_old_devices():
    """Remove devices not seen in the last 5 minutes"""
    now = time.time()
    old_macs = []
    
    # Find devices older than 5 minutes
    for mac, device in ble_devices.items():
        try:
            last_seen_time = time.mktime(time.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S"))
            if now - last_seen_time > 300:  # 5 minutes
                old_macs.append(mac)
        except:
            pass  # Skip if time parsing fails
    
    # Remove old devices
    for mac in old_macs:
        print(f"Removing old device: {mac}")
        del ble_devices[mac]

def scanner_thread():
    """Run scanner in a thread with automatic restart"""
    while True:
        try:
            scan_ble()
        except Exception as e:
            print(f"Scanner error: {e}")
        
        print("Scanner stopped, restarting in 3 seconds...")
        time.sleep(3)
        
        # Clean up old devices before restarting
        cleanup_old_devices()

def start():
    """Start the BLE scanner in a background thread"""
    if not verify_ubertooth():
        print("WARNING: Ubertooth may not be available")
        
    thread = threading.Thread(target=scanner_thread, daemon=True)
    thread.start()
    return thread

def get_devices():
    """Get devices sorted by signal strength"""
    # Clean old devices periodically
    cleanup_old_devices()
    
    # Convert to list and sort by RSSI (strongest first)
    devices_list = []
    for mac, device in ble_devices.items():
        # Copy device data and ensure all required fields
        device_copy = device.copy()
        device_copy["mac"] = mac
        device_copy["count"] = device.get("count", 1)
        device_copy["company"] = device.get("company", "Unknown")
        
        # Convert RSSI to integer for sorting
        try:
            device_copy["rssi"] = int(device_copy["rssi"])
        except:
            device_copy["rssi"] = -100  # Default for invalid RSSI
            
        devices_list.append(device_copy)
    
    # Sort by RSSI (strongest first)
    devices_list.sort(key=lambda x: x["rssi"], reverse=True)
    
    print(f"Returning {len(devices_list)} devices")
    return devices_list
