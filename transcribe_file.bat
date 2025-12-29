@echo off
REM File Transcription Script
REM Usage: transcribe_file.bat <input_file> <output_file> [format]
REM   format: txt (default), srt, or vtt

setlocal

REM Check if input file parameter is provided
if "%~1"=="" (
    echo Error: Input file not specified
    echo.
    echo Usage: transcribe_file.bat ^<input_file^> ^<output_file^> [format]
    echo.
    echo Examples:
    echo   transcribe_file.bat "meeting.mp4" "transcript.txt"
    echo   transcribe_file.bat "meeting.mp4" "transcript.srt" srt
    echo   transcribe_file.bat "meeting.mp4" "transcript.vtt" vtt
    pause
    exit /b 1
)

REM Check if output file parameter is provided
if "%~2"=="" (
    echo Error: Output file not specified
    echo.
    echo Usage: transcribe_file.bat ^<input_file^> ^<output_file^> [format]
    pause
    exit /b 1
)

REM Set format (default to txt if not specified)
set FORMAT=txt
if not "%~3"=="" set FORMAT=%~3

REM Set up environment variables
set PATH=%PATH%;C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin
set PYTHONHTTPSVERIFY=0

echo ============================================================
echo Audio/Video Transcription
echo ============================================================
echo Input:  %~1
echo Output: %~2
echo Format: %FORMAT%
echo ============================================================
echo.

REM Run transcription
.venv\Scripts\python.exe transcriber.py --file "%~1" --output "%~2" --format %FORMAT%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Transcription completed successfully!
    echo Output saved to: %~2
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo Transcription failed with error code: %ERRORLEVEL%
    echo ============================================================
)

endlocal
pause
