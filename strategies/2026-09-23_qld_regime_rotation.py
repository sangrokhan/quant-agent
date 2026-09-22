"""Strategy: QLD (2x Nasdaq-100) regime-timing rotation, gated by a QQQ
trend + 126-day momentum filter (single-leg conservative-leverage adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per FinLab's "ETF Rotation Strategy Backtest: One Risk-On/Risk-Off Signal,
Two Leverage Levels" (https://finlab.finance/en/blog/us-etf-rotation-strategy),
a fully disclosed regime-timing rule: risk-on when QQQ closes above its
200-day SMA AND its trailing 126-day return is positive; risk-off otherwise.
The source's CONSERVATIVE variant expresses this signal through 2x leveraged
index ETFs (QLD/SSO, held ~50/50 whenever risk-on since with only two
candidates the source's own ranking step nearly always selects both), while
the AGGRESSIVE variant uses 3x TQQQ/TECL (already tested this cron trigger
as 2026-09-23-006, rejected on decisive MDD fail). The source's own
published stats for the CONSERVATIVE (2x) version: 2016-2026 CAGR 30.5%,
Sharpe 1.38, MAX DRAWDOWN ONLY -17.9% (well inside this repo's 0.25
threshold, unlike the 3x aggressive sibling's -29.3%/-27.6% MDDs which both
failed this repo's validator), turnover 2.5x/year (175 trades over the
decade -- much lower turnover than the 3x laggard-rotation sibling).

Framework adaptation note: this repo's single-symbol 0/1 position contract
cannot express the source's genuine 2-instrument 50/50 QLD+SSO holding, so
this strategy simplifies to a SINGLE-LEG QLD-only version: hold QLD
(price_df) when the QQQ regime gate is risk-on, flat/cash when risk-off (no
SSO leg, no IEF/GLD/SHY defensive-sleeve rotation). This is the SAME
conservative simplification pattern already used in this repo's rejected
TQQQ/TECL sibling this cron trigger, but on the source's LOWER-DRAWDOWN 2x
leverage tier rather than the 3x tier, testing whether the lower leverage
level survives this repo's MDD threshold where the 3x version did not.

Signal logic
------------
- Regime filter (on QQQ): close > SMA(200) AND 126-day return > 0 -> risk-on.
- Long QLD (position=1) whenever risk-on; flat otherwise.
- No separate exit rule beyond the regime flag itself flipping to risk-off.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_regime_series(index: pd.DatetimeIndex, symbol: str) -> pd.Series:
    """Fetch the regime-gate symbol's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min() - timedelta(days=400)  # extra lookback for the 200d/126d regime calc
    end = index.max() + timedelta(days=2)
    df = load_equity(symbol, start, end)
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    regime_symbol: str = "QQQ",
    trend_sma: int = 200,
    momentum_window: int = 126,
) -> pd.Series:
    """Return a {0,1} position series: hold QLD (price_df) whenever the QQQ
    trend+momentum regime gate is risk-on."""
    df = _prep(price_df)
    close = df["close"]

    regime_close = _load_regime_series(df.index, regime_symbol)
    regime_close = regime_close.reindex(
        regime_close.index.union(close.index), method="ffill"
    ).reindex(close.index, method="ffill")

    regime_sma = regime_close.rolling(trend_sma, min_periods=trend_sma).mean()
    regime_mom = regime_close.pct_change(momentum_window)
    risk_on = (regime_close > regime_sma) & (regime_mom > 0)

    valid = regime_sma.notna() & regime_mom.notna()

    position = (risk_on & valid).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    regime_symbol: str = "QQQ",
    trend_sma: int = 200,
    momentum_window: int = 126,
) -> pd.Series:
    """Return daily strategy returns (position held from signal close to next bar close)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        regime_symbol=regime_symbol,
        trend_sma=trend_sma,
        momentum_window=momentum_window,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
