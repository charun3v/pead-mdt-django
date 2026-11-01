@echo off
title Paediatric MDT Server - http://127.0.0.1:8000/
cd /d "%~dp0"
echo ===================================================
echo   Starting Paediatric MDT Django Web Application
echo ===================================================
echo.
echo Activating virtual environment...
call ".\venv\Scripts\activate.bat"

echo Starting server on http://127.0.0.1:8000/ ...
echo (Press Ctrl+C in this window at any time to stop the server)
echo.

start "" "http://127.0.0.1:8000/"
python manage.py runserver 127.0.0.1:8000 --noreload

pause
