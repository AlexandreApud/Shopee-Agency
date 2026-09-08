"""
Configuration module for Shopee Lead Time and Revenue calculation service.
Defines column mappings, pricing tiers, business hours schedule, localized labels, and paths.
"""

from datetime import time
from pathlib import Path
from typing import Optional

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Default watch directory for scanning input files (resolves to C:\Users\<user>\Downloads on any PC)
DEFAULT_WATCH_DIR = Path.home() / "Downloads"

# Default directory to save standalone output results if not updating in-place
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

# Directory for local database and persistent browser profile storage
DATA_DIR = BASE_DIR / "data"

# --- Operating Business Schedule (Agency Open Hours) ---
# Monday to Friday: 08:00 to 19:30
WEEKDAY_OPEN_TIME = time(8, 0, 0)
WEEKDAY_CLOSE_TIME = time(19, 30, 0)

# Saturday: 09:00 to 15:00
SATURDAY_OPEN_TIME = time(9, 0, 0)
SATURDAY_CLOSE_TIME = time(15, 0, 0)

# Sunday: Closed


def get_latest_dropoff_file() -> Optional[Path]:
    """Finds the most recent Shopee drop-off export (.xlsx or .csv) in Downloads."""
    if not DEFAULT_WATCH_DIR.exists():
        return None
    candidates = list(DEFAULT_WATCH_DIR.glob("*dropoff*.xlsx")) + list(DEFAULT_WATCH_DIR.glob("*dropoff*.csv"))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    return None


def get_latest_collection_file() -> Optional[Path]:
    """Finds the most recent Shopee collection (retirada) export (.csv or .xlsx) in Downloads."""
    if not DEFAULT_WATCH_DIR.exists():
        return None
    candidates = list(DEFAULT_WATCH_DIR.glob("*collection*.csv")) + list(DEFAULT_WATCH_DIR.glob("*collection*.xlsx"))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    return None


# Excel 0-based column indices for Drop-off reports
TRACKING_CODE_COL_INDEX = 0  # Column A: SPX Tracking
TAG_COL_INDEX = 1            # Column B: Tag (e.g. '-' or 'Return/Refund')
INBOUND_TIME_COL_INDEX = 8   # Column I: Inbound Date & Time
OUTBOUND_TIME_COL_INDEX = 9  # Column J: Outbound Date & Time
STATUS_COL_INDEX = 10        # Column K: Status

# Column indices for Collection reports (CSV format)
COLLECTION_INBOUND_COL_INDEX = 6   # Horário de Recebimento
COLLECTION_OUTBOUND_COL_INDEX = 7  # Horário de Envio
COLLECTION_STATUS_COL_INDEX = 9    # Status (Collected)

# --- Lead Time Columns (Portuguese) ---
COL_LEAD_TIME_BUSINESS_FORMATTED = "Lead Time Útil (HH:MM:SS)"
COL_LEAD_TIME_BUSINESS_MINUTES = "Lead Time Útil (Minutos)"
COL_LEAD_TIME_BUSINESS_HOURS = "Lead Time Útil (Horas)"
COL_LEAD_TIME_RAW_FORMATTED = "Tempo Bruto 24h (HH:MM:SS)"
COL_PROCESSING_STATUS = "Status do Lead Time"

# Status values in Portuguese
STATUS_COMPLETED = "Despachado"
STATUS_COLLECTED = "Retirado pelo Comprador"
STATUS_PENDING = "Pendente na Agência (Aguardando Coleta)"
STATUS_INVALID_INBOUND = "Horário de Entrada Inválido"
STATUS_NEGATIVE_DURATION = "Inválido (Saída antes da Entrada)"

# --- Revenue / Financial Pricing Rules ---
# Fixed fee per return/refund package
RETURN_FEE = 0.80  # R$ 0,80 per return

# Tiered fees for standard drop-offs AND buyer collections (they pool together)
STANDARD_TIER_1_MAX = 500
STANDARD_TIER_1_RATE = 0.70  # Packages 1 to 500: R$ 0,70

STANDARD_TIER_2_MAX = 1000
STANDARD_TIER_2_RATE = 0.60  # Packages 501 to 1000: R$ 0,60

STANDARD_TIER_3_MAX = 1500
STANDARD_TIER_3_RATE = 0.50  # Packages 1001 to 1500: R$ 0,50

STANDARD_TIER_4_RATE = 0.50  # Packages > 1500: R$ 0,50

# Financial columns appended to Excel/CSV data sheets
COL_PACKAGE_TYPE = "Tipo de Pacote"
COL_UNIT_REVENUE = "Remuneração Unitária (R$)"
COL_CUMULATIVE_REVENUE = "Remuneração Acumulada (R$)"

PACKAGE_TYPE_RETURN = "Devolução (Return/Refund)"
PACKAGE_TYPE_STANDARD = "Postagem Comum"
PACKAGE_TYPE_COLLECTION = "Retirada de Comprador (Collection)"

# Sheet names
SUMMARY_SHEET_NAME = "Resumo_Metricas"

# Localized metric labels for operational reporting (Drop-off only)
LABEL_TOTAL_PACKAGES_DROPOFF = "Total de Pacotes Drop-off"
LABEL_DISPATCHED_PACKAGES = "Pacotes Despachados (Coleta do Caminhão)"
LABEL_PENDING_PACKAGES = "Pacotes Pendentes na Agência"
LABEL_AVG_LEAD_TIME_HHMMSS = "Lead Time Útil Médio (HH:MM:SS)"
LABEL_AVG_LEAD_TIME_MINUTES = "Lead Time Útil Médio (Minutos)"
LABEL_AVG_LEAD_TIME_HOURS = "Lead Time Útil Médio (Horas)"
LABEL_MEDIAN_LEAD_TIME = "Mediana do Lead Time Útil (HH:MM:SS)"
LABEL_MIN_LEAD_TIME = "Menor Lead Time Útil (HH:MM:SS)"
LABEL_MAX_LEAD_TIME = "Maior Lead Time Útil (HH:MM:SS)"
LABEL_AVG_RAW_LEAD_TIME = "Média de Tempo Bruto (24h contínuas)"

# Localized metric labels for financial reporting
LABEL_TOTAL_VOLUME_MOVED = "Volume Total Movimentado (Drop-off + Retiradas)"
LABEL_RETURN_COUNT = "Qtd. Devoluções (Return/Refund)"
LABEL_RETURN_REVENUE = "Faturamento com Devoluções (R$ 0,80 fixo)"
LABEL_POOLED_POSTAGEM_COUNT = "Total Postagens + Retiradas (Nas Faixas)"
LABEL_STANDARD_DROP_COUNT = "  • Postagens Comuns (Vendedores)"
LABEL_COLLECTION_COUNT = "  • Retiradas de Compradores (PUDO)"
LABEL_TIER1_COUNT = "Faixa 1 (1 a 500 unid.)"
LABEL_TIER1_REVENUE = "Faturamento Faixa 1 (R$ 0,70/unid)"
LABEL_TIER2_COUNT = "Faixa 2 (501 a 1000 unid.)"
LABEL_TIER2_REVENUE = "Faturamento Faixa 2 (R$ 0,60/unid)"
LABEL_TIER3_COUNT = "Faixa 3 (1001 a 1500 unid.)"
LABEL_TIER3_REVENUE = "Faturamento Faixa 3 (R$ 0,50/unid)"
LABEL_TIER4_COUNT = "Faixa 4 (> 1500 unid.)"
LABEL_TIER4_REVENUE = "Faturamento Faixa 4 (R$ 0,50/unid)"
LABEL_POOLED_POSTAGEM_REVENUE = "Faturamento Total (Postagens + Retiradas)"
LABEL_TOTAL_REVENUE = "FATURAMENTO TOTAL ESTIMADO (R$)"
LABEL_AVG_TICKET = "Ticket Médio por Pacote (R$)"
