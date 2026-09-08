"""
Module responsible for computing financial compensation and agency revenue metrics.
Devoluções (Return/Refund) are compensated at fixed R$ 0,80.
Postagens Comuns and Retiradas de Compradores (Collection) pool together in progressive volume tiers:
- 1 to 500: R$ 0,70
- 501 to 1000: R$ 0,60
- 1001 to 1500: R$ 0,50
- > 1500: R$ 0,50
"""

from typing import Tuple, Optional
import pandas as pd

from config import (
    RETURN_FEE,
    STANDARD_TIER_1_MAX,
    STANDARD_TIER_1_RATE,
    STANDARD_TIER_2_MAX,
    STANDARD_TIER_2_RATE,
    STANDARD_TIER_3_MAX,
    STANDARD_TIER_3_RATE,
    STANDARD_TIER_4_RATE,
    COL_PACKAGE_TYPE,
    COL_UNIT_REVENUE,
    COL_CUMULATIVE_REVENUE,
    PACKAGE_TYPE_RETURN,
    PACKAGE_TYPE_STANDARD,
    PACKAGE_TYPE_COLLECTION,
)
from models import RevenueSummary


class RevenueCalculator:
    """
    Computes revenue per package and consolidated agency earnings.
    """

    @staticmethod
    def is_return_package(tag_value: any) -> bool:
        """
        Determines whether a package tag denotes a return or refunded item.
        """
        if pd.isna(tag_value):
            return False
        cleaned = str(tag_value).strip().lower()
        return any(keyword in cleaned for keyword in ("return", "refund", "devolu"))

    @staticmethod
    def get_standard_tier_rate(sequential_index: int) -> float:
        """
        Returns the unit compensation rate for standard drop-offs and collections based on pooled sequential volume.
        """
        if sequential_index <= STANDARD_TIER_1_MAX:
            return STANDARD_TIER_1_RATE
        if sequential_index <= STANDARD_TIER_2_MAX:
            return STANDARD_TIER_2_RATE
        if sequential_index <= STANDARD_TIER_3_MAX:
            return STANDARD_TIER_3_RATE
        return STANDARD_TIER_4_RATE

    def process_consolidated_revenue(
        self,
        df_dropoff: Optional[pd.DataFrame],
        tag_col: str = "Tag",
        df_collection: Optional[pd.DataFrame] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], RevenueSummary]:
        """
        Calculates package type classification and unit fees for Drop-off and Collection datasets,
        pooling standard drop-offs and collections into the same progressive pricing tiers.

        :param df_dropoff: DataFrame of Drop-off orders (or None).
        :param tag_col: Name of the Tag column in Drop-off DataFrame.
        :param df_collection: DataFrame of Collection orders (or None).
        :return: Tuple of (enriched_dropoff_df, enriched_collection_df, RevenueSummary).
        """
        pooled_counter = 0
        return_count = 0
        standard_drop_count = 0
        collection_count = 0

        enriched_drop = df_dropoff.copy() if df_dropoff is not None else None
        enriched_coll = df_collection.copy() if df_collection is not None else None

        # 1. Process Drop-off
        if enriched_drop is not None:
            drop_types = []
            drop_fees = []

            for val in enriched_drop[tag_col]:
                if self.is_return_package(val):
                    return_count += 1
                    drop_types.append(PACKAGE_TYPE_RETURN)
                    drop_fees.append(RETURN_FEE)
                else:
                    pooled_counter += 1
                    standard_drop_count += 1
                    rate = self.get_standard_tier_rate(pooled_counter)
                    drop_types.append(PACKAGE_TYPE_STANDARD)
                    drop_fees.append(rate)

            enriched_drop[COL_PACKAGE_TYPE] = drop_types
            enriched_drop[COL_UNIT_REVENUE] = drop_fees
            enriched_drop[COL_CUMULATIVE_REVENUE] = (enriched_drop[COL_UNIT_REVENUE].cumsum()).round(2)

        # 2. Process Collection (pools sequentially with standard drop-offs)
        if enriched_coll is not None:
            coll_types = []
            coll_fees = []

            for _ in range(len(enriched_coll)):
                pooled_counter += 1
                collection_count += 1
                rate = self.get_standard_tier_rate(pooled_counter)
                coll_types.append(PACKAGE_TYPE_COLLECTION)
                coll_fees.append(rate)

            enriched_coll[COL_PACKAGE_TYPE] = coll_types
            enriched_coll[COL_UNIT_REVENUE] = coll_fees
            enriched_coll[COL_CUMULATIVE_REVENUE] = (enriched_coll[COL_UNIT_REVENUE].cumsum()).round(2)

        # 3. Calculate Tier Totals
        return_revenue = round(return_count * RETURN_FEE, 2)
        pooled_postagem_count = pooled_counter

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

        summary = RevenueSummary(
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
        )

        return enriched_drop, enriched_coll, summary
