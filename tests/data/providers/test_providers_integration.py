from datetime import datetime, timedelta

import pytest

from quant_agent.data.providers.ccxt_provider import CCXTProvider
from quant_agent.data.providers.yfinance_provider import YFinanceProvider


@pytest.mark.integration
def test_yfinance_provider_fetches_real_data():
    provider = YFinanceProvider()
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    df = provider.fetch("AAPL", "1d", start, end)
    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


@pytest.mark.integration
def test_ccxt_provider_fetches_real_data():
    provider = CCXTProvider(exchange_id="binance")
    end = datetime.utcnow()
    start = end - timedelta(days=1)
    df = provider.fetch("BTC/USDT", "1h", start, end)
    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
