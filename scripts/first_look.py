from datetime import UTC, datetime, timedelta
from pathlib import Path

from mtglc import eumetsat

TIMESTAMP = datetime(2025, 7, 1, 14, 0, tzinfo=UTC)
TIMEWINDOW = timedelta(minutes=60)

RAW_DATA_DIR = Path("data/raw")
CREDENTIALS_PATH = Path.home() / ".eumdac" / "credentials"
COLLECTION_NAMES = {"fci_fdhsi": "EO:EUM:DAT:0662", "li_afa": "EO:EUM:DAT:0687"}


def main():
    datastore = eumetsat.get_datastore()

    eumetsat.download(
        datastore, "li_afa", RAW_DATA_DIR, TIMESTAMP, TIMESTAMP + TIMEWINDOW
    )
    eumetsat.download(
        datastore,
        "fci_fdhsi",
        RAW_DATA_DIR,
        TIMESTAMP,
        TIMESTAMP + timedelta(minutes=10),
    )


if __name__ == "__main__":
    main()
