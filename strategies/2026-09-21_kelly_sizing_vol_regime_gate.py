"""Strategy: Fractional-Kelly-criterion position sizing overlay, gated to a
low-realized-volatility regime only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-XXX):
Direct rescue/fix of already-rejected 2026-09-08-176 (Fractional-Kelly
sizing overlay on an SMA(200) trend gate; per JournalX
https://journalx.app/blog/kelly-criterion-position-sizing). That entry's own
recorded grid evidence showed the edge concentrated almost entirely in the
low-realized-vol tercile: 12/24 low-vol cells passed vs 5/24 mid-vol and
0/24 high-vol, and the single best cell (SPY, kelly_fraction=0.25,
default_weight=0.5, low-vol) achieved Sharpe 2.195 -- while the unconditional
full-sample QQQ Sharpe (0.274) and net-of-cost Sharpe (-0.117) both failed
decisively, dragged down by high-vol-regime whipsaw in Kelly's own trailing
win-rate/payoff estimate (an estimate that is inherently noisier and more
prone to false high-Kelly-fraction sizing during choppy/high-vol periods).

This iteration adds this repo's own standard low-vol-regime gate
(strategies/2026-09-03_bb_meanrev_qqq_volregime.py pattern: 20-day realized
vol vs its trailing 252-day median, "low-vol" when current <= vol_regime_ratio
x that median) ON TOP of the unchanged Kelly-sizing + SMA(trend_window) trend
filter mechanic: force exposure to 0 whenever the asset is NOT in a low-vol
regime, regardless of what the trend filter or Kelly estimate says. No new
external research this iteration -- reusing this repo's own already-confirmed
formula/finding and its own already-confirmed vol-regime-gate construction to
directly repair a previously-recorded near-miss/rejected finding, per
RESEARCH_LOOP.md Step 3's guidance to prefer fixing near-misses over
generating a brand-new untested idea from scratch.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series (weight,
        continuous exposure in [0, leverage_cap]).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    trade_history_window: int = 252,
    kelly_fraction: float = 0.25,
    leverage_cap: float = 1.0,
    min_trades_for_estimate: int = 10,
    default_weight: float = 0.5,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return the fractional-Kelly exposure weight series (continuous, in
    [0, leverage_cap]), forced flat outside a low-realized-vol regime.

    Kelly's p (win rate) and b (avg win / avg loss) are estimated from the
    strategy's OWN trailing `trade_history_window` days of the underlying
    asset's daily returns ON DAYS WHEN THE TREND FILTER WAS ACTIVE (i.e. the
    "trades" this strategy would have taken), strictly using data up to and
    including day t-1 only (no lookahead). Before `min_trades_for_estimate`
    qualifying days are available, use `default_weight` as a neutral
    placeholder sizing. On top of that, exposure is forced to 0 whenever the
    asset's own 20-day realized volatility exceeds `vol_regime_ratio` times
    its trailing `vol_lookback`-day median (i.e. NOT in a low-vol regime).
    """
    import math

    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma
    daily_ret = close.pct_change().fillna(0.0)

    # Realized-vol regime filter (repo-standard construction).
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median * vol_regime_ratio)
    low_vol_regime = low_vol_regime.fillna(False)

    # Only the days the trend filter would have been long count as "trades"
    # for Kelly's own trailing win-rate/payoff estimate (unchanged from
    # 2026-09-08-176 -- the trade-history estimate itself is NOT additionally
    # restricted to low-vol days, only the final exposure gate is).
    trade_ret = daily_ret.where(uptrend, other=pd.NA)

    weight = pd.Series(0.0, index=close.index)
    n = len(close)

    for i in range(n):
        if not bool(uptrend.iloc[i]) or not bool(low_vol_regime.iloc[i]):
            weight.iloc[i] = 0.0
            continue

        window_start = max(0, i - trade_history_window)
        # Strictly no-lookahead: only trades up to (not including) day i.
        hist = trade_ret.iloc[window_start:i].dropna()

        if len(hist) < min_trades_for_estimate:
            weight.iloc[i] = min(default_weight, leverage_cap)
            continue

        wins = hist[hist > 0]
        losses = hist[hist < 0]
        p = len(wins) / len(hist) if len(hist) else 0.0
        q = 1.0 - p
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = abs(losses.mean()) if len(losses) else 0.0
        b = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        if b <= 0:
            kelly_full = 0.0
        else:
            kelly_full = (b * p - q) / b

        target_w = kelly_fraction * kelly_full
        weight.iloc[i] = min(max(target_w, 0.0), leverage_cap)

    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (weight.shift(1).fillna(0.0) * daily_ret)
    return strategy_ret
