from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from quant_agent.data.cache import ParquetCache
from quant_agent.data.market_data import MarketDataService


def make_df(rows):
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(base_dir=str(tmp_path))


def test_full_miss_fetches_and_caches(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100],
            [pd.Timestamp("2024-01-02", tz="UTC"), 1, 1, 1, 1, 100],
        ]
    )
    service._providers["yfinance"] = mock_provider

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))

    mock_provider.fetch.assert_called_once_with("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert len(result) == 2


def test_full_hit_does_not_call_provider(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100],
            [pd.Timestamp("2024-01-05", tz="UTC"), 1, 1, 1, 1, 100],
        ]
    )
    service._providers["yfinance"] = mock_provider

    service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 5))
    mock_provider.fetch.reset_mock()

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 2), datetime(2024, 1, 4))

    mock_provider.fetch.assert_not_called()
    assert len(result) == 0  # no rows exactly between 01-02 and 01-04 in the cached set, range still served from cache


def test_partial_miss_fetches_only_the_gap(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-05", tz="UTC"), 1, 1, 1, 1, 100],
         [pd.Timestamp("2024-01-10", tz="UTC"), 1, 1, 1, 1, 100]]
    )
    service._providers["yfinance"] = mock_provider
    service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 5), datetime(2024, 1, 10))
    mock_provider.fetch.reset_mock()

    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-12", tz="UTC"), 2, 2, 2, 2, 200]]
    )

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 5), datetime(2024, 1, 12))

    mock_provider.fetch.assert_called_once_with("AAPL", "1d", pd.Timestamp("2024-01-10", tz="UTC").to_pydatetime(), datetime(2024, 1, 12))
    assert len(result) == 3


def test_ccxt_source_uses_exchange_specific_provider(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100]]
    )
    service._ccxt_providers["binance"] = mock_provider

    result = service.get(
        "ccxt", "BTC/USDT", "1h", datetime(2024, 1, 1), datetime(2024, 1, 1), exchange="binance"
    )

    mock_provider.fetch.assert_called_once()
    assert len(result) == 1
