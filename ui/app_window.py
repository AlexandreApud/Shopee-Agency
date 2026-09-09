"""
Graphical User Interface (GUI) module for Shopee Drop-off & Collection Lead Time and Revenue Calculator.
- Clean tabbed interface: Tab 1 for Current Month operations, Tab 2 for Historical Past Months.
- Automatic SPX portal synchronization via Playwright with saved Google session.
- Excludes Collection from Lead Time (strictly measures Drop-off in agency business hours).
- Pools Postagens and Retiradas in progressive monthly tiers (from R$ 0,70).
- Local SQLite database persistence and multi-month historical navigation.
- Modern responsive layout with native window maximization ('zoomed') and scrollable viewport.
"""

import os
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from config import (
    DEFAULT_WATCH_DIR,
    DEFAULT_OUTPUT_DIR,
    get_latest_dropoff_file,
    get_latest_collection_file,
)
from services import (
    ExcelLoader,
    LeadTimeCalculator,
    RevenueCalculator,
    ExcelExporter,
    PortalSyncer,
)
from services.monthly_engine import MonthlyEngine
from database.repository import PackageRepository
from models import LeadTimeSummary, RevenueSummary


class ScrollableFrame(tk.Frame):
    """
    A responsive scrollable container that expands to fill the available width
    and supports vertical scrolling via mouse wheel and scrollbar.
    """

    def __init__(self, parent: tk.Widget, bg: str = "#F8FAFC", **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_content = tk.Frame(self.canvas, bg=bg)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_content, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Expand inner frame to match canvas width on resize
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel recursively
        self.bind_mousewheel(self)
        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.scrollable_content)

    def _on_canvas_configure(self, event: tk.Event) -> None:
        """Ensures inner frame expands to match current canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def bind_mousewheel(self, widget: tk.Widget) -> None:
        """Recursively binds mouse wheel scrolling across children."""
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel(child)

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Scrolls canvas with mouse wheel."""
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class LeadTimeApp(tk.Tk):
    """
    Main application window providing a clean, modern, tabbed interface:
    - Tab 1: Current Month daily operations, SPX sync, and live KPIs.
    - Tab 2: Historical past months query and monthly Excel export.
    """

    def __init__(self):
        super().__init__()
        self.title("Shopee Agency Pro - Gestão Financeira, Lead Time Útil & Histórico")

        # Set window icon if available
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Responsive window setup: Start natively maximized on Windows

        try:
            self.state("zoomed")
        except Exception:
            self.geometry("1100x850")
        self.minsize(980, 700)
        self.configure(bg="#F8FAFC")

        self.repo = PackageRepository()
        self.monthly_engine = MonthlyEngine(self.repo)
        self.syncer = PortalSyncer()
        self.exporter = ExcelExporter(DEFAULT_OUTPUT_DIR)

        self.current_month_str = datetime.now().strftime("%Y-%m")

        # Initial auto-discovered file paths
        dropoff_file = get_latest_dropoff_file()
        collection_file = get_latest_collection_file()

        self.dropoff_path_var = tk.StringVar(value=str(dropoff_file) if dropoff_file else "")
        self.collection_path_var = tk.StringVar(value=str(collection_file) if collection_file else "")
        self.update_in_place_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Pronto. Sincronize com a Shopee ou consulte o histórico.")

        # References to generated/updated files
        self.last_dropoff_file: Optional[Path] = None
        self.last_collection_file: Optional[Path] = None

        self._setup_styles()
        self._build_header()
        self._build_notebook_tabs()
        self._build_status_bar()

        # Automatically load current month stats on startup
        self._load_current_month_data()
        self.bind("<FocusIn>", lambda e: self.refresh_session_status())
        self._schedule_session_check()

    def refresh_session_status(self) -> bool:
        """
        Dynamically verifies Google/Shopee session via cookies inspection
        and updates the modern UI status badge.
        """
        is_connected = self.syncer.has_shopee_session()
        if hasattr(self, "lbl_session_status"):
            if is_connected:
                self.lbl_session_status.config(
                    text="🟢 Shopee SPX: Conectado ✅",
                    bg="#ECFDF5",
                    fg="#065F46",
                )
            else:
                self.lbl_session_status.config(
                    text="🟡 Shopee SPX: Sessão Pendente ⚠️",
                    bg="#FFFBEB",
                    fg="#92400E",
                )
        return is_connected

    def _schedule_session_check(self) -> None:
        """Periodically refreshes session status every 5 seconds."""
        self.refresh_session_status()
        self.after(5000, self._schedule_session_check)

    def _setup_styles(self) -> None:
        """Configures ttk styles for a clean, modern SaaS appearance."""
        style = ttk.Style(self)
        style.theme_use("clam")

        # Notebook tabs styling
        style.configure("TNotebook", background="#F8FAFC", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=(24, 10),
            background="#E2E8F0",
            foreground="#475569",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#FFFFFF"), ("active", "#F1F5F9")],
            foreground=[("selected", "#EE4D2D")],
        )

        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 11, "bold"),
            background="#EE4D2D",
            foreground="#FFFFFF",
            padding=(20, 8),
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", "#D73819")])

        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#F1F5F9",
            foreground="#1E293B",
            padding=(10, 5),
            borderwidth=1,
        )
        style.map("Secondary.TButton", background=[("active", "#E2E8F0")])

        style.configure(
            "History.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#0F172A",
            foreground="#FFFFFF",
            padding=(14, 6),
            borderwidth=0,
        )
        style.map("History.TButton", background=[("active", "#1E293B")])

        style.configure(
            "Sync.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#2563EB",
            foreground="#FFFFFF",
            padding=(14, 6),
            borderwidth=0,
        )
        style.map("Sync.TButton", background=[("active", "#1D4ED8")])

    def _build_header(self) -> None:
        """Builds top modern header banner with branding and session pill."""
        header_frame = tk.Frame(self, bg="#0F172A", height=78)
        header_frame.pack(fill="x", side="top")

        # Accent top bar (Shopee orange)
        accent_bar = tk.Frame(header_frame, bg="#EE4D2D", height=3)
        accent_bar.pack(fill="x", side="top")

        container = tk.Frame(header_frame, bg="#0F172A")
        container.pack(fill="both", expand=True, padx=20, pady=8)

        # Left branding
        brand_frame = tk.Frame(container, bg="#0F172A")
        brand_frame.pack(side="left", fill="y")

        title_label = tk.Label(
            brand_frame,
            text="SHOPEE AGENCY PRO",
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#0F172A",
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            brand_frame,
            text="Gestão Operacional, Faturamento Consolidado & Lead Time Útil",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A",
        )
        subtitle_label.pack(anchor="w")

        # Right session badge and business hours pill
        right_frame = tk.Frame(container, bg="#0F172A")
        right_frame.pack(side="right", fill="y")

        hours_lbl = tk.Label(
            right_frame,
            text="🕒 Horário Útil: Seg-Sex 08:00–19:30 | Sáb 09:00–15:00",
            font=("Segoe UI", 8, "bold"),
            fg="#F59E0B",
            bg="#1E293B",
            padx=10,
            pady=4,
        )
        hours_lbl.pack(side="right", padx=(10, 0))

        is_connected = self.syncer.has_shopee_session()
        self.lbl_session_status = tk.Label(
            right_frame,
            text="🟢 Shopee SPX: Conectado ✅" if is_connected else "🟡 Shopee SPX: Sessão Pendente ⚠️",
            font=("Segoe UI", 8, "bold"),
            bg="#ECFDF5" if is_connected else "#FFFBEB",
            fg="#065F46" if is_connected else "#92400E",
            padx=10,
            pady=4,
            relief="solid",
            bd=1,
        )
        self.lbl_session_status.pack(side="right")

    def _build_notebook_tabs(self) -> None:
        """Builds tabbed view separating Current Month from Past Months History."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(10, 4))

        # Tab 1: Mês Atual
        self.tab_current_container = ScrollableFrame(self.notebook, bg="#F8FAFC")
        self.tab_current = self.tab_current_container.scrollable_content
        self.notebook.add(self.tab_current_container, text="📊  Mês Atual (Setembro/2026)")
        self._build_current_month_tab(self.tab_current)

        # Tab 2: Histórico de Meses Anteriores
        self.tab_history_container = ScrollableFrame(self.notebook, bg="#F8FAFC")
        self.tab_history = self.tab_history_container.scrollable_content
        self.notebook.add(self.tab_history_container, text="📅  Histórico de Meses Anteriores")
        self._build_history_tab(self.tab_history)

        # Make sure scrollwheel works on inner controls
        self.tab_current_container.bind_mousewheel(self.tab_current)
        self.tab_history_container.bind_mousewheel(self.tab_history)

    # =========================================================================
    # TAB 1: CURRENT MONTH (MÊS ATUAL)
    # =========================================================================
    def _build_current_month_tab(self, parent: tk.Widget) -> None:
        """Builds the main operational tab for the current month."""
        # 1. Automation Bar
        auto_card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        auto_card.pack(fill="x", padx=10, pady=(10, 6))

        a_inner = tk.Frame(auto_card, bg="#FFFFFF", padx=14, pady=10)
        a_inner.pack(fill="x")

        lbl_spx = tk.Label(
            a_inner,
            text="🤖 Automação Shopee SPX:",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
        )
        lbl_spx.pack(side="left", padx=(0, 10))

        btn_sync = ttk.Button(
            a_inner,
            text="⚡ Sincronizar Agora (Download Automático)",
            style="Sync.TButton",
            command=self._start_portal_sync_thread,
        )
        btn_sync.pack(side="left", padx=6)

        btn_login = tk.Button(
            a_inner,
            text="🔑 Conectar / Reconectar Conta",
            font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9",
            fg="#1E293B",
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._start_login_browser_thread,
        )
        btn_login.pack(side="left", padx=6)

        btn_refresh = tk.Button(
            a_inner,
            text="🔄 Atualizar Status",
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#475569",
            relief="groove",
            cursor="hand2",
            padx=8,
            pady=3,
            command=lambda: [self.refresh_session_status(), self._load_current_month_data()],
        )
        btn_refresh.pack(side="right", padx=(6, 0))

        # 2. Local File Fallback Ingestion
        file_card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        file_card.pack(fill="x", padx=10, pady=(0, 8))

        f_inner = tk.Frame(file_card, bg="#FFFFFF", padx=14, pady=10)
        f_inner.pack(fill="x")

        f_top = tk.Frame(f_inner, bg="#FFFFFF")
        f_top.pack(fill="x", pady=(0, 6))

        tk.Label(
            f_top,
            text="Ou selecione arquivos locais manualmente:",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            fg="#334155",
        ).pack(side="left")

        auto_find_btn = tk.Button(
            f_top,
            text="🔍 Localizar Automaticamente em Downloads",
            font=("Segoe UI", 8, "bold"),
            bg="#EFF6FF",
            fg="#2563EB",
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=8,
            pady=2,
            command=self._handle_auto_find_both_files,
        )
        auto_find_btn.pack(side="right")

        # Row Drop-off
        r_drop = tk.Frame(f_inner, bg="#FFFFFF")
        r_drop.pack(fill="x", pady=2)
        tk.Label(r_drop, text="Drop-off:", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", width=10, anchor="w", fg="#475569").pack(side="left")
        tk.Entry(r_drop, textvariable=self.dropoff_path_var, font=("Segoe UI", 8), bd=1, relief="solid").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(r_drop, text="Procurar...", style="Secondary.TButton", command=self._handle_browse_dropoff).pack(side="right")

        # Row Collection
        r_coll = tk.Frame(f_inner, bg="#FFFFFF")
        r_coll.pack(fill="x", pady=2)
        tk.Label(r_coll, text="Retiradas:", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", width=10, anchor="w", fg="#475569").pack(side="left")
        tk.Entry(r_coll, textvariable=self.collection_path_var, font=("Segoe UI", 8), bd=1, relief="solid").pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(r_coll, text="Procurar...", style="Secondary.TButton", command=self._handle_browse_collection).pack(side="right")

        # 3. Main Action Button
        action_frame = tk.Frame(parent, bg="#F8FAFC")
        action_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_calculate = ttk.Button(
            action_frame,
            text="▶  PROCESSAR PLANILHAS E GRAVAR NO MÊS ATUAL",
            style="Primary.TButton",
            command=self._start_processing_thread,
        )
        self.btn_calculate.pack(fill="x", ipady=4)

        # 4. Current Month Dashboard KPIs (Responsive Grid)
        lbl_fin = tk.Label(
            parent,
            text="INDICADORES FINANCEIROS CONSOLIDADOS (MÊS ATUAL)",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        lbl_fin.pack(anchor="w", padx=10, pady=(2, 4))

        fin_grid = tk.Frame(parent, bg="#F8FAFC")
        fin_grid.pack(fill="x", padx=6, pady=(0, 10))
        for col_idx in range(4):
            fin_grid.grid_columnconfigure(col_idx, weight=1)

        self.cur_card_total_rev = self._create_modern_kpi_card(
            fin_grid, "FATURAMENTO TOTAL DO MÊS", "R$ --,--", "Devoluções + Postagens + Retiradas", val_color="#059669", accent_color="#10B981"
        )
        self.cur_card_total_rev.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)

        self.cur_card_returns = self._create_modern_kpi_card(
            fin_grid, "DEVOLUÇÕES (R$ 0,80)", "-- un", "R$ --,-- faturados", val_color="#2563EB", accent_color="#3B82F6"
        )
        self.cur_card_returns.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)

        self.cur_card_pooled_postagem = self._create_modern_kpi_card(
            fin_grid, "POSTAGENS + RETIRADAS (POOL)", "-- un", "R$ --,-- faturados (Faixas)", val_color="#1E293B", accent_color="#64748B"
        )
        self.cur_card_pooled_postagem.grid(row=0, column=2, sticky="nsew", padx=4, pady=2)

        self.cur_card_volume_moved = self._create_modern_kpi_card(
            fin_grid, "VOLUME TOTAL FATURÁVEL", "-- un", "Saíram vs Recebidos", val_color="#7C3AED", accent_color="#8B5CF6"
        )
        self.cur_card_volume_moved.grid(row=0, column=3, sticky="nsew", padx=4, pady=2)

        # 5. Lead Time Hero Card
        lbl_ops = tk.Label(
            parent,
            text="LEAD TIME ÚTIL DA AGÊNCIA (DROP-OFF ATÉ O CAMINHÃO)",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        lbl_ops.pack(anchor="w", padx=10, pady=(4, 4))

        lead_card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        lead_card.pack(fill="x", padx=10, pady=(0, 10))

        lead_top = tk.Frame(lead_card, bg="#EA580C", height=3)
        lead_top.pack(fill="x", side="top")

        lead_inner = tk.Frame(lead_card, bg="#FFFFFF", padx=16, pady=12)
        lead_inner.pack(fill="x")

        lbl_lead_title = tk.Label(
            lead_inner,
            text="TEMPO MÉDIO DE PERMANÊNCIA EM HORÁRIO DE FUNCIONAMENTO (MÊS ATUAL)",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            fg="#64748B",
        )
        lbl_lead_title.pack(anchor="w")

        self.cur_lbl_lead_value = tk.Label(
            lead_inner,
            text="--:--:--",
            font=("Segoe UI", 26, "bold"),
            bg="#FFFFFF",
            fg="#EA580C",
        )
        self.cur_lbl_lead_value.pack(anchor="w", pady=(2, 2))

        self.cur_lbl_lead_details = tk.Label(
            lead_inner,
            text="Média em minutos: -- | Horário de funcionamento: Seg-Sex 08h-19h30, Sáb 09h-15h",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#475569",
        )
        self.cur_lbl_lead_details.pack(anchor="w")

        b_sub = tk.Frame(lead_card, bg="#F8FAFC", bd=1, relief="solid")
        b_sub.pack(fill="x", side="bottom")

        self.cur_lbl_ops_footer = tk.Label(
            b_sub,
            text="Menor tempo: --  |  Maior tempo: --  |  Mediana: --  |  Pacotes despachados: --",
            font=("Segoe UI", 8, "bold"),
            bg="#F8FAFC",
            fg="#334155",
            padx=14,
            pady=6,
        )
        self.cur_lbl_ops_footer.pack(anchor="w")

    # =========================================================================
    # TAB 2: HISTORICAL PAST MONTHS (HISTÓRICO DE MESES ANTERIORES)
    # =========================================================================
    def _build_history_tab(self, parent: tk.Widget) -> None:
        """Builds the dedicated tab for past months exploration."""
        top_hist = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        top_hist.pack(fill="x", padx=10, pady=(10, 8))

        t_row = tk.Frame(top_hist, bg="#FFFFFF", padx=14, pady=10)
        t_row.pack(fill="x")

        lbl_sel = tk.Label(
            t_row,
            text="Selecione o Mês para Consultar:",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
        )
        lbl_sel.pack(side="left", padx=(0, 8))

        self.hist_month_combo = ttk.Combobox(t_row, state="readonly", width=16, font=("Segoe UI", 10))
        self.hist_month_combo.pack(side="left", padx=6)

        btn_load = ttk.Button(
            t_row, text="Consultar Mês Passado", style="History.TButton", command=self._handle_load_past_month
        )
        btn_load.pack(side="left", padx=8)

        btn_export = tk.Button(
            t_row,
            text="📥 Exportar Mês em Planilha Excel",
            font=("Segoe UI", 9, "bold"),
            bg="#ECFDF5",
            fg="#059669",
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=12,
            pady=5,
            command=self._handle_export_history_month_excel,
        )
        btn_export.pack(side="right")

        # Historical KPI Section (Responsive Grid)
        lbl_hist_fin = tk.Label(
            parent,
            text="INDICADORES FINANCEIROS DO MÊS CONSULTADO",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        lbl_hist_fin.pack(anchor="w", padx=10, pady=(4, 4))

        hist_fin_grid = tk.Frame(parent, bg="#F8FAFC")
        hist_fin_grid.pack(fill="x", padx=6, pady=(0, 8))
        for col_idx in range(4):
            hist_fin_grid.grid_columnconfigure(col_idx, weight=1)

        self.hist_card_total_rev = self._create_modern_kpi_card(
            hist_fin_grid, "FATURAMENTO DO MÊS", "R$ --,--", "Total faturado no mês", val_color="#059669", accent_color="#10B981"
        )
        self.hist_card_total_rev.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)

        self.hist_card_returns = self._create_modern_kpi_card(
            hist_fin_grid, "DEVOLUÇÕES (R$ 0,80)", "-- un", "R$ --,-- faturados", val_color="#2563EB", accent_color="#3B82F6"
        )
        self.hist_card_returns.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)

        self.hist_card_pooled_postagem = self._create_modern_kpi_card(
            hist_fin_grid, "POSTAGENS + RETIRADAS", "-- un", "R$ --,-- faturados", val_color="#1E293B", accent_color="#64748B"
        )
        self.hist_card_pooled_postagem.grid(row=0, column=2, sticky="nsew", padx=4, pady=2)

        self.hist_card_volume_moved = self._create_modern_kpi_card(
            hist_fin_grid, "VOLUME DO MÊS", "-- un", "Soma de todos os pacotes", val_color="#7C3AED", accent_color="#8B5CF6"
        )
        self.hist_card_volume_moved.grid(row=0, column=3, sticky="nsew", padx=4, pady=2)

        # Historical Tier Breakdown Details Card
        self.hist_tier_card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        self.hist_tier_card.pack(fill="x", padx=10, pady=(0, 8))

        t_accent = tk.Frame(self.hist_tier_card, bg="#3B82F6", height=3)
        t_accent.pack(fill="x", side="top")

        t_body = tk.Frame(self.hist_tier_card, bg="#FFFFFF", padx=14, pady=10)
        t_body.pack(fill="x")

        lbl_tier_title = tk.Label(
            t_body,
            text="DETALHAMENTO DE FAIXAS PROGRESSIVAS DO MÊS",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
        )
        lbl_tier_title.pack(anchor="w", pady=(0, 4))

        self.lbl_hist_tiers_detail = tk.Label(
            t_body,
            text="Selecione um mês anterior acima para visualizar a distribuição das faixas de remuneração.",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#475569",
            justify="left",
        )
        self.lbl_hist_tiers_detail.pack(anchor="w")

        # Historical Operational Lead Time Card
        lbl_hist_ops = tk.Label(
            parent,
            text="LEAD TIME ÚTIL DO MÊS CONSULTADO (DROP-OFF)",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        lbl_hist_ops.pack(anchor="w", padx=10, pady=(4, 4))

        hist_lead_card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
        hist_lead_card.pack(fill="x", padx=10, pady=(0, 10))

        h_lead_top = tk.Frame(hist_lead_card, bg="#EA580C", height=3)
        h_lead_top.pack(fill="x", side="top")

        h_lead_body = tk.Frame(hist_lead_card, bg="#FFFFFF", padx=16, pady=10)
        h_lead_body.pack(fill="x")

        self.hist_lbl_lead_value = tk.Label(
            h_lead_body,
            text="--:--:--",
            font=("Segoe UI", 24, "bold"),
            bg="#FFFFFF",
            fg="#EA580C",
        )
        self.hist_lbl_lead_value.pack(anchor="w", pady=(0, 2))

        self.hist_lbl_lead_details = tk.Label(
            h_lead_body,
            text="Média em minutos: -- | Mediana: -- | Despachados: --",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#64748B",
        )
        self.hist_lbl_lead_details.pack(anchor="w")

        self._refresh_history_months_dropdown()

    # =========================================================================
    # HELPERS & UI COMPONENTS
    # =========================================================================
    def _create_modern_kpi_card(
        self,
        parent: tk.Widget,
        title: str,
        value: str,
        subtitle: str,
        val_color: str = "#0F172A",
        accent_color: str = "#CBD5E1",
    ) -> tk.Frame:
        """Helper to create standardized, responsive modern KPI card."""
        card = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid")

        top_accent = tk.Frame(card, bg=accent_color, height=3)
        top_accent.pack(fill="x", side="top")

        content = tk.Frame(card, bg="#FFFFFF", padx=12, pady=10)
        content.pack(fill="both", expand=True)

        lbl_title = tk.Label(content, text=title, font=("Segoe UI", 8, "bold"), bg="#FFFFFF", fg="#64748B")
        lbl_title.pack(anchor="w")

        lbl_value = tk.Label(content, text=value, font=("Segoe UI", 16, "bold"), bg="#FFFFFF", fg=val_color)
        lbl_value.pack(anchor="w", pady=(4, 2))

        lbl_sub = tk.Label(
            content,
            text=subtitle,
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#94A3B8",
            wraplength=260,
            justify="left",
        )
        lbl_sub.pack(anchor="w")

        card.lbl_value = lbl_value
        card.lbl_sub = lbl_sub
        return card

    def _build_status_bar(self) -> None:
        """Builds bottom bar with quick open buttons and status text."""
        bar = tk.Frame(self, bg="#E2E8F0", height=42)
        bar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            bar,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#E2E8F0",
            fg="#334155",
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=14, pady=8)

        self.btn_open_dropoff = tk.Button(
            bar,
            text="Abrir Drop-off no Excel",
            font=("Segoe UI", 8, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief="flat",
            state="disabled",
            cursor="hand2",
            padx=10,
            command=lambda: self._open_file(self.last_dropoff_file),
        )
        self.btn_open_dropoff.pack(side="right", padx=(2, 10), pady=6)

        self.btn_open_collection = tk.Button(
            bar,
            text="Abrir Retiradas",
            font=("Segoe UI", 8, "bold"),
            bg="#8B5CF6",
            fg="#FFFFFF",
            relief="flat",
            state="disabled",
            cursor="hand2",
            padx=10,
            command=lambda: self._open_file(self.last_collection_file),
        )
        self.btn_open_collection.pack(side="right", padx=2, pady=6)

    def _load_current_month_data(self) -> None:
        """Loads and updates Tab 1 with current month data from SQLite."""
        lead_s, rev_s, d_df, c_df = self.monthly_engine.compute_month_summary(self.current_month_str)

        self.cur_card_total_rev.lbl_value.config(text=f"R$ {rev_s.total_revenue:.2f}")
        self.cur_card_total_rev.lbl_sub.config(text=f"Ticket Médio: R$ {rev_s.average_ticket:.2f} / un")

        self.cur_card_returns.lbl_value.config(text=f"{rev_s.return_count} un")
        self.cur_card_returns.lbl_sub.config(text=f"R$ {rev_s.return_revenue:.2f} faturados")

        self.cur_card_pooled_postagem.lbl_value.config(text=f"{rev_s.pooled_postagem_count} un")
        self.cur_card_pooled_postagem.lbl_sub.config(
            text=f"{rev_s.standard_drop_count} post. + {rev_s.collection_count} ret. (Faixa 1: R$ 0,70)"
        )

        self.cur_card_volume_moved.lbl_value.config(
            text=f"{rev_s.total_dispatched_count} un faturáveis"
        )
        self.cur_card_volume_moved.lbl_sub.config(
            text=f"Saíram: {rev_s.dispatched_drop_count} post. + {rev_s.collected_count} ret. | Recebidos: {rev_s.inbound_total_count} un | {rev_s.total_pending_count} no ponto"
        )

        if lead_s and lead_s.dispatched_packages > 0:
            avg_drop = LeadTimeCalculator.format_timedelta(lead_s.average_business_time)
            med_drop = LeadTimeCalculator.format_timedelta(lead_s.median_business_time)
            min_drop = LeadTimeCalculator.format_timedelta(lead_s.min_business_time)
            max_drop = LeadTimeCalculator.format_timedelta(lead_s.max_business_time)

            self.cur_lbl_lead_value.config(text=avg_drop)
            self.cur_lbl_lead_details.config(
                text=f"Média em minutos: {lead_s.average_business_minutes:.1f} min ({lead_s.dispatched_packages} pacotes despachados no mês)"
            )
            self.cur_lbl_ops_footer.config(
                text=f"Menor tempo: {min_drop}  |  Maior tempo: {max_drop}  |  Mediana: {med_drop}  |  Pendentes na Agência: {lead_s.pending_packages}"
            )
        else:
            self.cur_lbl_lead_value.config(text="--:--:--")
            self.cur_lbl_lead_details.config(text="Nenhum pacote despachado no mês atual ainda.")

    def _refresh_history_months_dropdown(self) -> None:
        """Populates the history combobox with past months from SQLite."""
        all_months = self.monthly_engine.get_available_months()
        past_months = [m for m in all_months if m != self.current_month_str]
        self.hist_month_combo["values"] = past_months if past_months else all_months
        if past_months:
            self.hist_month_combo.current(0)
            self._handle_load_past_month()
        elif all_months:
            self.hist_month_combo.current(0)

    def _handle_load_past_month(self) -> None:
        """Loads and displays metrics for the selected historical month."""
        selected_month = self.hist_month_combo.get().strip()
        if not selected_month:
            return

        lead_s, rev_s, d_df, c_df = self.monthly_engine.compute_month_summary(selected_month)

        self.hist_card_total_rev.lbl_value.config(text=f"R$ {rev_s.total_revenue:.2f}")
        self.hist_card_total_rev.lbl_sub.config(text=f"Ticket Médio: R$ {rev_s.average_ticket:.2f} / un")

        self.hist_card_returns.lbl_value.config(text=f"{rev_s.return_count} un")
        self.hist_card_returns.lbl_sub.config(text=f"R$ {rev_s.return_revenue:.2f} faturados")

        self.hist_card_pooled_postagem.lbl_value.config(text=f"{rev_s.pooled_postagem_count} un")
        self.hist_card_pooled_postagem.lbl_sub.config(
            text=f"{rev_s.standard_drop_count} post. + {rev_s.collection_count} retiradas"
        )

        self.hist_card_volume_moved.lbl_value.config(
            text=f"{rev_s.total_dispatched_count} un faturáveis"
        )
        self.hist_card_volume_moved.lbl_sub.config(
            text=f"Saíram: {rev_s.dispatched_drop_count} post. + {rev_s.collected_count} ret. | Recebidos: {rev_s.inbound_total_count} un | {rev_s.total_pending_count} no ponto"
        )

        tier_str = (
            f"• Mês {selected_month}: {rev_s.total_packages_moved} pacotes no total ({rev_s.standard_drop_count} postagens + {rev_s.collection_count} retiradas + {rev_s.return_count} devoluções)\n"
            f"  - Faixa 1 (1 a 500 un a R$ 0,70): {rev_s.tier1_count} un -> R$ {rev_s.tier1_revenue:.2f}\n"
        )
        if rev_s.tier2_count > 0:
            tier_str += f"  - Faixa 2 (501 a 1000 un a R$ 0,60): {rev_s.tier2_count} un -> R$ {rev_s.tier2_revenue:.2f}\n"
        if rev_s.tier3_count > 0:
            tier_str += f"  - Faixa 3 (1001 a 1500 un a R$ 0,50): {rev_s.tier3_count} un -> R$ {rev_s.tier3_revenue:.2f}\n"
        tier_str += f"  - Faturamento Total Fechado: R$ {rev_s.total_revenue:.2f}"
        self.lbl_hist_tiers_detail.config(text=tier_str)

        if lead_s and lead_s.dispatched_packages > 0:
            avg_drop = LeadTimeCalculator.format_timedelta(lead_s.average_business_time)
            med_drop = LeadTimeCalculator.format_timedelta(lead_s.median_business_time)
            self.hist_lbl_lead_value.config(text=avg_drop)
            self.hist_lbl_lead_details.config(
                text=f"Média: {lead_s.average_business_minutes:.1f} min | Mediana: {med_drop} | {lead_s.dispatched_packages} pacotes despachados no mês"
            )
        else:
            self.hist_lbl_lead_value.config(text="--:--:--")
            self.hist_lbl_lead_details.config(text="Sem pacotes de drop-off despachados neste mês.")

    def _handle_export_history_month_excel(self) -> None:
        """Exports the selected past month to an Excel workbook."""
        selected_month = self.hist_month_combo.get().strip()
        if not selected_month:
            messagebox.showinfo("Aviso", "Selecione um mês para exportar.")
            return

        lead_s, rev_s, d_df, c_df = self.monthly_engine.compute_month_summary(selected_month)

        avg_b = LeadTimeCalculator.format_timedelta(lead_s.average_business_time) if lead_s else "--"
        med_b = LeadTimeCalculator.format_timedelta(lead_s.median_business_time) if lead_s else "--"
        min_b = LeadTimeCalculator.format_timedelta(lead_s.min_business_time) if lead_s else "--"
        max_b = LeadTimeCalculator.format_timedelta(lead_s.max_business_time) if lead_s else "--"

        ops_dict = lead_s.to_metrics_dictionary(avg_b, med_b, min_b, max_b, "--") if lead_s else {}
        fin_dict = rev_s.to_metrics_dictionary()

        try:
            out_file = self.exporter.export_monthly_report(selected_month, ops_dict, fin_dict, d_df, c_df)
            messagebox.showinfo("Exportação Concluída", f"Relatório do mês {selected_month} salvo em:\n{out_file}")
            os.startfile(out_file)
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", str(e))

    def _handle_browse_dropoff(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecione o arquivo de Drop-off (Postagens e Devoluções)",
            initialdir=str(DEFAULT_WATCH_DIR if DEFAULT_WATCH_DIR.exists() else Path.home()),
            filetypes=[("Arquivos Excel/CSV", "*.xlsx *.csv *.xls"), ("Todos os Arquivos", "*.*")],
        )
        if selected:
            self.dropoff_path_var.set(selected)

    def _handle_browse_collection(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecione o arquivo de Retiradas (Collection)",
            initialdir=str(DEFAULT_WATCH_DIR if DEFAULT_WATCH_DIR.exists() else Path.home()),
            filetypes=[("Arquivos CSV/Excel", "*.csv *.xlsx *.xls"), ("Todos os Arquivos", "*.*")],
        )
        if selected:
            self.collection_path_var.set(selected)

    def _handle_auto_find_both_files(self) -> None:
        drop = get_latest_dropoff_file()
        coll = get_latest_collection_file()

        if drop:
            self.dropoff_path_var.set(str(drop))
        if coll:
            self.collection_path_var.set(str(coll))

        if drop and coll:
            self.status_var.set(f"Localizados: {drop.name} e {coll.name}")
        elif drop:
            self.status_var.set(f"Localizado Drop-off: {drop.name}")
        elif coll:
            self.status_var.set(f"Localizado Retiradas: {coll.name}")
        else:
            messagebox.showinfo("Aviso", "Nenhum arquivo recente da Shopee encontrado em Downloads.")

    def _start_login_browser_thread(self) -> None:
        self.status_var.set("Abrindo navegador para login no portal Shopee SPX...")
        thread = threading.Thread(target=self._run_login_browser, daemon=True)
        thread.start()

    def _run_login_browser(self) -> None:
        try:
            success = self.syncer.open_browser_for_login(lambda msg: self.status_var.set(msg))
            self.after(0, self._update_session_indicator, success)
        except Exception as e:
            if "Target" in str(e) or "closed" in str(e) or "Context" in str(e):
                self.after(0, self._update_session_indicator, self.syncer.has_shopee_session())
            else:
                self.after(0, self._show_error, f"Erro ao abrir navegador: {e}")

    def _update_session_indicator(self, success: bool) -> None:
        is_conn = success or self.syncer.has_shopee_session()
        if is_conn:
            self.lbl_session_status.config(
                text="🟢 Shopee SPX: Conectado ✅",
                bg="#ECFDF5",
                fg="#065F46",
            )
            self.status_var.set("Sessão da Shopee conectada! Você pode usar a Sincronização Automática.")
            messagebox.showinfo("Sucesso", "Conta conectada com sucesso! O robô agora pode baixar os relatórios.")
        else:
            self.lbl_session_status.config(
                text="🟡 Shopee SPX: Sessão Pendente ⚠️",
                bg="#FFFBEB",
                fg="#92400E",
            )
            self.status_var.set("Janela de login fechada.")

    def _start_portal_sync_thread(self) -> None:
        self.status_var.set("Iniciando download automático no portal Shopee SPX...")
        thread = threading.Thread(target=self._run_portal_sync, daemon=True)
        thread.start()

    def _run_portal_sync(self) -> None:
        try:
            drop_file, coll_file = self.syncer.sync_both_reports(
                headless=False, on_status=lambda msg: self.status_var.set(msg)
            )

            if drop_file:
                self.dropoff_path_var.set(str(drop_file))
            if coll_file:
                self.collection_path_var.set(str(coll_file))

            if drop_file or coll_file:
                self.status_var.set("Download concluído! Processando dados e salvando no SQLite...")
                self._execute_pipeline(str(drop_file) if drop_file else "", str(coll_file) if coll_file else "")
            else:
                self.status_var.set("Nenhum relatório foi baixado. Verifique a sessão do portal.")
        except PermissionError as p_err:
            self.after(0, self._show_error, str(p_err))
        except Exception as exc:
            self.after(0, self._show_error, f"Erro na sincronização: {exc}")

    def _start_processing_thread(self) -> None:
        drop_str = self.dropoff_path_var.get().strip()
        coll_str = self.collection_path_var.get().strip()

        if not drop_str and not coll_str:
            messagebox.showwarning("Atenção", "Por favor, selecione ao menos um arquivo para processar.")
            return

        self.btn_calculate.config(state="disabled")
        self.status_var.set("Processando planilhas e gravando no banco SQLite... Aguarde.")

        thread = threading.Thread(target=self._execute_pipeline, args=(drop_str, coll_str), daemon=True)
        thread.start()

    def _execute_pipeline(self, drop_path_str: str, coll_path_str: str) -> None:
        try:
            lead_calc = LeadTimeCalculator()
            rev_calc = RevenueCalculator()

            drop_lead_summary: Optional[LeadTimeSummary] = None
            df_drop_raw = None
            df_coll_raw = None
            d_tag_col = "Tag"
            d_in_col = ""
            d_out_col = ""

            # 1. Load Drop-off
            p_drop = Path(drop_path_str) if drop_path_str else None
            if p_drop and p_drop.exists():
                loader_drop = ExcelLoader(p_drop)
                df_drop_raw, _, d_tag_col, d_in_col, d_out_col = loader_drop.load_data()
                df_drop_lead, drop_lead_summary = lead_calc.process_lead_times(
                    df_drop_raw, d_in_col, d_out_col, is_collection=False
                )
            else:
                df_drop_lead = None

            # 2. Load Collection with resilient fallback
            p_coll = Path(coll_path_str) if coll_path_str else None
            if p_coll and p_coll.exists():
                try:
                    loader_coll = ExcelLoader(p_coll)
                    df_coll_raw, _, _, _, _ = loader_coll.load_data()
                except Exception:
                    import pandas as pd
                    if p_coll.suffix.lower() == ".csv":
                        df_coll_raw = ExcelLoader._load_csv_safely(p_coll)
                    else:
                        df_coll_raw = pd.read_excel(p_coll)
            else:
                df_coll_raw = None

            # 3. Consolidated Revenue (Pooled together)
            enr_drop, enr_coll, rev_summary = rev_calc.process_consolidated_revenue(
                df_dropoff=df_drop_lead if df_drop_lead is not None else df_drop_raw,
                tag_col=d_tag_col,
                df_collection=df_coll_raw,
            )

            # 4. Ingest into SQLite Database
            if enr_drop is not None and p_drop:
                self.repo.upsert_dropoff_dataframe(enr_drop, p_drop.name)
            if enr_coll is not None and p_coll:
                self.repo.upsert_collection_dataframe(enr_coll, p_coll.name)

            # 5. Save/Update in-place
            if p_drop and p_drop.exists() and enr_drop is not None and drop_lead_summary is not None:
                avg_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_business_time)
                med_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.median_business_time)
                min_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.min_business_time)
                max_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.max_business_time)
                raw_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_raw_24h_time)

                ops_dict = drop_lead_summary.to_metrics_dictionary(avg_b, med_b, min_b, max_b, raw_b)
                fin_dict = rev_summary.to_metrics_dictionary()

                if self.update_in_place_var.get():
                    self.last_dropoff_file = self.exporter.update_dropoff_in_place(
                        p_drop, enr_drop, ops_dict, fin_dict
                    )
                else:
                    self.last_dropoff_file = p_drop

            if p_coll and p_coll.exists() and enr_coll is not None:
                if self.update_in_place_var.get():
                    self.last_collection_file = self.exporter.update_collection_in_place(p_coll, enr_coll)
                else:
                    self.last_collection_file = p_coll

            self.after(0, self._on_pipeline_completed)

        except PermissionError as perm_err:
            self.after(0, self._show_error, str(perm_err))
        except Exception as exc:
            self.after(0, self._show_error, f"Erro no processamento: {str(exc)}")
        finally:
            self.after(0, lambda: self.btn_calculate.config(state="normal"))

    def _on_pipeline_completed(self) -> None:
        """Called on main thread when processing finishes."""
        self._load_current_month_data()
        self._refresh_history_months_dropdown()
        self.status_var.set("Processamento concluído com sucesso e dados do Mês Atual atualizados!")

        if self.last_dropoff_file and self.last_dropoff_file.exists():
            self.btn_open_dropoff.config(state="normal")
        if self.last_collection_file and self.last_collection_file.exists():
            self.btn_open_collection.config(state="normal")

        messagebox.showinfo(
            "Sucesso!",
            "Dados processados e integrados ao Mês Atual com êxito!\n"
            "O dashboard do mês atual e o histórico SQLite foram atualizados.",
        )

    def _show_error(self, msg: str) -> None:
        self.status_var.set(f"Erro: {msg}")
        messagebox.showerror("Erro de Execução", msg)

    @staticmethod
    def _open_file(path: Optional[Path]) -> None:
        if path and path.exists():
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Erro ao Abrir", str(e))


def run_gui() -> None:
    app = LeadTimeApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
