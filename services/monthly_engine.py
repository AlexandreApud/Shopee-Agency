"""
Monthly aggregation engine for computing historical performance from SQLite.
Consolidates all packages in a given billing month, applying monthly progressive volume tiers
and computing aggregate business hours Lead Time for Drop-off.
"""

from datetime import timedelta
from typing import Dict, Any, Optional
import pandas as pd

from database.repository import PackageRepository
from config import (
    RETURN_FEE,
    STANDARD_TIER_1_MAX,
    STANDARD_TIER_1_RATE,
    STANDARD_TIER_2_MAX,
    STANDARD_TIER_2_RATE,
    STANDARD_TIER_3_MAX,
    STANDARD_TIER_3_RATE,
    STANDARD_TIER_4_RATE,
    PACKAGE_TYPE_RETURN,
)
from models import LeadTimeSummary, RevenueSummary
from services.lead_time_calculator import LeadTimeCalculator


class MonthlyEngine:
    """
    Computes monthly historical revenue and lead time metrics from the SQLite database.
    """

    def __init__(self, repository: Optional[PackageRepository] = None):
        self.repository = repository or PackageRepository()

    def get_available_months(self) -> list[str]:
        """Returns sorted list of distinct reference billing months (e.g. ['2026-09', '2026-08'])."""
        return self.repository.get_available_months()

    def compute_month_summary(
        self, reference_month: str
    ) -> tuple[Optional[LeadTimeSummary], RevenueSummary, pd.DataFrame, pd.DataFrame]:
        """
        Computes the complete consolidated operational and financial summary for a given month.

        :param reference_month: Month string in 'YYYY-MM' format.
        :return: Tuple of (LeadTimeSummary, RevenueSummary, dropoff_df, collection_df).
        """
        df_drop = self.repository.get_month_dropoff_orders(reference_month)
        df_coll = self.repository.get_month_collection_orders(reference_month)

        # 1. Financial Revenue: Pool standard drop-off and collection into progressive tiers
        return_count = 0
        standard_drop_count = 0
        collection_count = len(df_coll)

        if not df_drop.empty:
            is_return = df_drop["package_type"] == PACKAGE_TYPE_RETURN
            return_count = int(is_return.sum())
            standard_drop_count = int((~is_return).sum())

        pooled_postagem_count = standard_drop_count + collection_count

        return_revenue = round(return_count * RETURN_FEE, 2)

        tier1_count = min(pooled_postagem_count, STANDARD_TIER_1_MAX)
        tier1_revenue = round(tier1_count * STANDARD_TIER_1_RATE, 2)

        tier2_count = max(0, min(pooled_postagem_count - STANDARD_TIER_1_MAX, STANDARD_TIER_2_MAX - STANDARD_TIER_1_MAX))
        tier2_revenue = round(tier2_count * STANDARD_TIER_2_RATE, 2)

        tier3_count = max(0, min(pooled_postagem_count - STANDARD_TIER_2_MAX, STANDARD_TIER_3_MAX - STANDARD_TIER_2_MAX))
        tier3_revenue = round(tier3_count * STANDARD_TIER_3_RATE, 2)

        tier4_count = max(0, pooled_postagem_count - STANDARD_TIER_3_MAX)
        tier4_revenue = round(tier4_count * STANDARD_TIER_4_RATE, 2)

        pooled_postagem_revenue = round(tier1_revenue + tier2_revenue + tier3_revenue + tier4_revenue, 2)
        total_revenue = round(return_revenue + pooled_postagem_revenue, 2)
        total_packages_moved = return_count + pooled_postagem_count
        average_ticket = round(total_revenue / total_packages_moved, 2) if total_packages_moved > 0 else 0.0

        # Detailed status breakdown for operational transparency
        dispatched_drop_count = 0
        pending_drop_count = 0
        if not df_drop.empty:
            is_dispatched = df_drop["outbound_time"].notna() & (df_drop["outbound_time"].astype(str).str.strip() != "") & (df_drop["outbound_time"].astype(str) != "nan")
            dispatched_drop_count = int(is_dispatched.sum())
            pending_drop_count = int((~is_dispatched).sum())

        collected_count = 0
        pending_collection_count = 0
        if not df_coll.empty:
            is_collected = df_coll["status"] == "Collected"
            collected_count = int(is_collected.sum())
            pending_collection_count = int((~is_collected).sum())

        total_dispatched_count = dispatched_drop_count + collected_count
        total_pending_count = pending_drop_count + pending_collection_count

        rev_summary = RevenueSummary(
            total_packages_moved=total_packages_moved,
            return_count=return_count,
            return_revenue=return_revenue,
            standard_drop_count=standard_drop_count,
            collection_count=collection_count,
            pooled_postagem_count=pooled_postagem_count,
            tier1_count=tier1_count,
            tier1_revenue=tier1_revenue,
            tier2_count=tier2_count,
            tier2_revenue=tier2_revenue,
            tier3_count=tier3_count,
            tier3_revenue=tier3_revenue,
            tier4_count=tier4_count,
            tier4_revenue=tier4_revenue,
            pooled_postagem_revenue=pooled_postagem_revenue,
            total_revenue=total_revenue,
            average_ticket=average_ticket,
            dispatched_drop_count=dispatched_drop_count,
            pending_drop_count=pending_drop_count,
            collected_count=collected_count,
            pending_collection_count=pending_collection_count,
            total_dispatched_count=total_dispatched_count,
            total_pending_count=total_pending_count,
        )

        # 2. Operational Lead Time: Strictly for Drop-off
        lead_summary = None
        if not df_drop.empty:
            valid_durations = df_drop["business_seconds"].dropna()
            total_pkgs = len(df_drop)
            dispatched_pkgs = int(len(valid_durations))
            pending_pkgs = int((df_drop["status"] == "DOP_Received").sum())

            if dispatched_pkgs > 0:
                avg_sec = valid_durations.mean()
                med_sec = valid_durations.median()
                min_sec = valid_durations.min()
                max_sec = valid_durations.max()

                lead_summary = LeadTimeSummary(
                    total_packages=total_pkgs,
                    dispatched_packages=dispatched_pkgs,
                    pending_packages=pending_pkgs,
                    average_business_time=timedelta(seconds=int(avg_sec)),
                    median_business_time=timedelta(seconds=int(med_sec)),
                    min_business_time=timedelta(seconds=int(min_sec)),
                    max_business_time=timedelta(seconds=int(max_sec)),
                    average_business_minutes=avg_sec / 60.0,
                    average_business_hours=avg_sec / 3600.0,
                    average_raw_24h_time=None,
                )

        return lead_summary, rev_summary, df_drop, df_coll
