@echo off
:: Запуск Dark Souls Death Tracker от администратора

:: Проверяем права администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запрашиваю права администратора...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Переходим в папку скрипта
cd /d "%~dp0"

:: Запускаем
echo ========================================
echo   Dark Souls Remastered Death Tracker
echo ========================================
echo.

uv run python main.py

pause
