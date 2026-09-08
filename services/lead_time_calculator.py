"""
Module responsible for computing package operational lead times in agency business hours.
Integrates with BusinessCalendar to strictly account for open hours:
- Monday to Friday: 08:00 to 19:30
- Saturday: 09:00 to 15:00
- Sunday: Closed
"""

from datetime import timedelta
from typing import Tuple, Optional
import pandas as pd

from config import (
    COL_LEAD_TIME_BUSINESS_FORMATTED,
    COL_LEAD_TIME_BUSINESS_MINUTES,
    COL_LEAD_TIME_BUSINESS_HOURS,
    COL_LEAD_TIME_RAW_FORMATTED,
    COL_PROCESSING_STATUS,
    STATUS_COMPLETED,
    STATUS_COLLECTED,
    STATUS_PENDING,
    STATUS_INVALID_INBOUND,
    STATUS_NEGATIVE_DURATION,
)
from models import LeadTimeSummary
from services.business_calendar import BusinessCalendar


class LeadTimeCalculator:
    """
    Computes lead times per package in business operating hours and aggregate statistics.
    """

    @staticmethod
    def format_timedelta(td: Optional[timedelta]) -> str:
        """
        Converts a timedelta object to a human-readable string format.
        If duration is >= 24h, formats as 'Xd HH:MM:SS'. Otherwise 'HH:MM:SS'.

        :param td: The timedelta object to format (can be None or NaT).
        :return: Formatted string representing elapsed time.
        """
        if pd.isna(td) or td is None:
            return "N/A"

        total_seconds = int(td.total_seconds())
        is_negative = total_seconds < 0
        total_seconds = abs(total_seconds)

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        prefix = "-" if is_negative else ""
        if days > 0:
            return f"{prefix}{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{prefix}{hours:02d}:{minutes:02d}:{seconds:02d}"

    def process_lead_times(
        self, df: pd.DataFrame, inbound_col: str, outbound_col: str, is_collection: bool = False
    ) -> Tuple[pd.DataFrame, LeadTimeSummary]:
        """
        Processes the input DataFrame, parses timestamps, calculates business hours duration
        for each order, and computes aggregate metrics.

        :param df: The raw DataFrame containing package records.
        :param inbound_col: Column name containing the inbound timestamp.
        :param outbound_col: Column name containing the outbound timestamp.
        :param is_collection: True if processing buyer collection orders.
        :return: A tuple containing:
                 - enriched_df (pd.DataFrame): DataFrame with added lead time calculation columns.
                 - summary (LeadTimeSummary): Aggregate statistical metrics for the dataset.
        """
        enriched_df = df.copy()

        # Parse datetime values safely
        enriched_df["_inbound_parsed"] = pd.to_datetime(enriched_df[inbound_col], errors="coerce")
        enriched_df["_outbound_parsed"] = pd.to_datetime(enriched_df[outbound_col], errors="coerce")

        # 1. Continuous 24h raw duration
        enriched_df["_raw_duration"] = enriched_df["_outbound_parsed"] - enriched_df["_inbound_parsed"]
        enriched_df[COL_LEAD_TIME_RAW_FORMATTED] = enriched_df["_raw_duration"].apply(self.format_timedelta)

        # 2. Business hours duration (agency open hours only)
        business_seconds_list = []
        status_list = []

        completed_label = STATUS_COLLECTED if is_collection else STATUS_COMPLETED

        for _, row in enriched_df.iterrows():
            t_in = row["_inbound_parsed"]
            t_out = row["_outbound_parsed"]

            if pd.isna(t_in):
                status_list.append(STATUS_INVALID_INBOUND)
                business_seconds_list.append(None)
            elif pd.isna(t_out):
                status_list.append(STATUS_PENDING)
                business_seconds_list.append(None)
            elif t_out < t_in:
                status_list.append(STATUS_NEGATIVE_DURATION)
                business_seconds_list.append(None)
            else:
                status_list.append(completed_label)
                sec = BusinessCalendar.calculate_business_seconds(t_in, t_out)
                business_seconds_list.append(sec)

        enriched_df[COL_PROCESSING_STATUS] = status_list
        enriched_df["_business_seconds"] = business_seconds_list

        enriched_df[COL_LEAD_TIME_BUSINESS_MINUTES] = (
            enriched_df["_business_seconds"].apply(lambda s: round(s / 60.0, 2) if pd.notna(s) else None)
        )
        enriched_df[COL_LEAD_TIME_BUSINESS_HOURS] = (
            enriched_df["_business_seconds"].apply(lambda s: round(s / 3600.0, 2) if pd.notna(s) else None)
        )
        enriched_df[COL_LEAD_TIME_BUSINESS_FORMATTED] = (
            enriched_df["_business_seconds"].apply(
                lambda s: self.format_timedelta(timedelta(seconds=int(s))) if pd.notna(s) else "N/A"
            )
        )

        # Aggregate metrics
        valid_mask = enriched_df[COL_PROCESSING_STATUS] == completed_label
        valid_seconds = enriched_df.loc[valid_mask, "_business_seconds"].dropna()
        valid_raw_durations = enriched_df.loc[valid_mask, "_raw_duration"].dropna()

        total_packages = len(enriched_df)
        dispatched_packages = int(len(valid_seconds))
        pending_packages = int((enriched_df[COL_PROCESSING_STATUS] == STATUS_PENDING).sum())

        if dispatched_packages > 0:
            avg_sec = valid_seconds.mean()
            med_sec = valid_seconds.median()
            min_sec = valid_seconds.min()
            max_sec = valid_seconds.max()

            avg_business_time = timedelta(seconds=int(avg_sec))
            median_business_time = timedelta(seconds=int(med_sec))
            min_business_time = timedelta(seconds=int(min_sec))
            max_business_time = timedelta(seconds=int(max_sec))

            avg_business_minutes = avg_sec / 60.0
            avg_business_hours = avg_sec / 3600.0
            avg_raw_time = valid_raw_durations.mean()
        else:
            avg_business_time = None
            median_business_time = None
            min_business_time = None
            max_business_time = None
            avg_business_minutes = 0.0
            avg_business_hours = 0.0
            avg_raw_time = None

        summary = LeadTimeSummary(
            total_packages=total_packages,
            dispatched_packages=dispatched_packages,
            pending_packages=pending_packages,
            average_business_time=avg_business_time,
            median_business_time=median_business_time,
            min_business_time=min_business_time,
            max_business_time=max_business_time,
            average_business_minutes=avg_business_minutes,
            average_business_hours=avg_business_hours,
            average_raw_24h_time=avg_raw_time,
        )

        # Drop internal working columns
        enriched_df.drop(
            columns=["_inbound_parsed", "_outbound_parsed", "_raw_duration", "_business_seconds"],
            inplace=True,
        )

        return enriched_df, summary
