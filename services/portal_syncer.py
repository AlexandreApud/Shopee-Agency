"""
Module responsible for automating browser interactions and data synchronization with Shopee SPX Service Point.
Uses Playwright with a persistent Chrome profile to maintain Google OAuth session cookies.
Combines UI export triggers with direct authenticated API retrieval for maximum resilience.
Portal URLs:
- Login: https://sp.spx.shopee.com.br/login
- Drop-off: https://sp.spx.shopee.com.br/order-management/drop-off
- Collection: https://sp.spx.shopee.com.br/order-management/self-collection
"""

import time
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any, List
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from config import DATA_DIR, DEFAULT_WATCH_DIR

PORTAL_LOGIN_URL = "https://sp.spx.shopee.com.br/login"
DROPOFF_URL = "https://sp.spx.shopee.com.br/order-management/drop-off"
COLLECTION_URL = "https://sp.spx.shopee.com.br/order-management/self-collection"
TASK_LIST_API_URL = "https://sp.spx.shopee.com.br/sp-api/admin/export/task/list"

BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"


def find_chrome_executable() -> Optional[str]:
    """Finds Google Chrome executable across standard Windows installation paths."""
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


class PortalSyncer:
    """
    Automates login session management and report exports from Shopee SPX Service Point.
    """

    def __init__(self, profile_dir: Optional[Path] = None, download_dir: Optional[Path] = None):
        self.profile_dir = profile_dir or BROWSER_PROFILE_DIR
        self.download_dir = download_dir or DEFAULT_WATCH_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def is_session_saved(self) -> bool:
        """Checks if a browser profile directory exists and contains cookies or storage."""
        if not self.profile_dir.exists():
            return False
        default_dir = self.profile_dir / "Default"
        return default_dir.exists() and any(default_dir.iterdir())

    def open_browser_for_login(self, on_status: Optional[Callable[[str], None]] = None) -> bool:
        """
        Launches an interactive Chrome window with the persistent profile.
        Keeps the window open for the user to complete Google OAuth and 2-step verification.
        Does NOT prematurely close Chrome, allowing the user to finish 2FA at their own pace.
        """
        if on_status:
            on_status("Navegador aberto. Faça login com o Google (e conclua o 2FA) com tranquilidade.")

        logged_in = False
        with sync_playwright() as p:
            exec_path = find_chrome_executable()
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                executable_path=exec_path,
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                viewport=None,
            )

            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(PORTAL_LOGIN_URL, timeout=60000)
            except Exception:
                pass

            # Monitor loop: Keep browser open until the user closes it manually
            start_time = time.time()
            while time.time() - start_time < 300:  # 5 minutes window
                try:
                    open_pages = [pg for pg in context.pages if not pg.is_closed()]
                    if not open_pages:
                        break  # User manually closed the browser window

                    # Check if user reached Shopee authenticated area
                    for pg in open_pages:
                        try:
                            u = pg.url.lower()
                            is_in_spx = "sp.spx.shopee.com.br" in u or "spx.shopee.com.br" in u
                            is_out_of_login = "login" not in u and "google" not in u and "accounts.google" not in u

                            if is_in_spx and is_out_of_login:
                                if not logged_in:
                                    logged_in = True
                                    if on_status:
                                        on_status("Login e 2FA concluídos! Pode fechar a janela do Chrome para continuar.")
                        except Exception:
                            pass

                    time.sleep(1)
                except Exception:
                    break

            try:
                context.close()
            except Exception:
                pass

        return logged_in or self.is_session_saved()

    def _trigger_page_export(self, page: Page, url: str, report_label: str, on_status: Optional[Callable[[str], None]]) -> None:
        """
        Navigates to an order management page and clicks Export -> Export to generate a new export task.
        """
        if on_status:
            on_status(f"Navegando para {report_label}...")

        page.goto(url, wait_until="networkidle", timeout=50000)
        page.wait_for_timeout(2000)

        # Session check
        if "login" in page.url.lower():
            raise PermissionError("A sessão da Shopee expirou. Faça login com o Google novamente.")

        if on_status:
            on_status(f"Acionando exportação em {report_label}...")

        # 1. Main Export button
        export_btn = page.locator("button:has-text('Export'), button:has-text('Exportar')").first
        export_btn.wait_for(state="visible", timeout=15000)
        export_btn.click()
        page.wait_for_timeout(1000)

        # 2. Popover Export option
        popover_export = page.locator("div, li, span, button").filter(has_text="Export").filter(has_not_text="History").last
        popover_export.click()
        page.wait_for_timeout(2500)

    def _fetch_and_download_latest_task(
        self,
        page: Page,
        task_type: str,
        report_label: str,
        on_status: Optional[Callable[[str], None]],
        max_wait_seconds: int = 30,
    ) -> Path:
        """
        Polls the Shopee export task list API until the newly created task reaches status 2 (Succeed),
        then downloads the resulting file directly via authenticated HTTP request.
        """
        if on_status:
            on_status(f"Aguardando processamento do relatório de {report_label} na Shopee...")

        start_time = time.time()
        latest_task: Optional[Dict[str, Any]] = None

        while time.time() - start_time < max_wait_seconds:
            try:
                resp = page.request.get(f"{TASK_LIST_API_URL}?count=10&pageno=1")
                data = resp.json()
                items = data.get("data", {}).get("list", [])
                matching = [i for i in items if i.get("type") == task_type and i.get("filename")]
                if matching:
                    # Status 2 indicates completed/ready
                    candidate = matching[0]
                    if candidate.get("status") == 2:
                        latest_task = candidate
                        break
            except Exception:
                pass
            time.sleep(2)

        if not latest_task or not latest_task.get("filename"):
            raise RuntimeError(f"O relatório de {report_label} não concluiu o processamento a tempo na Shopee.")

        # Download directly via authenticated API request
        rel_path = latest_task["filename"].lstrip("/")
        download_url = f"https://sp.spx.shopee.com.br/{rel_path}"
        filename = Path(rel_path).name
        target_path = self.download_dir / filename

        if on_status:
            on_status(f"Baixando arquivo de {report_label}: {filename}...")

        file_resp = page.request.get(download_url)
        with open(target_path, "wb") as f:
            f.write(file_resp.body())

        if on_status:
            on_status(f"Relatório de {report_label} salvo com sucesso! ({target_path.stat().st_size} bytes)")

        return target_path

    def sync_both_reports(
        self,
        headless: bool = True,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Executes complete automated retrieval of Drop-off and Collection reports from the SPX portal.
        """
        drop_file: Optional[Path] = None
        coll_file: Optional[Path] = None

        if on_status:
            on_status("Conectando ao portal Shopee SPX com perfil autenticado...")

        with sync_playwright() as p:
            exec_path = find_chrome_executable()
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                executable_path=exec_path,
                headless=headless,
                downloads_path=str(self.download_dir),
                args=["--disable-blink-features=AutomationControlled"],
            )

            page = context.pages[0] if context.pages else context.new_page()

            # 1. Trigger Drop-off Export
            try:
                self._trigger_page_export(page, DROPOFF_URL, "Drop-off", on_status)
                drop_file = self._fetch_and_download_latest_task(
                    page, "export_dropoff_order_list", "Drop-off", on_status
                )
            except Exception as e:
                if on_status:
                    on_status(f"Aviso Drop-off: {e}")
                raise e

            # 2. Trigger Self-Collection Export
            try:
                self._trigger_page_export(page, COLLECTION_URL, "Retiradas (Self-Collection)", on_status)
                coll_file = self._fetch_and_download_latest_task(
                    page, "export_collection_order_list", "Retiradas", on_status
                )
            except Exception as e:
                if on_status:
                    on_status(f"Aviso Retiradas: {e}")
                raise e

            try:
                context.close()
            except Exception:
                pass

        return drop_file, coll_file
