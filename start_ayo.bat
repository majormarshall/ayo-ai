@echo off
title Ayo AI — Starting...
color 0A
chcp 65001 >NUL

echo.
echo  =============================================
echo    AYO AI -- Personal AI Operating System
echo    Built by Major Marshall
echo  =============================================
echo.

:: ── Check Ollama is running ─────────────────────────────────────────────────
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo [*] Starting Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >NUL
) else (
    echo [OK] Ollama is already running.
)

:: ── Check for AI model ───────────────────────────────────────────────────────
echo [*] Checking AI model...
ollama list 2>NUL | find "llama3.2" >NUL
if errorlevel 1 (
    echo.
    echo [!] AI model not found. Starting auto-downloader...
    echo     This runs in a separate window and auto-retries on network failure.
    start "Ayo Model Downloader" cmd /c pull_model.bat
    echo     Continuing to launch dashboard (model will load when ready)...
    echo.
)

:: ── Start Python backend in a separate window ───────────────────────────────
echo [*] Starting Ayo backend (Python)...
start "Ayo AI Backend" cmd /c "python main.py --no-enroll"

:: Wait for backend to come up (max 30s)
echo [*] Waiting for backend to start...
set /a tries=0
:wait_loop
    timeout /t 2 /nobreak >NUL
    curl -s http://localhost:5050/api/status >NUL 2>&1
    if not errorlevel 1 goto backend_ready
    set /a tries+=1
    if %tries% geq 15 (
        echo [!] Backend took too long — launching dashboard anyway.
        goto launch_dashboard
    )
    echo     Waiting... (%tries%/15)
    goto wait_loop

:backend_ready
echo [OK] Backend is ready!

:: ── Launch Electron dashboard ───────────────────────────────────────────────
:launch_dashboard
echo [*] Launching Ayo AI Dashboard...
echo.
npm start
