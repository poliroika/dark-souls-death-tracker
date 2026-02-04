@echo off
:: Запуск Dark Souls Death Tracker + DSDeaths

:: Проверяем права администратора (нужны для чтения памяти игры)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Запрашиваю права администратора...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs"
    exit /b
)

:: Переходим в папку скрипта
cd /d "%~dp0"

echo.
echo ========================================
echo   Dark Souls Death Counter
echo   Powered by DSDeaths
echo ========================================
echo.

:: Проверяем наличие DSDeaths.exe
if not exist "DSDeaths.exe" (
    echo [!] DSDeaths.exe не найден!
    echo.
    echo Скачайте его с:
    echo https://github.com/quidrex/DSDeaths/releases
    echo.
    echo и положите в эту папку: %cd%
    echo.
    pause
    exit /b
)

:: Запускаем DSDeaths СКРЫТО (без окна консоли)
echo [*] Запускаю DSDeaths.exe в фоне...
powershell -Command "Start-Process -FilePath '%cd%\DSDeaths.exe' -WindowStyle Hidden"

:: Даём время на запуск
timeout /t 2 /nobreak >nul

:: Запускаем Python оверлей
echo [*] Запускаю оверлей...
echo.
uv run python main.py

:: Когда оверлей закрыт - закрываем и DSDeaths
echo.
echo [*] Закрываю DSDeaths...
taskkill /f /im DSDeaths.exe >nul 2>&1

pause
