@echo off
REM Teams Meeting Transcription Launcher
REM This script sets up the environment and starts live transcription with dual-capture
REM (system audio + microphone) for complete Teams meeting coverage
REM
REM Usage: start_teams_transcription.bat [name-prefix] [transcriber flags...]
REM   name-prefix:  prefix for the output filename (default: meeting)
REM   Timestamps default to wall-clock time (--actual-time is always passed).
REM   flags:        passed through to transcriber.py, e.g.
REM                   --silence-timeout 0      never auto-stop on silence
REM                   --save-audio             also save sys/mic WAV files
REM                   --language en            force a language
REM   Example: start_teams_transcription.bat sprint-review --silence-timeout 0
setlocal

set NAME_PREFIX=meeting
set REST=
if not "%~1"=="" if not "%~1:~0,1%"=="-" (
    set NAME_PREFIX=%~1
    shift
)
:args_loop
if "%~1"=="" goto args_done
set REST=%REST% %1
shift
goto args_loop
:args_done

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set up environment variables
set PATH=%PATH%;C:\Users\e-AndreSaunite\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin
set PYTHONHTTPSVERIFY=0
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONIOENCODING=utf-8
chcp 65001 >nul

REM Generate timestamp for output filename
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,8%_%datetime:~8,6%
set output_file=%NAME_PREFIX%_%timestamp%.txt

REM Start transcription with WASAPI loopback + microphone. Built into one
REM variable and both echoed and run from it, so the printed line can never
REM drift from what's actually executed (openspec/changes/compact-live-cli-output).
set "CMD=python transcriber.py --live --wasapi --include-mic --model base --output "%output_file%" --chunk-duration 10 --actual-time %REST%"
echo %CMD%
%CMD%

echo.
echo ============================================================
echo Transcription saved to: %output_file%
echo ============================================================
pause
