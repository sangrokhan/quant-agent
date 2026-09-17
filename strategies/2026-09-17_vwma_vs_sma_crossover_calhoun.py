"""Strategy: Volume-Weighted Moving Average vs Simple Moving Average
crossover (Ken Calhoun, TASC Feb 2017 article / Apr 2017 Traders Tips code).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-142):
Per Ken Calhoun's "Volume-Weighted Moving Average Breakouts" (TASC Feb 2017;
TradeStation EasyLanguage code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2017/04/TradersTips.html),
a VWMA(vwma_length) -- rolling sum(price*volume)/sum(volume), source's own
"_MovingAvgVolumeWeighted" function -- is compared against a plain
SMA(ma_length) of the SAME price series, with the source's own default
lengths (VWMA=50, SMA=70, i.e. the volume-weighted line is FASTER than the
plain SMA). Source's own mechanical rule: buy when VWMA crosses over the
SMA, sell when VWMA crosses under. This is a genuinely distinct
construction from this repo's existing VWMA(10) vs VWMA(100) dual-VWMA
crossover (2026-09-04-060, accepted QQQ+SPY) -- here only ONE line is
volume-weighted (the faster one) while the slower line is a plain
unweighted SMA, so the crossover signal captures divergence between
volume-weighted and volume-blind price averages specifically (a proxy for
"is the recent move backed by volume conviction relative to unweighted
trend"), not just two volume-weighted lines at different speeds.

Signal logic
------------
- vwma = rolling sum(close*volume, vwma_length) / rolling sum(volume,
  vwma_length).
- sma = SMA(close, ma_length).
- Entry (long): vwma crosses over sma (source's own rule).
- Exit: vwma crosses back under sma (source's own rule), OR a
  max_hold_days time-stop (this repo's safety valve, substituting the
  source's fixed-dollar stop/trailing-stop which isn't replicable with
  OHLCV-only bars).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
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
    vwma_length: int = 50,
    ma_length: int = 70,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    pv_sum = (close * volume).rolling(vwma_length).sum()
    v_sum = volume.rolling(vwma_length).sum()
    vwma = pv_sum / v_sum.replace(0.0, float("nan"))

    sma = close.rolling(ma_length).mean()

    cross_over = (vwma > sma) & (vwma.shift(1) <= sma.shift(1))
    cross_under = (vwma < sma) & (vwma.shift(1) >= sma.shift(1))

    entry = cross_over.fillna(False)
    exit_signal = cross_under.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
