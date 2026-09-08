"""
Main application entry point for calculating Shopee Lead Time and Revenue.
- Features automated synchronization with Shopee SPX portal (https://sp.spx.shopee.com.br/) via Playwright.
- Computes Lead Time in business hours strictly for Drop-off.
- Pools Postagens and Retiradas together into progressive monthly tiers.
- Persists all records into local SQLite database for historical month-by-month analysis.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from config import DEFAULT_OUTPUT_DIR
from services import (
    ExcelLoader,
    LeadTimeCalculator,
    RevenueCalculator,
    ExcelExporter,
    FileClassifier,
    FILE_TYPE_COLLECTION,
    PortalSyncer,
)
from services.monthly_engine import MonthlyEngine
from database.repository import PackageRepository
from ui.app_window import run_gui


def display_monthly_report_from_db(month: str) -> None:
    """
    Fetches and displays the consolidated operational and financial report for a specific month from SQLite.
    """
    repo = PackageRepository()
    engine = MonthlyEngine(repo)
    lead_s, rev_s, d_df, c_df = engine.compute_month_summary(month)

    print("=" * 80)
    print(f"       RELATÓRIO HISTÓRICO CONSOLIDADO (SQLITE) - MÊS: {month}       ")
    print("=" * 80)
    print(f"VOLUME TOTAL MOVIMENTADO       : {rev_s.total_packages_moved} pacotes")
    print(f"  • Postagens de Vendedores    : {rev_s.standard_drop_count} un")
    print(f"  • Retiradas de Compradores   : {rev_s.collection_count} un")
    print(f"  • Devoluções                 : {rev_s.return_count} un")
    print("-" * 80)
    print(f"FATURAMENTO TOTAL DO MÊS       : R$ {rev_s.total_revenue:.2f}")
    print(f"Ticket Médio por Pacote        : R$ {rev_s.average_ticket:.2f}")
    print(f"• Devoluções (R$ 0,80 fixo)    : {rev_s.return_count} un -> R$ {rev_s.return_revenue:.2f}")
    print(f"• Postagens + Retiradas (Pool) : {rev_s.pooled_postagem_count} un -> R$ {rev_s.pooled_postagem_revenue:.2f}")
    if rev_s.tier1_count > 0:
        print(f"    - Faixa 1 (1 a 500 unid.)  : {rev_s.tier1_count} un x R$ 0,70 = R$ {rev_s.tier1_revenue:.2f}")
    if rev_s.tier2_count > 0:
        print(f"    - Faixa 2 (501 a 1000 unid): {rev_s.tier2_count} un x R$ 0,60 = R$ {rev_s.tier2_revenue:.2f}")

    print("-" * 80)
    if lead_s and lead_s.dispatched_packages > 0:
        avg_drop = LeadTimeCalculator.format_timedelta(lead_s.average_business_time)
        print(f"• Lead Time Médio Útil (Drop-off): {avg_drop} ({lead_s.average_business_minutes:.1f} min)")
        print(f"  Pacotes Coletados pelo Caminhão: {lead_s.dispatched_packages} de {lead_s.total_packages}")
        print(f"  Pacotes Pendentes na Agência   : {lead_s.pending_packages}")
    print("=" * 80 + "\n")


def run_pipeline(
    dropoff_file: Optional[Path],
    collection_file: Optional[Path],
    output_dir: Path,
    update_in_place: bool = True,
) -> None:
    """
    Executes the consolidated processing pipeline and persists records to SQLite.
    """
    print("=" * 80)
    print("      SHOPEE AGENCY PRO: LEAD TIME ÚTIL & GESTÃO FINANCEIRA CONSOLIDADA      ")
    print("=" * 80)
    print("Horário de Funcionamento: Seg a Sex 08:00 às 19:30 | Sáb 09:00 às 15:00 | Dom Fechado\n")

    lead_calc = LeadTimeCalculator()
    rev_calc = RevenueCalculator()
    exporter = ExcelExporter(output_dir)
    repo = PackageRepository()

    drop_lead_summary = None
    df_drop_raw = None
    df_coll_raw = None
    d_tag_col = "Tag"
    d_in_col = ""
    d_out_col = ""

    # 1. Load Drop-off
    if dropoff_file and dropoff_file.exists():
        print(f"[+] Carregando Drop-off (Postagens & Devoluções): {dropoff_file.name}")
        loader_drop = ExcelLoader(dropoff_file)
        df_drop_raw, _, d_tag_col, d_in_col, d_out_col = loader_drop.load_data()
        df_drop_lead, drop_lead_summary = lead_calc.process_lead_times(
            df_drop_raw, d_in_col, d_out_col, is_collection=False
        )
    else:
        df_drop_lead = None

    # 2. Load Collection
    if collection_file and collection_file.exists():
        print(f"[+] Carregando Retiradas de Compradores (Collection): {collection_file.name}")
        loader_coll = ExcelLoader(collection_file)
        df_coll_raw, _, _, _, _ = loader_coll.load_data()

    # 3. Compute Consolidated Revenue (Postagens + Retiradas pooled together)
    enr_drop, enr_coll, rev_summary = rev_calc.process_consolidated_revenue(
        df_dropoff=df_drop_lead if df_drop_lead is not None else df_drop_raw,
        tag_col=d_tag_col,
        df_collection=df_coll_raw,
    )

    # 4. Ingest into SQLite Database (Deduplicated on tracking code)
    if enr_drop is not None and dropoff_file:
        d_saved = repo.upsert_dropoff_dataframe(enr_drop, dropoff_file.name)
        print(f"[+] Gravados/atualizados {d_saved} registros de Drop-off no SQLite.")
    if enr_coll is not None and collection_file:
        c_saved = repo.upsert_collection_dataframe(enr_coll, collection_file.name)
        print(f"[+] Gravados/atualizados {c_saved} registros de Retiradas no SQLite.")

    # 5. Save/Update in-place
    if dropoff_file and dropoff_file.exists() and enr_drop is not None and drop_lead_summary is not None:
        avg_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_business_time)
        med_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.median_business_time)
        min_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.min_business_time)
        max_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.max_business_time)
        raw_b = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_raw_24h_time)

        ops_dict = drop_lead_summary.to_metrics_dictionary(avg_b, med_b, min_b, max_b, raw_b)
        fin_dict = rev_summary.to_metrics_dictionary()

        if update_in_place:
            saved_drop = exporter.update_dropoff_in_place(dropoff_file, enr_drop, ops_dict, fin_dict)
            print(f"[+] Planilha Drop-off atualizada com sucesso: {saved_drop}")

    if collection_file and collection_file.exists() and enr_coll is not None:
        if update_in_place:
            saved_coll = exporter.update_collection_in_place(collection_file, enr_coll)
            print(f"[+] Planilha Retiradas atualizada com sucesso: {saved_coll}")

    # 6. Display Summary
    print("\n" + "-" * 80)
    print("                    ESTIMATIVA FINANCEIRA CONSOLIDADA (GANHOS)               ")
    print("-" * 80)
    print(f"VOLUME TOTAL MOVIMENTADO       : {rev_summary.total_packages_moved} pacotes")
    print(f"FATURAMENTO TOTAL ESTIMADO     : R$ {rev_summary.total_revenue:.2f}")
    print(f"Ticket Médio por Pacote        : R$ {rev_summary.average_ticket:.2f}")
    print(f"• Devoluções (R$ 0,80 fixo)    : {rev_summary.return_count} un -> R$ {rev_summary.return_revenue:.2f}")
    print(f"• Postagens + Retiradas Juntas : {rev_summary.pooled_postagem_count} un -> R$ {rev_summary.pooled_postagem_revenue:.2f}")
    print(f"    - Postagens de Vendedores  : {rev_summary.standard_drop_count} un")
    print(f"    - Retiradas de Compradores : {rev_summary.collection_count} un")
    if rev_summary.tier1_count > 0:
        print(f"    - Faixa 1 (1 a 500 unid.)  : {rev_summary.tier1_count} un x R$ 0,70 = R$ {rev_summary.tier1_revenue:.2f}")

    print("\n" + "-" * 80)
    print("         RESUMO OPERACIONAL: LEAD TIME ÚTIL (DROP-OFF ATÉ O CAMINHÃO)         ")
    print("-" * 80)
    if drop_lead_summary and drop_lead_summary.dispatched_packages > 0:
        avg_drop = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_business_time)
        raw_drop = LeadTimeCalculator.format_timedelta(drop_lead_summary.average_raw_24h_time)
        print(f"• Lead Time Médio Útil (Drop-off): {avg_drop} ({drop_lead_summary.average_business_minutes:.1f} min)")
        print(f"  (Comparação com 24h contínuas  : {raw_drop})")
        print(f"  Pacotes Coletados pelo Caminhão: {drop_lead_summary.dispatched_packages} de {drop_lead_summary.total_packages}")
        print(f"  Pacotes Pendentes na Agência   : {drop_lead_summary.pending_packages}")
    print("=" * 80 + "\n")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula Lead Time útil de Drop-off e estimativa financeira consolidada."
    )
    parser.add_argument("-d", "--dropoff", type=Path, default=None, help="Caminho para arquivo de Drop-off.")
    parser.add_argument("-c", "--collection", type=Path, default=None, help="Caminho para arquivo de Retiradas.")
    parser.add_argument("-i", "--input", type=Path, default=None, help="Arquivo único para auto-classificação.")
    parser.add_argument("-m", "--month", type=str, default=None, help="Consulta relatório histórico do mês no SQLite (ex: 2026-09).")
    parser.add_argument("--sync", action="store_true", help="Dispara download automático dos relatórios no portal Shopee SPX.")
    parser.add_argument("--login", action="store_true", help="Abre navegador interativo para conectar a conta Google no portal SPX.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Diretório de saída.")
    parser.add_argument("--no-in-place", action="store_true", help="Não altera as planilhas de entrada.")
    parser.add_argument("--gui", action="store_true", help="Força a inicialização da tela gráfica.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    if args.login:
        syncer = PortalSyncer()
        print("[+] Abrindo navegador Chrome para login no portal Shopee SPX...")
        syncer.open_browser_for_login(lambda m: print(f"    {m}"))
    elif args.sync:
        syncer = PortalSyncer()
        print("[+] Sincronizando relatórios com o portal Shopee SPX...")
        drop_f, coll_f = syncer.sync_both_reports(headless=False, on_status=lambda m: print(f"    {m}"))
        if drop_f or coll_f:
            run_pipeline(drop_f, coll_f, args.output, not args.no_in_place)
        else:
            print("[!] Nenhum arquivo baixado. Verifique se o login foi realizado com --login.")
    elif args.month:
        display_monthly_report_from_db(args.month)
    elif args.gui or (args.input is None and args.dropoff is None and args.collection is None):
        run_gui()
    else:
        drop_file = args.dropoff
        coll_file = args.collection

        if args.input:
            ctype = FileClassifier.classify_file(args.input)
            if ctype == FILE_TYPE_COLLECTION:
                coll_file = args.input
            else:
                drop_file = args.input

        try:
            run_pipeline(
                dropoff_file=drop_file,
                collection_file=coll_file,
                output_dir=args.output,
                update_in_place=not args.no_in_place,
            )
        except Exception as exc:
            print(f"[!] Erro no processamento: {exc}", file=sys.stderr)
            sys.exit(1)
