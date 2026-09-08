"""
Database connection and schema initialization module.
Manages local SQLite database storage for historical package tracking.
"""

from pathlib import Path
import sqlite3

from config import DATA_DIR

DB_FILE = DATA_DIR / "agency_history.db"


def get_db_connection() -> sqlite3.Connection:
    """
    Returns an active SQLite database connection with row factory enabled.

    :return: sqlite3.Connection instance.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # Better concurrency and performance
    return conn


def initialize_database() -> None:
    """
    Initializes database tables and indexes if they do not exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop-off packages table (postagens e devoluções)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dropoff_orders (
            tracking_code TEXT PRIMARY KEY,
            tag TEXT,
            package_type TEXT,
            inbound_time TEXT,
            outbound_time TEXT,
            status TEXT,
            business_seconds INTEGER,
            business_formatted TEXT,
            raw_seconds INTEGER,
            unit_fee REAL,
            reference_month TEXT, -- YYYY-MM based on outbound or inbound
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Collection packages table (retirada de compradores)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_orders (
            tracking_code TEXT PRIMARY KEY,
            package_type TEXT,
            inbound_time TEXT,
            outbound_time TEXT,
            status TEXT,
            unit_fee REAL,
            reference_month TEXT, -- YYYY-MM
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Indexes for fast querying by month and status
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dropoff_month ON dropoff_orders(reference_month);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dropoff_status ON dropoff_orders(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_month ON collection_orders(reference_month);")

    conn.commit()
    conn.close()


# Ensure database is initialized on import
initialize_database()
