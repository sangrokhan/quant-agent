"""Strategy: Stan Weinstein Stage Analysis -- Stage 2 breakout long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-127):
Per Stan Weinstein's "Secrets For Profiting in Bull and Bear Markets" (Stage
Analysis), summarized at https://deepvue.com/indicators/stan-weinstein-stage-analysis/
(visited this iteration; AXLFI/EquityReads sources 404'd) and corroborated by
the Google AI-overview SERP synthesis of TraderLion/Equity Reads/TradingView/
AXLFI: stocks cycle through 4 stages defined by price action relative to
their 30-week moving average (~150 trading days, daily-bar proxy used here
since our loaders provide daily not weekly bars):
  - Stage 1 (Basing): price chops sideways, the 150d SMA is flat.
  - Stage 2 (Advance): price is above a RISING 150d SMA -- Weinstein's ideal
    buy zone, entered on a breakout above prior resistance (a rolling N-day
    high) with the 30-week MA already turning up.
  - Stage 3 (Topping) / Stage 4 (Decline): the mirror-image sell/short
    conditions -- not traded here (long-only, per this repo's convention).

Operationalized rule tested here:
  - Compute SMA(sma_window) (default 150, ~30 weeks of daily bars) and its
    slope over sma_slope_lookback bars.
  - "Stage 2 regime" = close > SMA AND SMA has risen over the slope lookback
    window (source's explicit "rising 30-week MA" requirement).
  - Entry (long): a fresh breakout -- close crosses above the rolling
    breakout_window-day high (Weinstein's "breakout above resistance... on
    strong volume", volume confirmation approximated/omitted here since the
    source's own volume multiple is not tied to a specific number) -- AND
    we are already in the Stage 2 regime.
  - Exit: close crosses back below the SMA (source's own stated Stage 2->3/4
    transition signal), OR the SMA itself stops rising (early warning of a
    Stage 3 top), OR a max_hold_days time-stop safety backstop (source gives
    no explicit hold-period rule, this repo's established convention).

Distinct from this repo's existing SMA-trend-filter strategies: no prior
entry uses a *rising-SMA-slope* Stage-2-style regime gate combined with a
breakout trigger specifically on a 150d/30-week SMA (existing 52-week-high
proximity momentum 2026-09-03-015 uses a flat 252d high/150d SMA EXIT only,
no rising-slope entry gate; existing SMA-crossover trend strategies use two
SMAs crossing, not a single-SMA-slope regime + breakout combo).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    sma_window: int = 150,
    sma_slope_lookback: int = 10,
    breakout_window: int = 50,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    sma_rising = sma > sma.shift(sma_slope_lookback)
    stage2_regime = (close > sma) & sma_rising.fillna(False)

    rolling_high = close.rolling(breakout_window).max().shift(1)
    breakout = close > rolling_high

    entry = breakout & stage2_regime
    exit_below_sma = close < sma
    exit_sma_flat_or_falling = ~sma_rising.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_below_sma.iloc[i])
                or bool(exit_sma_flat_or_falling.iloc[i])
                or held >= max_hold_days
            ):
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
