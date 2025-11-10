# Live Teams Meeting Transcription Setup

Since you're using a Bluetooth headset and can't download Teams recordings, here are your options for live capture:

## Option 1: VB-Cable Virtual Audio Device (Recommended)

### Installation:
1. Download VB-Cable from: https://vb-audio.com/Cable/
2. Extract the ZIP file
3. Right-click `VBCABLE_Setup_x64.exe` → "Run as Administrator"
4. Click "Install Driver"
5. Restart your computer

### Configuration:
1. **In Windows Sound Settings:**
   - Right-click speaker icon → Sound Settings
   - Output device: Select "CABLE Input (VB-Audio Virtual Cable)"
   
2. **In Teams:**
   - Settings → Devices
   - Speaker: "CABLE Input (VB-Audio Virtual Cable)"
   - Microphone: Your Bluetooth headset microphone
   
3. **In Windows (to hear audio yourself):**
   - Open Sound Control Panel (mmsys.cpl)
   - Recording tab → Right-click "CABLE Output" → Properties
   - Listen tab → Check "Listen to this device"
   - Playback through: Your Bluetooth Headphones

4. **Find the VB-Cable device number:**
   ```powershell
   python transcriber.py --list-devices
   ```
   Look for "CABLE Output" - note its number (e.g., device 5)

5. **Start transcription:**
   ```powershell
   python transcriber.py --live --audio-device <NUMBER> --model base --output "teams_meeting.txt" --chunk-duration 10
   ```

## Option 2: OBS Studio (Free Screen Recorder)

### Setup:
1. Install OBS Studio: `winget install OBSProject.OBSStudio`
2. Set it to record Teams meetings
3. After meeting, transcribe the recording file:
   ```powershell
   python transcriber.py --file "recording.mp4" --model base
   ```

## Option 3: Windows Game Bar

1. During Teams meeting, press `Win + G`
2. Click "Capture" → "Start Recording" (or `Win + Alt + R`)
3. Recording saves to `C:\Users\YourName\Videos\Captures\`
4. After meeting ends, transcribe:
   ```powershell
   python transcriber.py --file "C:\Users\e-AndreSaunite\Videos\Captures\meeting.mp4" --model base
   ```

**Game Bar is the easiest** - no installation needed, but recordings happen after the fact (not live transcription).

---

## Current Working Commands:

### File Transcription (Already Working):
```powershell
$env:PATH += ";C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin"
$env:PYTHONHTTPSVERIFY = "0"
python transcriber.py --file "path\to\video.mp4" --model base --output "transcript.txt"
```

### Live Microphone (Already Working):
```powershell
$env:PATH += ";C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin"
$env:PYTHONHTTPSVERIFY = "0"
python transcriber.py --live --audio-device 3 --model base --output "live.txt" --chunk-duration 10
```
