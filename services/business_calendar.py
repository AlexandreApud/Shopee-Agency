"""
Module responsible for calculating operational business hours for Shopee agency operations.
Filters out closed hours (overnight and Sundays) according to the agency's schedule:
- Monday to Friday: 08:00 to 19:30
- Saturday: 09:00 to 15:00
- Sunday: Closed
"""

from datetime import datetime, date, time, timedelta
from typing import Optional
import pandas as pd

from config import (
    WEEKDAY_OPEN_TIME,
    WEEKDAY_CLOSE_TIME,
    SATURDAY_OPEN_TIME,
    SATURDAY_CLOSE_TIME,
)


class BusinessCalendar:
    """
    Computes elapsed operational time strictly within agency open hours.
    """

    @staticmethod
    def get_open_window(target_date: date) -> Optional[tuple[datetime, datetime]]:
        """
        Returns the opening and closing datetimes for a specific calendar date.

        :param target_date: The date to check.
        :return: Tuple of (open_datetime, close_datetime) or None if closed.
        """
        weekday = target_date.weekday()  # 0=Monday ... 5=Saturday, 6=Sunday
        if weekday < 5:
            # Monday to Friday
            start_dt = datetime.combine(target_date, WEEKDAY_OPEN_TIME)
            end_dt = datetime.combine(target_date, WEEKDAY_CLOSE_TIME)
            return start_dt, end_dt
        if weekday == 5:
            # Saturday
            start_dt = datetime.combine(target_date, SATURDAY_OPEN_TIME)
            end_dt = datetime.combine(target_date, SATURDAY_CLOSE_TIME)
            return start_dt, end_dt
        # Sunday: Closed
        return None

    @classmethod
    def calculate_business_seconds(cls, start_dt: datetime, end_dt: datetime) -> int:
        """
        Calculates total operational seconds elapsed between start_dt and end_dt,
        only counting intervals when the agency is open.

        :param start_dt: Inbound / entry datetime.
        :param end_dt: Outbound / departure datetime.
        :return: Total business seconds elapsed.
        """
        if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
            return 0

        # Ensure pure datetime objects
        if hasattr(start_dt, "to_pydatetime"):
            start_dt = start_dt.to_pydatetime()
        if hasattr(end_dt, "to_pydatetime"):
            end_dt = end_dt.to_pydatetime()

        total_seconds = 0
        current_date = start_dt.date()
        final_date = end_dt.date()

        while current_date <= final_date:
            window = cls.get_open_window(current_date)
            if window is not None:
                window_open, window_close = window
                # Find overlap between [start_dt, end_dt] and [window_open, window_close]
                interval_start = max(start_dt, window_open)
                interval_end = min(end_dt, window_close)
                if interval_start < interval_end:
                    total_seconds += int((interval_end - interval_start).total_seconds())

            current_date += timedelta(days=1)

        return total_seconds

    @classmethod
    def calculate_business_duration(cls, start_dt: datetime, end_dt: datetime) -> Optional[timedelta]:
        """
        Returns timedelta of operational business duration.

        :param start_dt: Inbound / entry datetime.
        :param end_dt: Outbound / departure datetime.
        :return: Timedelta object representing business hours duration, or None if invalid.
        """
        if pd.isna(start_dt) or pd.isna(end_dt) or start_dt > end_dt:
            return None
        seconds = cls.calculate_business_seconds(start_dt, end_dt)
        return timedelta(seconds=seconds)
