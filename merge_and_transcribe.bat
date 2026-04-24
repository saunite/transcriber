@echo off
REM Merge Mic + System Audio and Transcribe
REM Usage: merge_and_transcribe.bat <mic_file.wav> <sys_file.wav> [output_file] [format]
REM   format: txt (default), srt, or vtt

setlocal

REM Check required parameters
if "%~1"=="" (
    echo Error: Mic audio file not specified
    echo.
    echo Usage: merge_and_transcribe.bat ^<mic_file.wav^> ^<sys_file.wav^> [output_file] [format]
    echo.
    echo Examples:
    echo   merge_and_transcribe.bat mic.wav sys.wav transcript.txt
    echo   merge_and_transcribe.bat mic.wav sys.wav transcript.srt srt
    pause
    exit /b 1
)

if "%~2"=="" (
    echo Error: System audio file not specified
    echo.
    echo Usage: merge_and_transcribe.bat ^<mic_file.wav^> ^<sys_file.wav^> [output_file] [format]
    pause
    exit /b 1
)

REM Set up environment
set PATH=%PATH%;C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin
set PYTHONHTTPSVERIFY=0
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

REM Determine output file name
set OUTPUT_FILE=%~3
if "%OUTPUT_FILE%"=="" (
    set OUTPUT_FILE=%~n1_merged.txt
)

REM Set format (default to txt if not specified)
set FORMAT=txt
if not "%~4"=="" set FORMAT=%~4

REM Determine merged WAV path (placed alongside the mic file)
set MERGED_WAV=%~dp1%~n1_merged.wav

echo ============================================================
echo Merge and Transcribe
echo ============================================================
echo Mic file:    %~1
echo System file: %~2
echo Merged WAV:  %MERGED_WAV%
echo Output:      %OUTPUT_FILE%
echo Format:      %FORMAT%
echo Model:       large
echo ============================================================
echo.

REM Merge the two WAV files by mixing their audio streams
echo [1/2] Merging audio files with ffmpeg...
ffmpeg -y -i "%~1" -i "%~2" -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0" -ar 16000 -ac 1 "%MERGED_WAV%"

if errorlevel 1 (
    echo Error: ffmpeg failed to merge audio files.
    pause
    exit /b 1
)

echo.
echo [2/2] Transcribing merged audio with large model...
echo.

REM Transcribe using the large model for best accuracy
.venv\Scripts\python.exe transcriber.py --language en --model large --file "%MERGED_WAV%" --output "%OUTPUT_FILE%" --format %FORMAT%

if errorlevel 1 (
    echo Error: Transcription failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Done! Transcript saved to: %OUTPUT_FILE%
echo Merged WAV saved to:       %MERGED_WAV%
echo ============================================================
pause
