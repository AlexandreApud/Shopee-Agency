"""
Build script to compile Shopee Agency Pro into a standalone Windows executable.
Uses PyInstaller to generate dist/ShopeeAgencyPro/ShopeeAgencyPro.exe without terminal console.
"""

import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
SPEC_FILE = BASE_DIR / "ShopeeAgencyPro.spec"


def build_executable() -> bool:
    """Invokes PyInstaller to compile ShopeeAgencyPro.exe."""
    print("=" * 80)
    print("       COMPILADOR STANDALONE: SHOPEE AGENCY PRO (.EXE)       ")
    print("=" * 80)
    print(f"[+] Diretório do projeto: {BASE_DIR}")
    print(f"[+] Arquivo de especificação: {SPEC_FILE.name}")

    if not SPEC_FILE.exists():
        print(f"[X] Erro: Arquivo {SPEC_FILE} não encontrado.")
        return False

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]

    print("\n[1/3] Executando PyInstaller...")
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print("[X] Falha na compilação do executável com PyInstaller.")
        return False

    exe_target = DIST_DIR / "ShopeeAgencyPro" / "ShopeeAgencyPro.exe"
    if not exe_target.exists():
        print(f"[X] Executável não localizado em: {exe_target}")
        return False

    print(f"\n[2/3] Executável gerado com sucesso: {exe_target}")

    # Copy assets into dist
    assets_dist = DIST_DIR / "ShopeeAgencyPro" / "assets"
    assets_dist.mkdir(parents=True, exist_ok=True)
    if (BASE_DIR / "assets" / "icon.ico").exists():
        shutil.copy2(BASE_DIR / "assets" / "icon.ico", assets_dist / "icon.ico")
        print("  + Ícone copiado para dist/ShopeeAgencyPro/assets/icon.ico")

    # Create 1-click desktop shortcut creator inside dist
    shortcut_vbs = DIST_DIR / "ShopeeAgencyPro" / "Criar_Atalho_Area_de_Trabalho.vbs"
    vbs_content = r"""Set oWS = WScript.CreateObject("WScript.Shell")
strDesktop = oWS.SpecialFolders("Desktop")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

Set oLink = oWS.CreateShortcut(strDesktop & "\Shopee Agency Pro.lnk")
oLink.TargetPath = strCurrentDir & "\ShopeeAgencyPro.exe"
oLink.WorkingDirectory = strCurrentDir
oLink.Description = "Shopee Agency Pro - Gestao e Lead Time"
If CreateObject("Scripting.FileSystemObject").FileExists(strCurrentDir & "\assets\icon.ico") Then
    oLink.IconLocation = strCurrentDir & "\assets\icon.ico"
End If
oLink.Save
MsgBox "Atalho 'Shopee Agency Pro' criado com sucesso na Area de Trabalho!", vbInformation, "Shopee Agency Pro"
"""
    with open(shortcut_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_content)
    print("  + Script de criação de atalho na Área de Trabalho gerado.")

    print("\n[3/3] Concluído com êxito!")
    print("=" * 80)
    print(f"PASTA DE DISTRIBUIÇÃO PRONTA: {DIST_DIR / 'ShopeeAgencyPro'}")
    print(f"EXECUTÁVEL PRINCIPAL: {exe_target}")
    print("Para usar em qualquer computador:")
    print("1. Copie a pasta 'ShopeeAgencyPro' para o computador de destino.")
    print("2. Dê dois cliques em 'Criar_Atalho_Area_de_Trabalho.vbs' para criar o ícone na Área de Trabalho.")
    print("3. O sistema abre diretamente com duplo clique sem janelas de terminal!")
    print("=" * 80 + "\n")
    return True


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
