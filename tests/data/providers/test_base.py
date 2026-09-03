import pytest

from quant_agent.data.providers.base import MarketDataFetchError, MarketDataProvider


def test_market_data_provider_is_abstract():
    with pytest.raises(TypeError):
        MarketDataProvider()


def test_market_data_fetch_error_is_exception():
    assert issubclass(MarketDataFetchError, Exception)
