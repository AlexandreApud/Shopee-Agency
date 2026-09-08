"""
Domain models for Shopee Drop-off Lead Time and Revenue processing.
Encapsulates operational (Drop-off Lead Time) and pooled financial metrics.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Dict, Any

from config import (
    LABEL_TOTAL_PACKAGES_DROPOFF,
    LABEL_DISPATCHED_PACKAGES,
    LABEL_PENDING_PACKAGES,
    LABEL_AVG_LEAD_TIME_HHMMSS,
    LABEL_AVG_LEAD_TIME_MINUTES,
    LABEL_AVG_LEAD_TIME_HOURS,
    LABEL_MEDIAN_LEAD_TIME,
    LABEL_MIN_LEAD_TIME,
    LABEL_MAX_LEAD_TIME,
    LABEL_AVG_RAW_LEAD_TIME,
    LABEL_TOTAL_VOLUME_MOVED,
    LABEL_RETURN_COUNT,
    LABEL_RETURN_REVENUE,
    LABEL_POOLED_POSTAGEM_COUNT,
    LABEL_STANDARD_DROP_COUNT,
    LABEL_COLLECTION_COUNT,
    LABEL_TIER1_COUNT,
    LABEL_TIER1_REVENUE,
    LABEL_TIER2_COUNT,
    LABEL_TIER2_REVENUE,
    LABEL_TIER3_COUNT,
    LABEL_TIER3_REVENUE,
    LABEL_TIER4_COUNT,
    LABEL_TIER4_REVENUE,
    LABEL_POOLED_POSTAGEM_REVENUE,
    LABEL_TOTAL_REVENUE,
    LABEL_AVG_TICKET,
)


@dataclass(frozen=True)
class LeadTimeSummary:
    """
    Data transfer object representing operational dwell-time metrics for Drop-off packages.
    Lead time is NOT calculated for buyer collection orders.
    """
    total_packages: int
    dispatched_packages: int
    pending_packages: int
    average_business_time: Optional[timedelta]
    median_business_time: Optional[timedelta]
    min_business_time: Optional[timedelta]
    max_business_time: Optional[timedelta]
    average_business_minutes: float
    average_business_hours: float
    average_raw_24h_time: Optional[timedelta]

    def to_metrics_dictionary(
        self,
        formatted_avg: str,
        formatted_med: str,
        formatted_min: str,
        formatted_max: str,
        formatted_raw: str,
    ) -> Dict[str, Any]:
        """Returns ordered operational metrics in Portuguese."""
        return {
            LABEL_TOTAL_PACKAGES_DROPOFF: self.total_packages,
            LABEL_DISPATCHED_PACKAGES: self.dispatched_packages,
            LABEL_PENDING_PACKAGES: self.pending_packages,
            LABEL_AVG_LEAD_TIME_HHMMSS: formatted_avg,
            LABEL_AVG_LEAD_TIME_MINUTES: round(self.average_business_minutes, 2),
            LABEL_AVG_LEAD_TIME_HOURS: round(self.average_business_hours, 2),
            LABEL_MEDIAN_LEAD_TIME: formatted_med,
            LABEL_MIN_LEAD_TIME: formatted_min,
            LABEL_MAX_LEAD_TIME: formatted_max,
            LABEL_AVG_RAW_LEAD_TIME: formatted_raw,
        }


@dataclass(frozen=True)
class RevenueSummary:
    """
    Data transfer object representing pooled financial revenue metrics.
    Postagens (Vendedores) and Retiradas (Compradores) share the same tiered pricing brackets.
    Devoluções (Return/Refund) receive a fixed R$ 0,80 fee.
    """
    total_packages_moved: int
    return_count: int
    return_revenue: float
    standard_drop_count: int
    collection_count: int
    pooled_postagem_count: int
    tier1_count: int
    tier1_revenue: float
    tier2_count: int
    tier2_revenue: float
    tier3_count: int
    tier3_revenue: float
    tier4_count: int
    tier4_revenue: float
    pooled_postagem_revenue: float
    total_revenue: float
    average_ticket: float
    dispatched_drop_count: int = 0
    pending_drop_count: int = 0
    collected_count: int = 0
    pending_collection_count: int = 0
    total_dispatched_count: int = 0
    total_pending_count: int = 0
    inbound_drop_count: int = 0
    inbound_collection_count: int = 0
    inbound_total_count: int = 0

    def to_metrics_dictionary(self) -> Dict[str, Any]:
        """Returns ordered financial metrics in Portuguese formatted for currency."""
        metrics = {
            LABEL_TOTAL_VOLUME_MOVED: self.total_packages_moved,
            LABEL_RETURN_COUNT: self.return_count,
            LABEL_RETURN_REVENUE: f"R$ {self.return_revenue:.2f}",
            LABEL_POOLED_POSTAGEM_COUNT: self.pooled_postagem_count,
            LABEL_STANDARD_DROP_COUNT: self.standard_drop_count,
            LABEL_COLLECTION_COUNT: self.collection_count,
            LABEL_TIER1_COUNT: f"{self.tier1_count} unid.",
            LABEL_TIER1_REVENUE: f"R$ {self.tier1_revenue:.2f}",
        }
        if self.tier2_count > 0:
            metrics[LABEL_TIER2_COUNT] = f"{self.tier2_count} unid."
            metrics[LABEL_TIER2_REVENUE] = f"R$ {self.tier2_revenue:.2f}"
        if self.tier3_count > 0:
            metrics[LABEL_TIER3_COUNT] = f"{self.tier3_count} unid."
            metrics[LABEL_TIER3_REVENUE] = f"R$ {self.tier3_revenue:.2f}"
        if self.tier4_count > 0:
            metrics[LABEL_TIER4_COUNT] = f"{self.tier4_count} unid."
            metrics[LABEL_TIER4_REVENUE] = f"R$ {self.tier4_revenue:.2f}"

        metrics[LABEL_POOLED_POSTAGEM_REVENUE] = f"R$ {self.pooled_postagem_revenue:.2f}"
        metrics[LABEL_TOTAL_REVENUE] = f"R$ {self.total_revenue:.2f}"
        metrics[LABEL_AVG_TICKET] = f"R$ {self.average_ticket:.2f}"
        return metrics
