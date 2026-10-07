import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from mtglc import eumetsat


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
