import io
import re
from contextlib import nullcontext as does_not_raise
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from mtglc import eumetsat

TESTTIME = datetime(2025, 7, 1, 14, 0, tzinfo=UTC)


class DummyCollection:
    def __init__(self, products):
        self.products = products

    def search(self, dtstart, dtend):
        return self.products


class DummyDatastore:
    def __init__(self, collection):
        self.collection = collection

    def get_collection(self, identifier):
        return self.collection


def test_get_products():
    starttime = datetime(2015, 1, 1, 23, 0, tzinfo=UTC)
    endtime = datetime(2015, 1, 2, 0, 0, tzinfo=UTC)
    time_steps = [
        starttime.replace(tzinfo=None) + timedelta(minutes=minutes)
        for minutes in reversed(range(-10, 70, 10))
    ]
    expected_time_steps = [
        eumetsat.as_utc(starttime) + timedelta(minutes=minutes)
        for minutes in range(0, 60, 10)
    ]
    dummy_products = [SimpleNamespace(sensing_start=t) for t in time_steps]
    dummy_collection = DummyCollection(dummy_products)
    dummy_datastore = DummyDatastore(dummy_collection)

    products = eumetsat.get_products(dummy_datastore, "dummy", starttime, endtime)
    assert [eumetsat.as_utc(p.sensing_start) for p in products] == expected_time_steps


@pytest.mark.parametrize(
    ("dt", "expected_dt"),
    [
        (
            datetime(2015, 1, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2015, 1, 1, 1, 0, tzinfo=UTC),
        ),
        (
            datetime(2014, 12, 31, 23, 59, 59, 99, tzinfo=UTC),
            datetime(2014, 12, 31, 23, 50, tzinfo=UTC),
        ),
        (
            datetime(2015, 1, 1, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2015, 1, 1, 1, 10, tzinfo=UTC),
        ),
        (
            datetime(2015, 1, 1, 1, 19, 59, tzinfo=UTC),
            datetime(2015, 1, 1, 1, 10, tzinfo=UTC),
        ),
    ],
)
def test_get_times(dt, expected_dt):
    assert eumetsat.get_timeslot(dt) == expected_dt


class DummyProduct:
    def __init__(self, entries):
        self.entries = entries

    def open(self, entry):
        return io.BytesIO(b"dummydata")


@pytest.mark.parametrize(
    ("body_numbers", "expected_files"),
    [
        (None, ["x_CHK-BODY_..._0001.nc", "x_CHK-BODY_..._0002.nc"]),
        ([2, 1], ["x_CHK-BODY_..._0001.nc", "x_CHK-BODY_..._0002.nc"]),
        ([22], []),
        ([22, 1], ["x_CHK-BODY_..._0001.nc"]),
    ],
)
def test_download_bodies(body_numbers, expected_files, tmp_path):
    ENTRIES = [
        "x_CHK-BODY_..._0002.nc",
        "x_CHK-BODY_..._0001.nc",
        "x_CHK-TRAIL_..._0002.nc",
        "x_CHK-BODY_..._0002.png",
    ]
    fake_product = DummyProduct(ENTRIES)
    filelist = eumetsat.download_bodies(fake_product, tmp_path, body_numbers)
    assert filelist == [tmp_path / e for e in expected_files]
    assert sorted([p.name for p in tmp_path.iterdir()]) == expected_files


@pytest.fixture
def dummy_eumdac(monkeypatch):
    monkeypatch.setattr(eumetsat.eumdac, "DataStore", DummyDatastoreEumdac)
    monkeypatch.setattr(eumetsat.eumdac, "AccessToken", DummyToken)


class DummyDatastoreEumdac:
    def __init__(self, token):
        self.token = token


class DummyToken:
    def __init__(self, credentials):
        self.credentials = credentials


def test_get_datastore_from_env(monkeypatch, dummy_eumdac):
    monkeypatch.setenv("EUMDAC_KEY", "k")
    monkeypatch.setenv("EUMDAC_SECRET", "s")

    datastore = eumetsat.get_datastore()
    assert isinstance(datastore, DummyDatastoreEumdac)
    assert datastore.token.credentials == ("k", "s")


def test_get_datastore_from_file(monkeypatch, tmp_path, dummy_eumdac):
    monkeypatch.delenv("EUMDAC_KEY", raising=False)
    monkeypatch.delenv("EUMDAC_SECRET", raising=False)

    credentials_file = tmp_path / "credentials"
    credentials_file.write_text("k,s\n")

    monkeypatch.setattr(eumetsat, "CREDENTIALS_PATH", credentials_file)

    datastore = eumetsat.get_datastore()
    assert datastore.token.credentials == ("k", "s")


def test_get_datastore_missing_credentials(monkeypatch, tmp_path, dummy_eumdac):
    monkeypatch.delenv("EUMDAC_KEY", raising=False)
    monkeypatch.delenv("EUMDAC_SECRET", raising=False)
    monkeypatch.setattr(eumetsat, "CREDENTIALS_PATH", tmp_path / "missing")

    with pytest.raises(RuntimeError, match="No EUMDAC credentials found"):
        _ = eumetsat.get_datastore()


def test_get_product_dir(tmp_path):
    dt = datetime(2025, 7, 1, 14, 7, tzinfo=UTC)
    product_name = "fci_fdhsi"
    expected_path = tmp_path / product_name / "20250701" / "1400"
    assert eumetsat.get_product_dir(tmp_path, product_name, dt) == expected_path


def test_chunk_number_from_filename(tmp_path):
    filename1 = str(tmp_path / body_name(1234))
    filename2 = str(tmp_path / (body_name(1234) + "a"))
    filename3 = str(tmp_path / body_name(1234).replace("1234.nc", "123.nc"))
    filename4 = str(tmp_path / body_name(4))

    assert eumetsat.chunk_number_from_filename(filename1) == 1234
    with pytest.raises(ValueError, match="Chunk number could not be determined"):
        eumetsat.chunk_number_from_filename(filename2)
    with pytest.raises(ValueError, match="Chunk number could not be determined"):
        eumetsat.chunk_number_from_filename(filename3)
    assert eumetsat.chunk_number_from_filename(filename4) == 4


def test_chunk_completeness():
    filename1 = body_name(1234)
    filename2 = body_name(4)
    filename3 = body_name(1235)
    filename4 = body_name(1234)
    assert (
        eumetsat.check_chunk_completeness(
            [filename1, filename2, filename3], [1234, 4, 1235]
        )
        is None
    )
    with pytest.raises(ValueError, match=re.escape("extra {4}")):
        eumetsat.check_chunk_completeness(
            [filename1, filename2, filename3], [1234, 1235]
        )
    with pytest.raises(ValueError, match=re.escape("duplicates {1234}")):
        eumetsat.check_chunk_completeness(
            [filename1, filename3, filename4], [1234, 1235]
        )
    with pytest.raises(ValueError, match=re.escape("Missing {1235}")):
        eumetsat.check_chunk_completeness([filename1, filename2], [1234, 1235])


@pytest.mark.parametrize(
    ("found_channels", "expected_channels", "outcome"),
    [
        (
            ["ir_105", "nir_13", "vis_04", "vis_06"],
            ["ir_105", "nir_13", "vis_04", "vis_06"],
            does_not_raise(),
        ),
        (
            ["ir_105", "nir_13", "vis_04", "vis_06"],
            ["ir_105", "nir_13", "vis_06", "vis_04"],
            does_not_raise(),
        ),
        (
            ["ir_105", "nir_13", "vis_04"],
            ["ir_105", "nir_13", "vis_04", "vis_06"],
            pytest.raises(ValueError, match=re.escape("Missing channels {'vis_06'}")),
        ),
    ],
)
def test_check_channel_completeness(found_channels, expected_channels, outcome):
    with outcome:
        eumetsat.check_channel_completeness(found_channels, expected_channels)


def test_get_product_filelist(tmp_path):
    make_product_dir(tmp_path)
    filelist = eumetsat.get_product_filelist(
        tmp_path / "fci_fdhsi" / "20250701" / "1400"
    )
    assert [eumetsat.chunk_number_from_filename(f.name) for f in filelist] == [
        3,
        17,
        40,
    ]


def body_name(n: int) -> str:
    return f"W_XX-EUMETSAT-Darmstadt,IMG+SAT,MTI1+FCI-1C-RRAD-FDHSI-FD--CHK-BODY---NC4E_C_EUMT_20250718141512_IDPFI_OPE_20250718140007_20250718140924_N__O_0085_{n:04d}.nc"


def make_product_dir(tmp_path):
    folder = tmp_path / "fci_fdhsi" / "20250701" / "1400"
    folder.mkdir(parents=True)
    for n in (40, 3, 17):
        (folder / body_name(n)).touch()
    (folder / body_name(41).replace("CHK-BODY", "CHK-TRAIL")).touch()
    (folder / body_name(5).replace(".nc", ".part")).touch()
    (folder / "manifest.xml").touch()
    (folder / "quicklook.png").touch()
    return folder


def test_select_chunk(tmp_path):
    folder = make_product_dir(tmp_path)
    filelist = eumetsat.get_product_filelist(folder)
    kept_chunks = eumetsat.select_chunk(filelist, [17, 40])
    assert [eumetsat.chunk_number_from_filename(str(f)) for f in kept_chunks] == [
        17,
        40,
    ]
    with pytest.raises(ValueError, match=re.escape("Missing {18}")):
        eumetsat.select_chunk(filelist, [18, 40])
    long_filelist = filelist + filelist
    with pytest.raises(ValueError, match=re.escape("duplicate [17, 40]")):
        eumetsat.select_chunk(long_filelist, [17, 40])
