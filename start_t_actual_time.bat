@echo off
REM Teams Meeting Transcription Launcher
REM This script sets up the environment and starts live transcription with dual-capture
REM (system audio + microphone) for complete Teams meeting coverage

echo ============================================================
echo Teams Meeting Transcriber
echo ============================================================
echo.
echo This will capture and transcribe:
echo   [SYS] - System audio (other participants)
echo   [MIC] - Your microphone (your voice)
echo.
echo Press Ctrl+C to stop transcription when meeting ends
echo ============================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set up environment variables
set PATH=%PATH%;C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin
set PYTHONHTTPSVERIFY=0

REM Generate timestamp for output filename
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,8%_%datetime:~8,6%
set output_file=meeting_%timestamp%.txt

echo Starting transcription...
echo Output will be saved to: %output_file%
echo Auto-stop after 10 minutes of silence (use --silence-timeout 0 to disable)
echo.

REM Start transcription with WASAPI loopback + microphone
REM Default silence timeout is 10 minutes (600 seconds)
REM To disable auto-stop, add: --silence-timeout 0
REM Microphone auto-detection enabled (use --mic-device N to specify manually)
python transcriber.py --actual-time --live --wasapi --include-mic --model base --output "%output_file%" --chunk-duration 10

echo.
echo ============================================================
echo Transcription saved to: %output_file%
echo ============================================================
pause
