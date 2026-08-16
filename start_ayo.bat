@echo off
title Ayo AI — Starting...
color 0A

echo.
echo  =============================================
echo    AYO AI — Personal AI Operating System
echo    Built by Major Marshall
echo  =============================================
echo.

:: Check if Ollama is running, start it if not
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo  [*] Starting Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >NUL
) else (
    echo  [OK] Ollama is already running.
)

:: Check for llama3.2 model
echo  [*] Checking AI model...
ollama list 2>NUL | find "llama3.2" >NUL
if errorlevel 1 (
    echo  [!] llama3.2 not found. Pulling now...
    echo      This may take several minutes on first run.
    ollama pull llama3.2:3b
)

echo.
echo  [*] Launching Ayo AI Dashboard...
echo.

:: Start Electron app
npm start

pause
