@echo off
setlocal
title Shopee Agency Pro - Instalador e Inicializador Automatico
cd /d "%~dp0"

echo ===============================================================================
echo        SHOPEE AGENCY PRO: CONFIGURACAO AUTOMATICA PARA NOVO COMPUTADOR        
echo ===============================================================================
echo.

:check_python
echo [1/4] Verificando instalacao do Python...
where python >nul 2>&1
if not errorlevel 1 goto python_ok

echo [!] Python nao foi detectado neste computador.
echo [+] Tentando instalar Python 3.12 automaticamente...

where winget >nul 2>&1
if not errorlevel 1 (
    echo [+] Instalando via winget...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    goto refresh_path
)

echo [+] Baixando instalador oficial do Python...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '$env:TEMP\python_setup.exe'"
echo [+] Executando instalador silencioso...
powershell -Command "Start-Process -FilePath '$env:TEMP\python_setup.exe' -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1' -Wait"

:refresh_path
set "PATH=%SystemDrive%\Python312;%SystemDrive%\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [X] Nao foi possivel instalar o Python automaticamente.
    echo     Por favor, baixe e instale o Python em https://www.python.org
    echo     e lembre-se de marcar a opcao 'Add python.exe to PATH'.
    echo.
    pause
    exit /b 1
)

:python_ok
echo [OK] Python detectado com sucesso.

:check_dependencies
echo.
echo [2/4] Verificando bibliotecas necessarias...
python -c "import pandas, openpyxl, playwright" >nul 2>&1
if not errorlevel 1 goto dependencies_ok

echo [+] Instalando bibliotecas necessarias do requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Falha ao instalar pacotes. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

:dependencies_ok
echo [OK] Todas as dependencias estao prontas.

:check_browser
echo.
echo [3/4] Verificando navegador para o robo Shopee...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" goto browser_ok
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" goto browser_ok
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" goto browser_ok

echo [+] Google Chrome nao encontrado. Instalando Chromium integrado para o robo...
python -m playwright install chromium

:browser_ok
echo [OK] Navegador pronto para automacao.

:create_shortcut
echo.
echo [4/4] Criando atalho na Area de Trabalho...
cscript //nologo create_shortcut.vbs
echo [OK] Atalho 'Shopee Agency Pro' criado com sucesso na Area de Trabalho!

echo.
echo ===============================================================================
echo     CONFIGURACAO CONCLUIDA COM SUCESSO! INICIANDO APLICACAO...
echo ===============================================================================

ping 127.0.0.1 -n 3 >nul
start "" pythonw main.py
exit
