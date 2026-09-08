@echo off
cd /d "%~dp0"
title Shopee Agency Pro - Painel Web Local

:: Check if python is available
where python >nul 2>&1
if errorlevel 1 (
    echo [X] Python nao foi detectado no sistema. Execute INSTALADOR_AUTOMATICO.bat primeiro.
    pause
    exit /b 1
)

:: Run local web server
python run_web.py
pause
