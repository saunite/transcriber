@echo off
REM Teams Meeting Transcription Launcher
REM This script sets up the environment and starts live transcription with dual-capture
REM (system audio + microphone) for complete Teams meeting coverage
REM
REM Usage: win-start-transcription.bat [name-prefix] [transcriber flags...]
REM   name-prefix:  prefix for the output filename (default: meeting)
REM   Timestamps default to wall-clock time (--actual-time is always passed).
REM   flags:        passed through to transcriber.py, e.g.
REM                   --silence-timeout 0      never auto-stop on silence
REM                   --language en            force a language
REM   Example: win-start-transcription.bat sprint-review --silence-timeout 0
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

REM Prefer the standalone CLI next to this script (a release's CLI archive, no
REM Python needed); otherwise fall back to the project venv
REM (openspec/changes/02-add-release-pipeline-windows).
if exist "%~dp0transcriber.exe" (
    set "RUN="%~dp0transcriber.exe""
) else (
    if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
    set "RUN=python transcriber.py"
)

REM Set up environment variables
set PYTHONHTTPSVERIFY=0
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONIOENCODING=utf-8
chcp 65001 >nul

REM Generate timestamp for output filename. PowerShell, not wmic: WMIC is
REM disabled or removed on current Windows 11, and its empty output once named
REM the file TEST_~0,8datetime:~8,6.txt -- the ":" hid the transcript in an
REM NTFS alternate data stream (openspec/changes/02-add-release-pipeline-windows).
set timestamp=
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set timestamp=%%I
if not defined timestamp (
    echo Could not read the current time from PowerShell, so no output filename can be built.
    exit /b 1
)
set output_file=%NAME_PREFIX%_%timestamp%.txt

REM Start transcription with WASAPI loopback + microphone. Built into one
REM variable and both echoed and run from it, so the printed line can never
REM drift from what's actually executed (openspec/changes/compact-live-cli-output).
set "CMD=%RUN% --live --wasapi --include-mic --model base --output "%output_file%" --chunk-duration 10 --actual-time %REST%"
echo %CMD%
%CMD%

echo.
echo ============================================================
echo Transcription saved to: %output_file%
echo ============================================================
pause
