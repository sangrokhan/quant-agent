"""Strategy: Z-score-confirmed range-box breakout.

Hypothesis (knowledge_base id TBD, this iteration):
Per TheIndicatorLab's review of "Z_Score_Range_Boxes_Breakout"
(https://theindicatorlab.com/reviews/z-score-range-boxes-breakout/, read
via browser_exec this iteration -- web_search backend intermittently
failing so browser fallback used): a rolling z-score of close (vs its own
rolling mean/std over `box_window` bars) is used to detect volatility
COMPRESSION -- periods where |z| stays inside a tight deadband for at least
`min_compression_bars` bars form a "box" (its high/low = the range of close
over that compression window). A breakout signal fires only when BOTH (a)
price closes outside that box's high/low AND (b) the z-score on the
breakout bar itself is a statistical outlier beyond +/-`z_threshold`
(disclosed range 1.5-2.0). This differs from a plain Donchian-channel
breakout (already tested/rejected many times in this repo, e.g.
2026-09-04_donchian_breakout_trend.py) by requiring the box to have first
formed during a genuine low-volatility (z-compressed) regime, and by
requiring statistical significance on the breakout bar rather than a bare
price cross -- the source's own claim is this filters out breakouts fired
in already-choppy/high-vol conditions that a plain channel breakout would
false-signal on.

Signal logic
------------
- Rolling z-score: z = (close - rolling_mean(box_window)) / rolling_std(box_window).
- Compression flag: |z| <= compression_z for at least `min_compression_bars`
  consecutive bars ending at bar t-1 (box has "formed").
- Box high/low = max/min(close) over the most recent compression run.
- Entry (long): a box exists (formed via the compression run above) AND
  close > box_high AND z on this bar >= z_threshold (statistically
  significant upside breakout).
- Exit: close reverts back inside the box (<= box_high), OR z reverts to
  within +/- exit_z of zero (mean-reversion back to baseline, per source's
  "trail using the zone as your guide... z-score mean-reverts toward zero"
  exit note), OR a max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals(price_df, **params) -> pd.Series {0,1};
generate_returns(price_df, **params) -> pd.Series of daily strategy returns.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    box_window: int = 30,
    compression_z: float = 0.75,
    min_compression_bars: int = 6,
    z_threshold: float = 1.75,
    exit_z: float = 0.25,
    max_hold_days: int = 15,
    vol_regime_gate: bool = False,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    vol_regime_gate (added in follow-up sub-iteration 2026-09-21-223, per
    parent entry 2026-09-21-195's own suggestion): when True, entries are
    additionally restricted to bars where trailing realized volatility is
    at/below its own trailing 1-year median (this repo's established
    low-vol-regime-gate construction, reused unchanged from
    strategies/2026-09-03_bb_meanrev_qqq_volregime.py), since the parent
    grid showed the box-breakout edge concentrated almost entirely in the
    low-vol tercile (31/36 low-vol cells passed vs 7/36 mid, 3/36 high).
    """
    import math
    import numpy as np

    df = _prep(price_df)
    close = df["close"]

    roll_mean = close.rolling(box_window).mean()
    roll_std = close.rolling(box_window).std()
    z = (close - roll_mean) / roll_std.replace(0, np.nan)

    compressed = z.abs() <= compression_z

    # Consecutive compressed-bar run length ending at each bar.
    run_len = pd.Series(0, index=close.index, dtype=int)
    cnt = 0
    for i in range(len(close)):
        if bool(compressed.iloc[i]) if pd.notna(compressed.iloc[i]) else False:
            cnt += 1
        else:
            cnt = 0
        run_len.iloc[i] = cnt

    box_formed = run_len >= min_compression_bars

    if vol_regime_gate:
        ratios = close / close.shift(1)
        daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
        realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
        vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
        low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)
    else:
        low_vol_regime = pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    box_high = None
    box_low = None
    active_box_high = None
    active_box_low = None

    closes = close.values
    z_vals = z.values
    box_formed_vals = box_formed.values
    run_len_vals = run_len.values
    low_vol_vals = low_vol_regime.values

    last_box_high = np.nan
    last_box_low = np.nan

    for i in range(len(close)):
        # Update "last formed box" range using the trailing compression run.
        if box_formed_vals[i]:
            run = int(run_len_vals[i])
            start = max(0, i - run + 1)
            window_closes = closes[start : i + 1]
            last_box_high = float(np.nanmax(window_closes))
            last_box_low = float(np.nanmin(window_closes))

        zi = z_vals[i]
        ci = closes[i]

        if in_position:
            held = i - entry_idx
            back_inside = (
                not np.isnan(active_box_high) and ci <= active_box_high
            )
            z_reverted = (not np.isnan(zi)) and abs(zi) <= exit_z
            regime_flip_exit = vol_regime_gate and not bool(low_vol_vals[i])
            if back_inside or z_reverted or held >= max_hold_days or regime_flip_exit:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            has_box = not np.isnan(last_box_high)
            breakout = (
                has_box
                and (not np.isnan(zi))
                and ci > last_box_high
                and zi >= z_threshold
                and bool(low_vol_vals[i])
            )
            if breakout:
                in_position = True
                entry_idx = i
                active_box_high = last_box_high
                active_box_low = last_box_low
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
