@echo off
cd /d "%~dp0"

:: If Python or dependencies are missing, run the automated setup
where python >nul 2>&1
if errorlevel 1 goto run_installer

python -c "import pandas, openpyxl, playwright" >nul 2>&1
if errorlevel 1 goto run_installer

:: Environment ready: launch GUI immediately and exit
start "" pythonw main.py
exit

:run_installer
call INSTALADOR_AUTOMATICO.bat
exit
