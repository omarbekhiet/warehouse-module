@echo off
title Warehouse Module - Server
color 0A

cd /d "%~dp0"

REM [1/5] التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM [2/5] البيئة الافتراضية
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create venv!
        pause
        exit /b 1
    )
)

REM [3/5] تفعيل البيئة
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate venv!
    pause
    exit /b 1
)

REM [4/5] التحقق من Flask
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    if exist "requirements.txt" (
        pip install -r requirements.txt
    ) else (
        pip install flask flask-cors flask-sqlalchemy flask-jwt-extended python-dotenv
    )
)

REM [5/5] تشغيل السيرفر
python run.py
pause