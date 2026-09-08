"""
Module responsible for loading and validating Shopee Drop-off and Collection files.
Supports both .xlsx (Excel) and .csv formats with automatic encoding and schema detection.
"""

from pathlib import Path
from typing import Tuple
import pandas as pd

from config import (
    INBOUND_TIME_COL_INDEX,
    OUTBOUND_TIME_COL_INDEX,
    COLLECTION_INBOUND_COL_INDEX,
    COLLECTION_OUTBOUND_COL_INDEX,
)
from services.file_classifier import FileClassifier, FILE_TYPE_COLLECTION, FILE_TYPE_DROPOFF


class ExcelLoader:
    """
    Handles file ingestion and schema validation for Shopee drop-off and collection reports.
    """

    def __init__(self, file_path: Path):
        """
        Initializes the loader with the target file path.

        :param file_path: Path pointing to an .xlsx or .csv file.
        """
        self.file_path = Path(file_path)

    def load_data(self) -> Tuple[pd.DataFrame, str, str, str, str]:
        """
        Loads the spreadsheet/CSV, classifies its type, and identifies key column headers.

        :raises FileNotFoundError: If the target file does not exist.
        :raises ValueError: If columns cannot be parsed.
        :return: A tuple containing:
                 - df (pd.DataFrame): Raw loaded DataFrame.
                 - file_type (str): 'DROPOFF' or 'COLLECTION'.
                 - tag_col_name (str): Column name for Tag (or empty string for collection).
                 - inbound_col_name (str): Column name for inbound timestamp.
                 - outbound_col_name (str): Column name for outbound timestamp.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_path}")

        file_type = FileClassifier.classify_file(self.file_path)

        # Load file into DataFrame
        if self.file_path.suffix.lower() == ".csv":
            df = self._load_csv_safely(self.file_path)
        else:
            df = pd.read_excel(self.file_path, engine="openpyxl")

        # Column identification based on classified report type
        if file_type == FILE_TYPE_COLLECTION:
            # Collection report schema
            tag_col_name = ""
            inbound_col_name = self._find_column_by_name_or_index(
                df, preferred_index=COLLECTION_INBOUND_COL_INDEX, keywords=["recebimento", "inbound", "received"]
            )
            outbound_col_name = self._find_column_by_name_or_index(
                df, preferred_index=COLLECTION_OUTBOUND_COL_INDEX, keywords=["envio", "outbound", "retirada", "shipped"]
            )
        else:
            # Drop-off report schema
            file_type = FILE_TYPE_DROPOFF
            tag_col_name = self._find_column_by_name_or_index(df, preferred_index=1, keywords=["tag"])
            inbound_col_name = self._find_column_by_name_or_index(
                df, preferred_index=INBOUND_TIME_COL_INDEX, keywords=["recebimento", "inbound", "received"]
            )
            outbound_col_name = self._find_column_by_name_or_index(
                df, preferred_index=OUTBOUND_TIME_COL_INDEX, keywords=["envio", "outbound", "shipped"]
            )

        return df, file_type, tag_col_name, inbound_col_name, outbound_col_name

    @staticmethod
    def _load_csv_safely(path: Path) -> pd.DataFrame:
        """Attempts reading CSV with multiple common encodings."""
        for enc in ("utf-8", "utf-8-sig", "latin1", "cp1252"):
            try:
                return pd.read_csv(path, encoding=enc)
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        # Fallback
        return pd.read_csv(path, encoding="latin1", errors="replace")

    @staticmethod
    def _find_column_by_name_or_index(df: pd.DataFrame, preferred_index: int, keywords: list[str]) -> str:
        """Finds column name matching specific phrase keywords or falls back to positional index."""
        # 1. First check if preferred_index matches keywords
        if len(df.columns) > preferred_index:
            pref_col = str(df.columns[preferred_index])
            clean_pref = pref_col.lower()
            if any(k in clean_pref for k in keywords):
                return pref_col

        # 2. Search other columns prioritizing exact phrase matches
        for col in df.columns:
            clean = str(col).lower()
            if any(k in clean for k in keywords):
                # Avoid picking 'tarefa de recebimento' (Task ID) when looking for timestamps
                if "tarefa" in clean or "task" in clean:
                    continue
                return str(col)

        if len(df.columns) > preferred_index:
            return str(df.columns[preferred_index])

        raise ValueError(f"Não foi possível identificar a coluna para {keywords} no arquivo.")
