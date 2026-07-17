@echo off
REM DR Deficiency Management System - Web Server Startup Script
echo ================================================================================
echo DR Deficiency Management System - Starting Web Server
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo Checking dependencies...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Some dependencies may not have installed correctly
)

echo.
echo Starting Flask development server...
echo The application will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
