"""
Repository module for SQLite persistence of Drop-off and Collection orders.
Handles upserting (deduplication on tracking code) and multi-month historical queries.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from database.connection import get_db_connection
from config import (
    COL_PACKAGE_TYPE,
    COL_UNIT_REVENUE,
    COL_LEAD_TIME_BUSINESS_FORMATTED,
    COL_PROCESSING_STATUS,
)


class PackageRepository:
    """
    Data access object for managing package records in SQLite.
    """

    @staticmethod
    def _extract_reference_month(inbound_str: Optional[str], outbound_str: Optional[str]) -> str:
        """
        Determines the reference billing month (YYYY-MM).
        Prioritizes outbound timestamp (month of shipment/collection), falling back to inbound.
        """
        target = outbound_str if (outbound_str and str(outbound_str).strip() and str(outbound_str) != "nan") else inbound_str
        if target and str(target).strip() and str(target) != "nan":
            try:
                dt = pd.to_datetime(target)
                return dt.strftime("%Y-%m")
            except Exception:
                pass
        return datetime.now().strftime("%Y-%m")

    def upsert_dropoff_dataframe(self, df: pd.DataFrame, source_filename: str) -> int:
        """
        Saves or updates drop-off records from an enriched DataFrame.
        Deduplicates on tracking code, updating outbound timestamps and status if already present.

        :param df: Enriched DataFrame with Lead Time and Revenue columns.
        :param source_filename: Name of the origin file.
        :return: Number of records processed.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        tracking_col = df.columns[0]
        tag_col = df.columns[1]
        inbound_col = df.columns[8]
        outbound_col = df.columns[9]
        status_col = df.columns[10]

        records_count = 0
        for _, row in df.iterrows():
            tracking_code = str(row[tracking_col]).strip()
            if not tracking_code or tracking_code == "nan":
                continue

            tag_val = str(row[tag_col]) if pd.notna(row[tag_col]) else ""
            inbound_val = str(row[inbound_col]) if pd.notna(row[inbound_col]) else None
            outbound_val = str(row[outbound_col]) if pd.notna(row[outbound_col]) else None
            status_val = str(row[status_col]) if pd.notna(row[status_col]) else ""

            pkg_type = str(row.get(COL_PACKAGE_TYPE, "Postagem Comum"))
            unit_fee = float(row.get(COL_UNIT_REVENUE, 0.70)) if pd.notna(row.get(COL_UNIT_REVENUE)) else 0.70
            bus_fmt = str(row.get(COL_LEAD_TIME_BUSINESS_FORMATTED, "N/A"))

            # Calculate business seconds if available
            bus_seconds = None
            if pd.notna(row.get("Lead Time Útil (Minutos)")):
                bus_seconds = int(float(row["Lead Time Útil (Minutos)"]) * 60)

            ref_month = self._extract_reference_month(inbound_val, outbound_val)

            cursor.execute(
                """
                INSERT INTO dropoff_orders (
                    tracking_code, tag, package_type, inbound_time, outbound_time,
                    status, business_seconds, business_formatted, unit_fee,
                    reference_month, source_file, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tracking_code) DO UPDATE SET
                    tag = excluded.tag,
                    package_type = excluded.package_type,
                    inbound_time = COALESCE(excluded.inbound_time, dropoff_orders.inbound_time),
                    outbound_time = COALESCE(excluded.outbound_time, dropoff_orders.outbound_time),
                    status = excluded.status,
                    business_seconds = COALESCE(excluded.business_seconds, dropoff_orders.business_seconds),
                    business_formatted = COALESCE(excluded.business_formatted, dropoff_orders.business_formatted),
                    unit_fee = excluded.unit_fee,
                    reference_month = excluded.reference_month,
                    source_file = excluded.source_file,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (
                    tracking_code,
                    tag_val,
                    pkg_type,
                    inbound_val,
                    outbound_val,
                    status_val,
                    bus_seconds,
                    bus_fmt,
                    unit_fee,
                    ref_month,
                    source_filename,
                ),
            )
            records_count += 1

        conn.commit()
        conn.close()
        return records_count

    def upsert_collection_dataframe(self, df: pd.DataFrame, source_filename: str) -> int:
        """
        Saves or updates buyer collection records from an enriched DataFrame.
        Deduplicates on tracking code.

        :param df: Enriched Collection DataFrame.
        :param source_filename: Name of the origin file.
        :return: Number of records processed.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        tracking_col = df.columns[0]
        inbound_col = df.columns[6]
        outbound_col = df.columns[7]
        status_col = df.columns[9]

        records_count = 0
        for _, row in df.iterrows():
            tracking_code = str(row[tracking_col]).strip()
            if not tracking_code or tracking_code == "nan":
                continue

            inbound_val = str(row[inbound_col]) if pd.notna(row[inbound_col]) else None
            outbound_val = str(row[outbound_col]) if pd.notna(row[outbound_col]) else None
            status_val = str(row[status_col]) if pd.notna(row[status_col]) else ""

            pkg_type = str(row.get(COL_PACKAGE_TYPE, "Retirada de Comprador (Collection)"))
            unit_fee = float(row.get(COL_UNIT_REVENUE, 0.70)) if pd.notna(row.get(COL_UNIT_REVENUE)) else 0.70
            ref_month = self._extract_reference_month(inbound_val, outbound_val)

            cursor.execute(
                """
                INSERT INTO collection_orders (
                    tracking_code, package_type, inbound_time, outbound_time,
                    status, unit_fee, reference_month, source_file, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tracking_code) DO UPDATE SET
                    inbound_time = COALESCE(excluded.inbound_time, collection_orders.inbound_time),
                    outbound_time = COALESCE(excluded.outbound_time, collection_orders.outbound_time),
                    status = excluded.status,
                    package_type = excluded.package_type,
                    unit_fee = excluded.unit_fee,
                    reference_month = excluded.reference_month,
                    source_file = excluded.source_file,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (
                    tracking_code,
                    pkg_type,
                    inbound_val,
                    outbound_val,
                    status_val,
                    unit_fee,
                    ref_month,
                    source_filename,
                ),
            )
            records_count += 1

        conn.commit()
        conn.close()
        return records_count

    def get_available_months(self) -> List[str]:
        """
        Returns a sorted list of unique reference billing months (e.g. ['2026-09', '2026-08']).
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT reference_month FROM (
                SELECT reference_month FROM dropoff_orders WHERE reference_month IS NOT NULL
                UNION
                SELECT reference_month FROM collection_orders WHERE reference_month IS NOT NULL
            ) ORDER BY reference_month DESC;
            """
        )
        months = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return months

    def get_month_dropoff_orders(self, reference_month: str) -> pd.DataFrame:
        """
        Returns a DataFrame of all drop-off orders for a specific reference month.
        """
        conn = get_db_connection()
        query = "SELECT * FROM dropoff_orders WHERE reference_month = ? ORDER BY inbound_time ASC;"
        df = pd.read_sql_query(query, conn, params=(reference_month,))
        conn.close()
        return df

    def get_month_collection_orders(self, reference_month: str) -> pd.DataFrame:
        """
        Returns a DataFrame of all collection orders for a specific reference month.
        """
        conn = get_db_connection()
        query = "SELECT * FROM collection_orders WHERE reference_month = ? ORDER BY inbound_time ASC;"
        df = pd.read_sql_query(query, conn, params=(reference_month,))
        conn.close()
        return df

    def get_total_records_count(self) -> Dict[str, int]:
        """
        Returns global counts of stored drop-off and collection packages.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dropoff_orders;")
        drop_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM collection_orders;")
        coll_count = cursor.fetchone()[0]
        conn.close()
        return {"dropoff": drop_count, "collection": coll_count, "total": drop_count + coll_count}
