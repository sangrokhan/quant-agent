import logging
from datetime import datetime, timezone

import pandas as pd
import pytest

from quant_agent.data.cache import ParquetCache
from quant_agent.data.models import CacheKey


def make_df(rows):
    return pd.DataFrame(
        rows,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )


@pytest.fixture
def key():
    return CacheKey(source="yfinance", symbol="AAPL", interval="1d")


def test_get_coverage_none_when_no_file(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    assert cache.get_coverage(key) is None


def test_write_then_get_coverage(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-03", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    coverage = cache.get_coverage(key)
    assert coverage == (pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-01-03", tz="UTC"))


def test_write_merges_and_dedupes(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    first = make_df([[pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100]])
    second = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 9, 9, 9, 9, 999],  # duplicate timestamp, should be replaced
            [pd.Timestamp("2024-01-02", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, first)
    cache.write(key, second)
    full = cache.read(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert len(full) == 2
    assert full.iloc[0]["open"] == 9  # later write wins on duplicate timestamp


def test_covers_true_when_range_fully_inside(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-10", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    assert cache.covers(key, datetime(2024, 1, 2), datetime(2024, 1, 5)) is True


def test_covers_false_when_range_extends_beyond_cache(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df([[pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100]])
    cache.write(key, df)
    assert cache.covers(key, datetime(2024, 1, 1), datetime(2024, 1, 5)) is False


def test_read_slices_to_requested_range(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-05", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-10", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    sliced = cache.read(key, datetime(2024, 1, 2), datetime(2024, 1, 6))
    assert list(sliced["timestamp"]) == [pd.Timestamp("2024-01-05", tz="UTC")]


def test_log_hit_emits_info_log(tmp_path, key, caplog):
    cache = ParquetCache(base_dir=str(tmp_path))
    with caplog.at_level(logging.INFO, logger="quant_agent.data.cache"):
        cache.log_hit(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert "cache_hit" in caplog.text


def test_log_miss_emits_info_log(tmp_path, key, caplog):
    cache = ParquetCache(base_dir=str(tmp_path))
    with caplog.at_level(logging.INFO, logger="quant_agent.data.cache"):
        cache.log_miss(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert "cache_miss" in caplog.text
