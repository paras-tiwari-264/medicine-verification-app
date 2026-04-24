@echo off
title Medicine Verification API

:: Always run from the directory where this bat file lives
cd /d "%~dp0"

echo.
echo  ================================
echo   Medicine Verification API
echo  ================================
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Is Python installed?
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: Activate virtual environment
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.

:: Install dependencies if needed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

:: Check .env exists
if not exist ".env" (
    echo [WARN] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo [WARN] Please edit .env with your Firebase credentials before continuing.
    pause
)

:: Check firebase credentials
if not exist "firebase-credentials.json" (
    echo [ERROR] firebase-credentials.json not found.
    echo Download it from Firebase Console ^> Project Settings ^> Service Accounts.
    pause
    exit /b 1
)

echo [OK] Starting server...
echo [OK] API docs: http://localhost:8000/docs
echo.

echo [Ok] Live on: http://localhost:8000/ui

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
