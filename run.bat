@echo off
rem Запуск приложения в Windows с кодировкой UTF-8.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
python main.py %*
if errorlevel 1 pause
endlocal
