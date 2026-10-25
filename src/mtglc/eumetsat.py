import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import eumdac

CREDENTIALS_PATH = Path.home() / ".eumdac" / "credentials"
COLLECTION_NAMES = {"fci_fdhsi": "EO:EUM:DAT:0662", "li_afa": "EO:EUM:DAT:0687"}
REGEX_PATTERN = re.compile(r"_(\d{4})\.nc$")


def as_utc(dt: datetime):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def get_datastore() -> eumdac.DataStore:
    consumer_key = os.environ.get("EUMDAC_KEY")
    consumer_secret = os.environ.get("EUMDAC_SECRET")

    if not (consumer_key and consumer_secret):
        if not Path.exists(CREDENTIALS_PATH):
            raise RuntimeError("No EUMDAC credentials found. Terminating")
        credentials = CREDENTIALS_PATH.read_text().strip().split(",", 1)
        if len(credentials) != 2:
            raise RuntimeError(f"Unexpected credentials format at {CREDENTIALS_PATH}")
        consumer_key, consumer_secret = credentials
    token = eumdac.AccessToken((consumer_key, consumer_secret))
    datastore = eumdac.DataStore(token)

    return datastore


def search_collections(
    datastore: eumdac.DataStore, included_keys=None, excluded_keys=None
):
    """Finds all collections from datastore that have one of the included_keys none of the excluded_keys in the title.
    This function is not case sensitive.
    Args:
    datastore : eumdac.DataStore
    included_keys: List of strings that should appear in the title of collection
    excluded_keys: List of strings that must not appear in the title of collection

    returns:
    List(Tuple(eumdac.collection.Collection, str)) with [(eumdac.collection.Collection, collection title)]
    """
    included_keys = included_keys or []
    excluded_keys = excluded_keys or []
    if not included_keys and not excluded_keys:
        print("No keys specified.")
        return []
    collections = datastore.collections
    counter = 0
    found_collections = []
    for c in collections:
        title = c.title.lower()
        if included_keys and not any(i_k.lower() in title for i_k in included_keys):
            continue
        if excluded_keys and any(e_k.lower() in title for e_k in excluded_keys):
            continue
        print(c, ": ", title)
        counter += 1
        found_collections.append((c, title))
    print(f"Found {counter} elements.")
    return found_collections


def get_products(
    datastore: eumdac.DataStore,
    identifier: str,
    start_time: datetime,
    end_time: datetime,
) -> list:
    """REturns all products with the given identifier that have the sensing_start within the interval [start_time, end_time).
    Args:
    datastore: eumdac.DataStore,
    identifier: str that is the corresponding identifier
    start_time: datetime for the beginning of the sensing"""

    start_time = as_utc(start_time)
    end_time = as_utc(end_time)
    selected_collection = datastore.get_collection(identifier)
    products = [
        p
        for p in selected_collection.search(dtstart=start_time, dtend=end_time)
        if start_time <= as_utc(p.sensing_start) < end_time
    ]
    return sorted(products, key=lambda p: as_utc(p.sensing_start))


def get_timeslot(dt: datetime) -> datetime:
    """
    Returns the 10-minute timeslot for measurements.

    """
    dt = as_utc(dt)
    dt = dt.replace(second=0, microsecond=0)
    resolution = 10  # minutes
    new_minutes = (dt.minute // resolution) * resolution
    return dt + timedelta(minutes=new_minutes - dt.minute)


def download_bodies(product, target_dir: Path, body_numbers=None) -> list[Path]:
    body_numbers = body_numbers or []
    file_list = []
    target_dir.mkdir(parents=True, exist_ok=True)

    for e in product.entries:
        if "CHK-BODY" not in e:
            continue
        else:
            target_file = target_dir / e
            if e.endswith(".nc"):
                if not body_numbers and not target_file.exists():
                    with (
                        product.open(entry=e) as source,
                        open(target_file, "wb") as target,
                    ):
                        shutil.copyfileobj(source, target)
                    file_list.append(target_file)
                else:
                    for body in body_numbers:
                        if e.endswith(f"_{body:04d}.nc") and not target_file.exists():
                            with (
                                product.open(entry=e) as source,
                                open(target_file, "wb") as target,
                            ):
                                shutil.copyfileobj(source, target)
                            file_list.append(target_file)
            else:
                continue
    return sorted(file_list)


def download(
    datastore, collectionname, target_dir, starttime, endtime, body_numbers=None
):
    body_numbers = body_numbers or []
    identifier = COLLECTION_NAMES[collectionname]
    products = get_products(datastore, identifier, starttime, endtime)
    for p in products:
        timeslot = get_timeslot(as_utc(p.sensing_start))
        target_path = get_product_dir(target_dir, collectionname, timeslot)
        download_bodies(p, target_path, body_numbers)


def get_product_dir(data_dir: Path, collection_name: str, dt: datetime) -> Path:
    timeslot = get_timeslot(as_utc(dt))
    target_path = (
        data_dir
        / collection_name
        / timeslot.strftime("%Y%m%d")
        / timeslot.strftime("%H%M")
    )
    return target_path


def chunk_number_from_filename(filename: str, pattern=REGEX_PATTERN) -> int:
    match = pattern.search(filename)
    if match is None:
        raise ValueError(f"Chunk number could not be determined from file {filename}")
    return int(match.group(1))


def check_chunk_completeness(filenames: list[Path], expected_chunks: list[int]) -> None:
    found_chunks = [chunk_number_from_filename(f) for f in filenames]
    expected_chunks = set(expected_chunks)
    missing = expected_chunks - set(found_chunks)
    extra = set(found_chunks) - expected_chunks
    duplicates = {x for x in found_chunks if found_chunks.count(x) > 1}

    if missing or extra or duplicates:
        raise ValueError(
            f"Mismatch in expected and found chunks. Missing {missing}, extra {extra}, duplicates {duplicates}"
        )


def check_channel_completeness(
    found_channels: list[str], expected_channels: list[str]
) -> None:
    expected_channels = set(expected_channels)
    missing_channels = expected_channels - set(found_channels)

    if missing_channels:
        raise ValueError(
            f"Mismatch in found channels. Missing channels {missing_channels}"
        )


def get_product_filelist(path) -> list[Path]:
    if not path.is_dir():
        raise FileNotFoundError(f"Product folder not found: {path}")
    filelist = sorted([f for f in path.glob("*.nc") if "CHK-BODY" in f.name])
    return filelist


def select_chunk(filelist: list[Path], chunks: list[int]) -> list[Path]:
    chunk_dict = {}
    for f in filelist:
        c = chunk_number_from_filename(str(f))
        if c not in chunk_dict:
            chunk_dict[c] = []
        chunk_dict[c].append(f)
    missing_chunks = set(chunks) - chunk_dict.keys()
    duplicate_chunks = [k for k in chunk_dict if len(chunk_dict[k]) > 1 and k in chunks]
    if missing_chunks or duplicate_chunks:
        raise ValueError(
            f"Chunk mismatch. Missing {missing_chunks}, duplicate {duplicate_chunks}"
        )
    return [chunk_dict[c][0] for c in chunk_dict if c in chunks]
