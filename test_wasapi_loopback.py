"""
Test WASAPI loopback - captures whatever Windows is playing (including Bluetooth!)
"""
import pyaudiowpatch as pyaudio
import numpy as np

print("="*60)
print("WASAPI Loopback Device Test")
print("="*60)
print("\nThis will find your default output device and capture from it.")
print("It should work with Bluetooth headsets!\n")

# Initialize PyAudio
p = pyaudio.PyAudio()

# Get default WASAPI loopback device
try:
    # Get default output device (what you're listening to)
    default_output = p.get_default_output_device_info()
    print(f"Default Output Device: {default_output['name']}")
    
    # Check if it has a loopback
    if default_output.get('isLoopbackDevice', False):
        print("✅ This device supports loopback!")
    else:
        print("⚠️  Checking for loopback variant...")
    
    # Get the loopback device for the default output
    wasapi_info = p.get_loopback_device_info_generator()
    loopback_device = None
    
    print("\nAvailable WASAPI Loopback Devices:")
    for idx, device in enumerate(wasapi_info):
        print(f"[{device['index']}] {device['name']}")
        if 'loopback' in device['name'].lower() or device.get('isLoopbackDevice'):
            loopback_device = device
            print(f"    ✅ This is a loopback device!")
    
    if loopback_device:
        print(f"\n{'='*60}")
        print(f"Found Loopback Device!")
        print(f"{'='*60}")
        print(f"Device: {loopback_device['name']}")
        print(f"Index: {loopback_device['index']}")
        print(f"Sample Rate: {int(loopback_device['defaultSampleRate'])} Hz")
        print(f"Channels: {loopback_device['maxInputChannels']}")
        
        # Test recording
        print(f"\n🎙️  Recording 5 seconds... PLAY SOME AUDIO NOW!")
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = loopback_device['maxInputChannels']
        RATE = int(loopback_device['defaultSampleRate'])
        RECORD_SECONDS = 5
        
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=loopback_device['index']
        )
        
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(np.frombuffer(data, dtype=np.int16))
        
        stream.stop_stream()
        stream.close()
        
        # Analyze audio levels
        audio_data = np.concatenate(frames)
        max_level = np.abs(audio_data).max()
        avg_level = np.abs(audio_data).mean()
        
        print(f"\n📊 Audio Levels:")
        print(f"   Max: {max_level}")
        print(f"   Avg: {avg_level}")
        
        if max_level > 100:
            print(f"\n✅ ✅ ✅ AUDIO DETECTED! WASAPI Loopback is working!")
            print(f"\nUse device index {loopback_device['index']} for live transcription!")
        else:
            print(f"\n❌ No audio detected. Make sure audio was playing.")
    else:
        print("\n❌ No loopback device found.")
        print("This shouldn't happen on Windows 10/11...")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    p.terminate()
