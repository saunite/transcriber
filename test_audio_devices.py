"""
Quick audio device test - checks if devices are actually receiving audio
"""
import sounddevice as sd
import numpy as np
import time

def test_device(device_id, duration=3):
    """Test if a device is receiving audio."""
    print(f"\n{'='*60}")
    print(f"Testing Device {device_id}")
    device_info = sd.query_devices(device_id)
    print(f"Name: {device_info['name']}")
    print(f"Sample Rate: {device_info['default_samplerate']} Hz")
    print(f"{'='*60}")
    
    if device_info['max_input_channels'] == 0:
        print("❌ This is not an input device (can't record)")
        return False
    
    try:
        sample_rate = int(device_info['default_samplerate'])
        
        print(f"Recording {duration} seconds... PLAY SOME AUDIO NOW!")
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_id,
            dtype=np.float32
        )
        sd.wait()
        
        # Check audio levels
        max_level = np.abs(recording).max()
        avg_level = np.abs(recording).mean()
        
        print(f"\n📊 Audio Levels:")
        print(f"   Max: {max_level:.6f}")
        print(f"   Avg: {avg_level:.6f}")
        
        if max_level > 0.001:
            print(f"✅ AUDIO DETECTED! This device is working!")
            return True
        else:
            print(f"❌ No audio detected (silence)")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("AUDIO DEVICE TEST")
    print("="*60)
    print("\nThis will test Stereo Mix devices to see which one works.")
    print("IMPORTANT: PLAY SOME AUDIO (YouTube, music, etc.) during the test!\n")
    
    # Test the Stereo Mix devices we found
    stereo_mix_devices = [1, 8, 18, 19]  # From --list-devices output
    
    working_devices = []
    
    for device_id in stereo_mix_devices:
        try:
            if test_device(device_id, duration=3):
                working_devices.append(device_id)
        except Exception as e:
            print(f"Skipping device {device_id}: {e}")
        
        time.sleep(0.5)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if working_devices:
        print(f"\n✅ Working devices found: {working_devices}")
        print(f"\nUse this command for live transcription:")
        print(f"python transcriber.py --live --audio-device {working_devices[0]} --model base --output live.txt")
    else:
        print("\n❌ No working Stereo Mix devices found.")
        print("\nPossible issues:")
        print("1. Stereo Mix is not enabled in Windows Sound settings")
        print("2. Stereo Mix is enabled but not set as default recording device")
        print("3. Your Bluetooth headset audio doesn't go through Stereo Mix")
        print("\nTo enable Stereo Mix:")
        print("1. Right-click speaker icon → Sounds")
        print("2. Recording tab → Right-click → Show Disabled Devices")
        print("3. Right-click 'Stereo Mix' → Enable")
        print("4. Right-click 'Stereo Mix' → Set as Default Device")
