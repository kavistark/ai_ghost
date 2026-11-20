@echo off
title GHOST - AI Voice Assistant (Django)
echo ========================================================
echo         STARTING GHOST AI VOICE ASSISTANT
echo ========================================================
echo.
python manage.py makemigrations assistant
python manage.py migrate
echo.
echo Launching server at http://127.0.0.1:8000/
start http://127.0.0.1:8000/
python manage.py runserver 0.0.0.0:8000
pause

