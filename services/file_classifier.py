"""
Module responsible for classifying Shopee export files into Drop-off or Collection types.
Inspects filenames and internal schema structures to accurately distinguish reports.
"""

from pathlib import Path
from typing import Literal, Tuple
import pandas as pd

FILE_TYPE_DROPOFF = "DROPOFF"
FILE_TYPE_COLLECTION = "COLLECTION"
FILE_TYPE_UNKNOWN = "UNKNOWN"

FileType = Literal["DROPOFF", "COLLECTION", "UNKNOWN"]


class FileClassifier:
    """
    Classifies Shopee spreadsheet files into Drop-off or Collection categories.
    """

    @classmethod
    def classify_file(cls, file_path: Path) -> FileType:
        """
        Identifies whether a file is a Drop-off export or a Collection export.

        :param file_path: Absolute or relative Path pointing to the file (.xlsx or .csv).
        :return: FileType string ('DROPOFF', 'COLLECTION', or 'UNKNOWN').
        """
        path = Path(file_path)
        filename_lower = path.name.lower()

        # 1. Fast path: Filename pattern matching
        if "dropoff" in filename_lower:
            return FILE_TYPE_DROPOFF
        if "collection" in filename_lower:
            return FILE_TYPE_COLLECTION

        # 2. Content inspection fallback (read first row headers)
        try:
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path, nrows=2, encoding="utf-8")
            else:
                df = pd.read_excel(path, nrows=2)

            headers_lower = " ".join([str(col).lower() for col in df.columns])

            if "data de coleta" in headers_lower or "payment method" in headers_lower:
                return FILE_TYPE_COLLECTION
            if "tag" in headers_lower or "tarefa de recebimento" in headers_lower:
                return FILE_TYPE_DROPOFF
        except Exception:
            pass

        return FILE_TYPE_UNKNOWN
