@echo off
title Warehouse Module - Server
color 0A
cd /d "%~dp0"

echo ============================================
echo     WAREHOUSE MODULE
echo ============================================
echo.

call venv\Scripts\activate.bat

echo Server starting...
echo.
echo Dashboard: http://localhost:5000/index.html
echo.
echo Press Ctrl+C to stop.
echo.

python run.py
pause
