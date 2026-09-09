"""
Packages the compiled Shopee Agency Pro distribution into a client-ready installer package.
Creates 'Instalador_Shopee_Agency_Pro.zip' ready for distribution to other computers.
"""

import sys
import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
APP_DIR = DIST_DIR / "ShopeeAgencyPro"
OUTPUT_ZIP = DIST_DIR / "Instalador_Shopee_Agency_Pro.zip"


def create_client_package() -> bool:
    """Creates a clean distribution zip with 1-click desktop setup."""
    print("=" * 80)
    print("       EMPACOTADOR DE DISTRIBUIÇÃO: SHOPEE AGENCY PRO       ")
    print("=" * 80)

    exe_file = DIST_DIR / "ShopeeAgencyPro.exe"
    if not exe_file.exists():
        exe_file = APP_DIR / "ShopeeAgencyPro.exe"

    if not exe_file.exists():
        print(f"[X] Executável não encontrado em: {exe_file}")
        print("    Execute 'python build_exe.py' primeiro para compilar o executável.")
        return False

    print(f"[+] Executável localizado: {exe_file} ({exe_file.stat().st_size / (1024 * 1024):.1f} MB)")

    # Generate 1-click INSTALAR_NOVO_COMPUTADOR.bat
    client_installer = DIST_DIR / "INSTALAR_NOVO_COMPUTADOR.bat"
    bat_content = r"""@echo off
setlocal
title Instalador Shopee Agency Pro
cd /d "%~dp0"

echo ===============================================================================
echo                INSTALADOR - SHOPEE AGENCY PRO (EXECUTAVEL NATIVO)             
echo ===============================================================================
echo.

set "TARGET_DIR=C:\ShopeeAgencyPro"
mkdir "%TARGET_DIR%" 2>nul
if not exist "%TARGET_DIR%" (
    set "TARGET_DIR=%LOCALAPPDATA%\ShopeeAgencyPro"
    mkdir "%TARGET_DIR%" 2>nul
)

echo [+] Instalando aplicacao em: %TARGET_DIR%
echo [+] Copiando executavel...

copy /Y "ShopeeAgencyPro.exe" "%TARGET_DIR%\" >nul
if exist "Criar_Atalho_Area_de_Trabalho.vbs" (
    copy /Y "Criar_Atalho_Area_de_Trabalho.vbs" "%TARGET_DIR%\" >nul
)

cd /d "%TARGET_DIR%"
if exist "Criar_Atalho_Area_de_Trabalho.vbs" (
    echo [+] Criando atalho na Area de Trabalho...
    cscript //nologo Criar_Atalho_Area_de_Trabalho.vbs
)

echo.
echo ===============================================================================
echo      INSTALACAO CONCLUIDA! O ATALHO FOI CRIADO NA AREA DE TRABALHO.
echo ===============================================================================
echo Abrindo o sistema agora...
start "" "%TARGET_DIR%\ShopeeAgencyPro.exe"
exit
"""
    with open(client_installer, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"  + Gerado {client_installer.name}")

    shortcut_vbs = DIST_DIR / "Criar_Atalho_Area_de_Trabalho.vbs"
    if not shortcut_vbs.exists():
        vbs_content = r"""Set oWS = WScript.CreateObject("WScript.Shell")
strDesktop = oWS.SpecialFolders("Desktop")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

Set oLink = oWS.CreateShortcut(strDesktop & "\Shopee Agency Pro.lnk")
oLink.TargetPath = strCurrentDir & "\ShopeeAgencyPro.exe"
oLink.WorkingDirectory = strCurrentDir
oLink.Description = "Shopee Agency Pro - Gestao e Lead Time"
oLink.Save
MsgBox "Atalho 'Shopee Agency Pro' criado com sucesso na Area de Trabalho!", vbInformation, "Shopee Agency Pro"
"""
        with open(shortcut_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_content)

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    print(f"\n[+] Criando arquivo compactado: {OUTPUT_ZIP.name}...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(client_installer, arcname="INSTALAR_NOVO_COMPUTADOR.bat")
        z.write(shortcut_vbs, arcname="Criar_Atalho_Area_de_Trabalho.vbs")
        z.write(exe_file, arcname="ShopeeAgencyPro.exe")

    print(f"[OK] Pacote gerado com sucesso!")
    print(f"     Destino: {OUTPUT_ZIP}")
    print(f"     Tamanho: {OUTPUT_ZIP.stat().st_size / (1024 * 1024):.1f} MB")
    print("=" * 80 + "\n")
    return True



if __name__ == "__main__":
    success = create_client_package()
    sys.exit(0 if success else 1)
