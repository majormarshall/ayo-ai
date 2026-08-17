@echo off
title Ayo AI — Model Downloader
color 0A

echo ============================================
echo   Ayo AI Model Downloader
echo   Auto-retries on network failure
echo ============================================
echo.

:retry
echo [%TIME%] Attempting to pull llama3.2:3b ...
ollama pull llama3.2:3b

if errorlevel 1 (
    echo.
    echo [!] Download failed or was interrupted.
    echo [*] Retrying in 10 seconds... (Ollama resumes from where it left off)
    echo.
    timeout /t 10 /nobreak >NUL
    goto retry
)

echo.
echo ============================================
echo   Model downloaded successfully!
echo   You can now run: npm start
echo ============================================
pause
