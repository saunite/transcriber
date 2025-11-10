@echo off
REM Live Transcription Starter for Teams Meetings
REM This script sets up the environment and starts live transcription

echo ============================================================
echo Live Teams Meeting Transcriber
echo ============================================================
echo.
echo BEFORE YOU START:
echo 1. Join your Teams meeting first
echo 2. Make sure Stereo Mix is enabled (should be device 16)
echo 3. Press Ctrl+C to stop transcription
echo.
pause

REM Add ffmpeg to PATH
set PATH=%PATH%;C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin

REM Disable SSL verification for model downloads
set PYTHONHTTPSVERIFY=0

REM Get timestamp for output filename
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set filename=teams_transcript_%mydate%_%mytime%.txt

echo.
echo Saving transcript to: %filename%
echo.

REM Start live transcription using Stereo Mix (device 16)
python transcriber.py --live --audio-device 16 --model base --output "%filename%"

pause
