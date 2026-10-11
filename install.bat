@echo off
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest
echo.
echo Install done. Ab check.bat chalao.
pause
