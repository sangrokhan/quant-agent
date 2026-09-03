from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from quant_agent.data.providers.base import MarketDataFetchError
from quant_agent.data.providers.yfinance_provider import YFinanceProvider


def make_yf_raw():
    index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    return pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [1.5, 2.5],
            "Low": [0.5, 1.5],
            "Close": [1.2, 2.2],
            "Volume": [100, 200],
        },
        index=index,
    )


def test_fetch_normalizes_columns_and_schema():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=make_yf_raw()):
        df = provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["timestamp"].dt.tz is not None


def test_fetch_returns_empty_df_when_no_data():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=pd.DataFrame()):
        df = provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df.empty


def test_fetch_raises_market_data_fetch_error_on_exception():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", side_effect=RuntimeError("boom")):
        with pytest.raises(MarketDataFetchError):
            provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))


def test_fetch_bumps_end_by_one_day_for_yf_download_exclusive_end():
    # yf.download treats `end` as exclusive, but this provider's contract is an
    # inclusive [start, end] range. fetch() must pass end + 1 day to yf.download
    # so the bar for `end` itself is actually returned (see cache.covers()).
    provider = YFinanceProvider()
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)
    with patch(
        "quant_agent.data.providers.yfinance_provider.yf.download", return_value=make_yf_raw()
    ) as mock_download:
        provider.fetch("AAPL", "1d", start, end)

    _, kwargs = mock_download.call_args
    assert kwargs["end"] == end + timedelta(days=1)
    assert kwargs["end"] != end


def test_fetch_flattens_multiindex_columns():
    index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    index.name = "Date"
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "AAPL"),
            ("High", "AAPL"),
            ("Low", "AAPL"),
            ("Close", "AAPL"),
            ("Volume", "AAPL"),
        ]
    )
    raw = pd.DataFrame(
        [[1.0, 1.5, 0.5, 1.2, 100], [2.0, 2.5, 1.5, 2.2, 200]],
        index=index,
        columns=columns,
    )

    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=raw):
        df = provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2


def test_fetch_renames_intraday_datetime_index():
    index = pd.to_datetime(["2024-01-01 09:30", "2024-01-01 10:30"])
    index.name = "Datetime"
    raw = pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [1.5, 2.5],
            "Low": [0.5, 1.5],
            "Close": [1.2, 2.2],
            "Volume": [100, 200],
        },
        index=index,
    )

    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=raw):
        df = provider.fetch("AAPL", "1h", datetime(2024, 1, 1), datetime(2024, 1, 1))

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["timestamp"].dt.tz is not None
