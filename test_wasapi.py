"""
Test WASAPI loopback capture - bypasses Stereo Mix completely
"""
import sounddevice as sd
import numpy as np

print("Attempting to find loopback devices...")
print("\nSearching for devices with 'loopback' in the name:\n")

devices = sd.query_devices()
for idx, device in enumerate(devices):
    # Check if it's a potential loopback device
    if ('loopback' in device['name'].lower() or 
        'stereo mix' in device['name'].lower() or
        'wave out' in device['name'].lower() or
        device['name'].startswith('CABLE')):
        
        print(f"[{idx}] {device['name']}")
        print(f"    Input Channels: {device['max_input_channels']}")
        print(f"    Sample Rate: {device['default_samplerate']}")
        print()

print("\nTrying to query default devices...")
try:
    default_input = sd.query_devices(kind='input')
    default_output = sd.query_devices(kind='output')
    
    print(f"Default Input: {default_input['name']}")
    print(f"Default Output: {default_output['name']}")
except Exception as e:
    print(f"Error: {e}")
