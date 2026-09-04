"""Strategy: Fair Value Gap (FVG) retracement entry, daily-bar adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-095):
ICT/smart-money-concepts "Fair Value Gap" (FVG): a 3-bar price imbalance
where bar[t]'s low > bar[t-2]'s high (bullish FVG, aggressive up-move
skipping a price zone). Source rules: only trade FVGs aligned with the
higher-timeframe trend (adapted here to a 200-day SMA trend filter on daily
bars, since this repo has no intraday data); enter on a retracement back to
the gap's 50% midpoint; stop below the gap's outer extreme (bar[t-2]'s
high, i.e. below the whole imbalance zone) with a small buffer; exit at a
fixed 1:2 risk:reward target (distance from entry to stop, doubled).
Hypothesis: the imbalance-then-retracement pattern marks genuine
institutional order-flow footprints that get "filled" (retested) before
continuing, giving a tradeable, risk-defined long setup in an uptrend.

Signal logic
------------
- Bullish FVG at index i (i>=2): low[i] > high[i-2] (a 3-candle
  imbalance/gap between candle i-2's high and candle i's low).
- Gap zone: [high[i-2], low[i]]; midpoint = (high[i-2] + low[i]) / 2.
- Trend filter: close[i] > SMA(trend_window)[i] (only trade FVGs formed in
  an uptrend, per source's context-filter rule).
- Entry: on any subsequent day (within fvg_expiry_days of formation) where
  price retraces down and touches the midpoint (low[t] <= midpoint <=
  high[t]), enter long at the midpoint price.
- Stop-loss: high[i-2] * (1 - stop_buffer_pct) (just below the gap's outer
  extreme, i.e. candle i-2's high).
- Take-profit: entry + reward_multiple * (entry - stop) (fixed R:R, default
  2:1 per source's "1:2 risk:reward" guidance).
- Exit: whichever of stop-loss / take-profit is hit first on a later bar
  (checked via high/low touch), or a max_hold_days time-stop if neither
  triggers.
- Only one open trade at a time (skip new FVG signals while already in a
  position) -- keeps the daily-bar approximation tractable and avoids
  overlapping-trade accounting complexity.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _simulate(
    price_df: pd.DataFrame,
    trend_window: int,
    fvg_expiry_days: int,
    stop_buffer_pct: float,
    reward_multiple: float,
    max_hold_days: int,
):
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    position = pd.Series(0, index=df.index, dtype=int)
    trade_returns = pd.Series(0.0, index=df.index)

    # Precompute bullish FVG candidates: gap between high[i-2] and low[i]
    is_fvg = pd.Series(False, index=df.index)
    for i in range(2, n):
        if low.iloc[i] > high.iloc[i - 2]:
            is_fvg.iloc[i] = True

    in_trade = False
    pending_fvgs = []  # list of (formed_idx, gap_low_bound, gap_mid)

    i = 0
    while i < n:
        if not in_trade:
            # register any newly-formed FVG (in an uptrend) as pending
            if bool(is_fvg.iloc[i]) and pd.notna(trend_sma.iloc[i]) and close.iloc[i] > trend_sma.iloc[i]:
                gap_low_bound = high.iloc[i - 2]
                gap_high_bound = low.iloc[i]
                mid = (gap_low_bound + gap_high_bound) / 2.0
                pending_fvgs.append((i, gap_low_bound, mid))

            # drop expired pending FVGs
            pending_fvgs = [p for p in pending_fvgs if i - p[0] <= fvg_expiry_days]

            # check for a retracement touch on this bar for any pending FVG
            triggered = None
            for (formed_idx, gap_low_bound, mid) in pending_fvgs:
                if formed_idx == i:
                    continue  # can't retrace into the gap the same bar it forms
                if low.iloc[i] <= mid <= high.iloc[i]:
                    triggered = (gap_low_bound, mid)
                    break

            if triggered is not None:
                gap_low_bound, mid = triggered
                entry_price = mid
                stop_price = gap_low_bound * (1 - stop_buffer_pct)
                risk = entry_price - stop_price
                if risk > 0:
                    target_price = entry_price + reward_multiple * risk
                    in_trade = True
                    pending_fvgs = []
                    entry_idx = i
                    position.iloc[i] = 1

                    # simulate forward to find exit
                    exit_i = None
                    exit_price = None
                    for j in range(i + 1, min(n, i + 1 + max_hold_days)):
                        position.iloc[j] = 1
                        if low.iloc[j] <= stop_price:
                            exit_i, exit_price = j, stop_price
                            break
                        if high.iloc[j] >= target_price:
                            exit_i, exit_price = j, target_price
                            break
                    if exit_i is None:
                        exit_i = min(n - 1, i + max_hold_days)
                        exit_price = close.iloc[exit_i]
                    trade_ret = (exit_price / entry_price) - 1.0
                    trade_returns.iloc[exit_i] += trade_ret
                    if exit_i < n:
                        for j in range(i, exit_i):
                            position.iloc[j] = 1
                        position.iloc[exit_i] = 0
                    in_trade = False
                    i = exit_i
        i += 1

    return position, trade_returns


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    fvg_expiry_days: int = 10,
    stop_buffer_pct: float = 0.005,
    reward_multiple: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    position, _ = _simulate(price_df, trend_window, fvg_expiry_days, stop_buffer_pct, reward_multiple, max_hold_days)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    fvg_expiry_days: int = 10,
    stop_buffer_pct: float = 0.005,
    reward_multiple: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Trade-level returns booked on the exit day (no transaction costs)."""
    _, trade_returns = _simulate(price_df, trend_window, fvg_expiry_days, stop_buffer_pct, reward_multiple, max_hold_days)
    return trade_returns
