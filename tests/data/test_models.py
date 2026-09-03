from quant_agent.data.models import CacheKey


def test_sanitized_symbol_replaces_slash():
    key = CacheKey(source="ccxt", symbol="BTC/USDT", interval="1h", exchange="binance")
    assert key.sanitized_symbol() == "BTC_USDT"


def test_sanitized_symbol_no_slash_unchanged():
    key = CacheKey(source="yfinance", symbol="AAPL", interval="1d")
    assert key.sanitized_symbol() == "AAPL"


def test_cache_path_yfinance_uses_underscore_for_missing_exchange():
    key = CacheKey(source="yfinance", symbol="AAPL", interval="1d")
    path = key.cache_path("data/cache")
    assert path == "data/cache/yfinance/_/AAPL/1d.parquet"


def test_cache_path_ccxt_includes_exchange():
    key = CacheKey(source="ccxt", symbol="BTC/USDT", interval="1h", exchange="binance")
    path = key.cache_path("data/cache")
    assert path == "data/cache/ccxt/binance/BTC_USDT/1h.parquet"
