from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from quant_agent.data.providers.base import MarketDataFetchError
from quant_agent.data.providers.ccxt_provider import CCXTProvider


def ms(dt):
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def test_fetch_normalizes_single_batch():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)
    batch = [
        [ms(datetime(2024, 1, 1)), 1.0, 1.5, 0.5, 1.2, 100],
        [ms(datetime(2024, 1, 2)), 2.0, 2.5, 1.5, 2.2, 200],
    ]
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = [batch, []]

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        df = provider.fetch("BTC/USDT", "1d", start, end)

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["timestamp"].dt.tz is not None


def test_fetch_returns_empty_df_when_no_data():
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = []

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        df = provider.fetch("BTC/USDT", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df.empty


def test_fetch_raises_market_data_fetch_error_on_exception():
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = RuntimeError("boom")

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        with pytest.raises(MarketDataFetchError):
            provider.fetch("BTC/USDT", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
