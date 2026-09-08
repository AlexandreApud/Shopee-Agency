"""
Unit tests for BusinessCalendar service.
Verifies open windows, overnight exclusion, weekend handling, and user test case.
"""

import unittest
from datetime import datetime, timedelta

from services.business_calendar import BusinessCalendar


class TestBusinessCalendar(unittest.TestCase):
    """Test suite for operational business hours calculations."""

    def test_user_scenario_overnight_weekday(self):
        # Arrived Wednesday at 19:10, Truck arrived Thursday at 08:00
        # Expected: 20 minutes (19:10 to 19:30 closing), 0 minutes on Thursday before 08:00
        t_in = datetime(2026, 9, 2, 19, 10, 0)
        t_out = datetime(2026, 9, 3, 8, 0, 0)

        seconds = BusinessCalendar.calculate_business_seconds(t_in, t_out)
        self.assertEqual(seconds, 20 * 60)

        duration = BusinessCalendar.calculate_business_duration(t_in, t_out)
        self.assertEqual(duration, timedelta(minutes=20))

    def test_overnight_with_morning_minutes(self):
        # Arrived Wednesday at 19:10, Truck arrived Thursday at 08:15
        # Expected: 20 min (Wed) + 15 min (Thu) = 35 min
        t_in = datetime(2026, 9, 2, 19, 10, 0)
        t_out = datetime(2026, 9, 3, 8, 15, 0)

        seconds = BusinessCalendar.calculate_business_seconds(t_in, t_out)
        self.assertEqual(seconds, 35 * 60)

    def test_saturday_hours(self):
        # Saturday open is 09:00 to 15:00
        # Package from 10:00 to 12:00 on Saturday (2026-09-05)
        t_in = datetime(2026, 9, 5, 10, 0, 0)
        t_out = datetime(2026, 9, 5, 12, 0, 0)

        seconds = BusinessCalendar.calculate_business_seconds(t_in, t_out)
        self.assertEqual(seconds, 2 * 3600)

    def test_saturday_to_monday_spans_sunday(self):
        # Saturday: 14:30 (closes at 15:00 => 30 min)
        # Sunday: Closed (0 min)
        # Monday: 08:30 (opens at 08:00 => 30 min)
        # Total expected: 60 min (1 hour)
        t_in = datetime(2026, 9, 5, 14, 30, 0)
        t_out = datetime(2026, 9, 7, 8, 30, 0)

        seconds = BusinessCalendar.calculate_business_seconds(t_in, t_out)
        self.assertEqual(seconds, 60 * 60)

    def test_arrival_before_opening(self):
        # Arrives at 07:00 on weekday, collected at 08:30
        # Since agency opens at 08:00, elapsed business time is 30 min (08:00 to 08:30)
        t_in = datetime(2026, 9, 2, 7, 0, 0)
        t_out = datetime(2026, 9, 2, 8, 30, 0)

        seconds = BusinessCalendar.calculate_business_seconds(t_in, t_out)
        self.assertEqual(seconds, 30 * 60)


if __name__ == "__main__":
    unittest.main()
