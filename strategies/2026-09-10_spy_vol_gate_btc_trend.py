"""Strategy: BTC/USDT SMA trend-following, gated by SPY's own realized
volatility regime (equity-volatility spillover into crypto).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from Conrad, Custovic & Ghysels (2018), "Long- and Short-Term
Cryptocurrency Volatility Components: A GARCH-MIDAS Analysis", Journal of
Risk and Financial Management (MDPI), https://www.mdpi.com/1911-8074/11/2/23:
the paper's headline finding (via Google AI-overview summary of the
paper's abstract/conclusions, 440+ citations) is that S&P 500 realized
volatility has a NEGATIVE and highly significant effect on Bitcoin's
LONG-TERM volatility component -- i.e. when equity-market realized vol is
elevated, Bitcoin's own volatility (over the following weeks/months)
tends to be structurally LOWER, not higher (an "atypical" cross-market
volatility spillover finding, per the paper's own framing, since one might
naively expect stress to propagate the same direction across markets).

This strategy operationalizes that finding as a regime gate for a BTC/USDT
trend-following signal: participate in a BTC SMA trend-following long only
when SPY's own trailing realized volatility is ABOVE a threshold (the
regime the paper associates with subsequently LOWER Bitcoin volatility,
hypothesized here as a calmer/more tradeable trending regime for BTC); go
flat when SPY realized vol is low (the regime associated with higher
subsequent Bitcoin volatility/choppier price action).

This is a structurally new signal for this repo: no prior entry uses
EQUITY (SPY) realized volatility as a regime gate for a CRYPTO strategy --
every prior cross-asset equity/crypto interaction in this repo (DXY,
HYG/LQD, gold ratios, network momentum) uses a PRICE or RATIO signal, not
the equity market's own REALIZED VOLATILITY level as the gating variable
for a crypto strategy.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} participation)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, causal -- SPY vol and BTC trend both shifted 1 day)
"""

from __future__ import annotations

import pandas as pd

from loaders import load_equity


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _spy_vol_aligned(index: pd.DatetimeIndex, vol_window: int) -> pd.Series:
    """Fetch SPY daily close, compute trailing realized vol, align to the
    given (possibly crypto, 24/7) index via forward-fill."""
    start = index.min()
    end = index.max()
    spy_df = load_equity("SPY", start.to_pydatetime(), end.to_pydatetime())
    spy_df = _prep(spy_df)
    spy_close = spy_df["close"]
    spy_ret = spy_close.pct_change()
    spy_vol = (spy_ret.rolling(vol_window).std() * (252 ** 0.5))
    spy_vol_aligned = spy_vol.reindex(index).ffill()
    return spy_vol_aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    spy_vol_window: int = 20,
    spy_vol_threshold: float = 0.15,
) -> pd.Series:
    """Return a {0,1} participation series: 1 = long trend-following
    position on the traded asset, 0 = flat.

    Trend condition: close > SMA(trend_window) on the traded asset itself.
    Regime gate: SPY's own trailing `spy_vol_window`-day annualized
    realized vol must be ABOVE `spy_vol_threshold` (per Conrad et al.'s
    finding that elevated equity-market RV precedes structurally lower
    subsequent Bitcoin volatility). Both conditions use only information
    known as of the PRIOR close (shifted by 1) to avoid look-ahead.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    above_trend = (close > trend_sma).fillna(False)

    spy_vol = _spy_vol_aligned(close.index, spy_vol_window)
    high_spy_vol_regime = (spy_vol > spy_vol_threshold).fillna(False)

    raw_signal = (above_trend & high_spy_vol_regime).astype(int)
    position = raw_signal.shift(1).fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily close-to-close strategy returns: position[t] * (close[t]/close[t-1] - 1)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = (position * daily_ret).fillna(0.0)
    strat_returns.name = "strategy_returns"
    return strat_returns
