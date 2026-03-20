@echo off
title GitHub Player Installer
echo [*] Installing UI dependencies...

:: Перевірка чи є звичайний Python в системі для запуску самого Плеєра
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] System Python not found. Please install Python 3.10+ first.
    pause
    exit /b
)

:: Встановлення модулів для інтерфейсу
pip install customtkinter requests ping3

echo [+] Done! Starting GitHub Player...
python GitHubPlayer.py
pause
