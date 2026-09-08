"""
Script responsible for building the standalone distribution package for Shopee Agency Pro.
Packages all core source files, creates the self-extracting bootstrap installer,
and outputs 'Instalador_Shopee_Agency_Pro.zip' ready to be sent to clients.
"""

import os
import zipfile
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Alexandre\Documents\Programaçao Finalizado\Leed time")
DIST_DIR = BASE_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

APP_ZIP = DIST_DIR / "app.zip"
FINAL_DIST_ZIP = Path.home() / "Downloads" / "Instalador_Shopee_Agency_Pro.zip"

# Core files and directories to include
CORE_FILES = [
    "config.py",
    "models.py",
    "main.py",
    "requirements.txt",
    "iniciar_calculadora.vbs",
    "iniciar_calculadora.bat",
    "create_shortcut.vbs",
]

CORE_DIRS = [
    "services",
    "database",
    "ui",
]


def build_app_zip():
    print("[1/3] Packaging application files into app.zip...")
    if APP_ZIP.exists():
        APP_ZIP.unlink()

    with zipfile.ZipFile(APP_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CORE_FILES:
            src = BASE_DIR / f
            if src.exists():
                z.write(src, arcname=f)
                print(f"  + Added {f}")

        for d in CORE_DIRS:
            dir_path = BASE_DIR / d
            for root, _, files in os.walk(dir_path):
                if "__pycache__" in root:
                    continue
                for file in files:
                    if file.endswith(".py"):
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(BASE_DIR)
                        z.write(full_path, arcname=str(rel_path))
                        print(f"  + Added {rel_path}")

    print(f"[OK] app.zip created ({APP_ZIP.stat().st_size} bytes)")


def create_installer_bat():
    print("[2/3] Generating INSTALAR.bat...")
    installer_content = r"""@echo off
setlocal
title Instalador Shopee Agency Pro
cd /d "%~dp0"

echo ===============================================================================
echo                INSTALADOR AUTOMATICO - SHOPEE AGENCY PRO                      
echo ===============================================================================
echo.

:: 1. Definir pasta de destino no Disco C:
set "TARGET_DIR=C:\ShopeeAgencyPro"
mkdir "%TARGET_DIR%" 2>nul
if not exist "%TARGET_DIR%" (
    set "TARGET_DIR=%LOCALAPPDATA%\ShopeeAgencyPro"
    mkdir "%TARGET_DIR%" 2>nul
)

echo [+] Instalando em: %TARGET_DIR%
echo.

:: 2. Extrair os arquivos da aplicacao
echo [1/5] Extraindo arquivos da aplicacao...
if exist "app.zip" (
    powershell -Command "Expand-Archive -Path 'app.zip' -DestinationPath '%TARGET_DIR%' -Force"
) else (
    echo [X] Erro: app.zip nao encontrado na mesma pasta do instalador!
    pause
    exit /b 1
)
echo [OK] Arquivos extraidos com sucesso para %TARGET_DIR%

:: 3. Verificar e instalar Python
echo.
echo [2/5] Verificando Python no computador...
where python >nul 2>&1
if not errorlevel 1 goto python_ready

echo [!] Python nao encontrado. Instalando Python automaticamente em segundo plano...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    goto update_env_path
)

echo [+] Baixando instalador oficial do Python...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '$env:TEMP\python_setup.exe'"
echo [+] Instalando Python silenciosamente...
powershell -Command "Start-Process -FilePath '$env:TEMP\python_setup.exe' -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1' -Wait"

:update_env_path
set "PATH=%SystemDrive%\Python312;%SystemDrive%\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

:python_ready
echo [OK] Python verificado com sucesso.

:: 4. Instalar bibliotecas
echo.
echo [3/5] Instalando bibliotecas necessarias (pandas, openpyxl, playwright)...
cd /d "%TARGET_DIR%"
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
echo [OK] Bibliotecas instaladas.

:: 5. Verificar navegador do robo
echo.
echo [4/5] Verificando navegador para o robo Shopee...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" goto browser_ready
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" goto browser_ready
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" goto browser_ready

echo [+] Google Chrome nao detectado. Instalando navegador Chromium integrado...
python -m playwright install chromium

:browser_ready
echo [OK] Navegador pronto.

:: 6. Criar Atalho na Area de Trabalho
echo.
echo [5/5] Criando atalho na Area de Trabalho...
cd /d "%TARGET_DIR%"
cscript //nologo create_shortcut.vbs
echo [OK] Atalho 'Shopee Agency Pro' criado com sucesso na Area de Trabalho!

:: 7. Iniciar a aplicacao
echo.
echo ===============================================================================
echo      INSTALACAO CONCLUIDA COM SUCESSO! ABRINDO O SISTEMA...
echo ===============================================================================
start "" "%TARGET_DIR%\iniciar_calculadora.vbs"

:: 8. Auto-limpeza: Apagar app.zip e auto-excluir o instalador
cd /d "%~dp0"
if exist "app.zip" del /f /q "app.zip" 2>nul

echo [+] Finalizando e limpando arquivos temporarios...
ping 127.0.0.1 -n 3 >nul

:: Auto-excluir este arquivo BAT
(goto) 2>nul & del "%~f0"
exit
"""
    installer_file = DIST_DIR / "INSTALAR.bat"
    with open(installer_file, "w", encoding="utf-8") as f:
        f.write(installer_content)
    print(f"[OK] INSTALAR.bat created at {installer_file}")


def build_final_dist_zip():
    print("[3/3] Creating final distributable zip...")
    if FINAL_DIST_ZIP.exists():
        FINAL_DIST_ZIP.unlink()

    with zipfile.ZipFile(FINAL_DIST_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(DIST_DIR / "INSTALAR.bat", arcname="INSTALAR.bat")
        z.write(DIST_DIR / "app.zip", arcname="app.zip")

    print(f"\n=======================================================")
    print(f"DISTRIBUTION PACKAGE CREATED SUCCESSFULLY!")
    print(f"Location: {FINAL_DIST_ZIP}")
    print(f"Size: {FINAL_DIST_ZIP.stat().st_size} bytes")
    print(f"=======================================================")


if __name__ == "__main__":
    build_app_zip()
    create_installer_bat()
    build_final_dist_zip()
