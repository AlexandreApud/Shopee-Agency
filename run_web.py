"""
Local launcher for Shopee Agency Pro Web Application.
Starts Uvicorn ASGI server and automatically opens the user's browser at http://127.0.0.1:8000.
"""

import sys
import time
import threading
import webbrowser
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from api.index import app


def open_browser():
    """Waits for server to bind then launches default web browser."""
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")


def main():
    """Starts local Uvicorn web server."""
    print("=" * 70)
    print("      SHOPEE AGENCY PRO - SERVIDOR WEB LOCAL INICIADO")
    print("=" * 70)
    print("  * Painel Web Interativo : http://127.0.0.1:8000")
    print("  * Documentacao da API   : http://127.0.0.1:8000/docs")
    print("  * Diagnostico do Sistema: http://127.0.0.1:8000/api/debug")
    print("=" * 70)
    print("Abrindo navegador automaticamente...")
    print("Pressione Ctrl+C para encerrar o servidor quando terminar.\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
