@echo off
setlocal
cd /d "%~dp0"

set "REVIEW_WORKSPACE=%~1"
if not defined REVIEW_WORKSPACE set "REVIEW_WORKSPACE=%~dp0"

if not exist "%REVIEW_WORKSPACE%\." (
    echo [ERROR] Workspace folder not found:
    echo %REVIEW_WORKSPACE%
    echo.
    pause
    exit /b 1
)

py -3 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 was not found. Install Python 3.10 or newer first.
    echo.
    pause
    exit /b 1
)

echo Starting Code Review Agent...
echo Workspace: %REVIEW_WORKSPACE%
echo The browser will open automatically. Close this window to stop the server.
echo.

py -3 -m code_review_agent --web --open-browser --workspace "%REVIEW_WORKSPACE%\."
set "RUN_EXIT_CODE=%ERRORLEVEL%"

if not "%RUN_EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Startup failed. Check Python, .env, and whether port 8000 is free.
    pause
)

endlocal & exit /b %RUN_EXIT_CODE%
