from datetime import datetime
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
