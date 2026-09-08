"""Strategy: Rolling VWAP trend-continuation pullback ("buy the dip to VWAP").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-128):
Per https://forextester.com/blog/vwap/ ("Context: intraday uptrend. Price
rides above a rising Volume Weighted Average Price. Entry: wait for a clean
retrace to the VWAP line ... Stop: a few ticks below the recent swing low or
below the lower VWAP band (-1 sigma)"), when price is in an established
uptrend above a RISING rolling VWAP, a pullback that touches/dips to the
VWAP line and then closes back above it is a trend-continuation long entry
(buying the dip to fair value), not a mean-reversion trade against the
trend. This is economically and mechanically DISTINCT from every other VWAP
strategy already tested in this repo:
  - 2026-09-04-052 (rejected, decisive): VWAP +/- n*sigma BAND mean-reversion
    (buy when price falls BELOW the lower band -- a stretch/extreme-touch
    counter-trend trade).
  - 2026-09-04-138 (rejected, near-miss)/2026-09-06-164 (accepted, SPY only
    w/ ATR stop): Anchored VWAP re-anchored at rolling swing lows, price
    CROSSING ABOVE/BELOW the AVWAP line (a crossover/regime-flip signal).
Here the VWAP line itself must already be RISING (trend filter) and price
must already be ABOVE it (uptrend confirmed) -- the entry trigger is a
pullback TOUCH of the still-rising VWAP followed by a recovery close back
above it, i.e. "buy support in an uptrend", the classic pullback-entry
pattern (cf. Keltner-middle-line pullback 2026-09-06-136, rejected on
TC-survival) applied to a volume-weighted average instead of an EMA.

Signal logic
------------
- Rolling VWAP over `vwap_window` days: sum(close*volume)/sum(volume).
- Trend filter: VWAP is "rising" when VWAP[t] > VWAP[t - trend_lookback].
- Uptrend confirmed: close > VWAP AND VWAP rising, for at least 1 bar prior
  to the pullback (i.e. we were already in an established uptrend).
- Pullback + entry trigger: on a bar where the intrabar low pierces down to
  within `pullback_pct` of VWAP (low <= VWAP * (1 + pullback_pct)) while the
  close still finishes ABOVE VWAP (rejection/bounce, not a breakdown) and
  VWAP is still rising -> long entry at that bar's close.
- Exit: close crosses back below VWAP (trend violated), VWAP stops rising
  (slope turns non-positive), or after `max_hold_days` (avoid indefinite
  holds), whichever comes first.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    vwap_window: int = 20,
    trend_lookback: int = 5,
    pullback_pct: float = 0.005,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"]

    pv = (close * volume).rolling(vwap_window).sum()
    vsum = volume.rolling(vwap_window).sum()
    vwap = pv / vsum.replace(0, pd.NA)

    vwap_rising = vwap > vwap.shift(trend_lookback)
    uptrend = (close > vwap) & vwap_rising.fillna(False)

    pullback_touch = low <= (vwap * (1 + pullback_pct))
    bounce_confirm = close > vwap

    entry = uptrend.fillna(False) & pullback_touch.fillna(False) & bounce_confirm.fillna(False)

    exit_trend_break = close < vwap
    exit_slope_flip = ~vwap_rising.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_slope_flip.iloc[i]) or held >= max_hold_days:
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
