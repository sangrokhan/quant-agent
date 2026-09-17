"""Strategy: Parabolic SAR + Dual Moving-Average Crossover confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-027):
Per tradingstrategyguides.com's "Parabolic SAR Moving Average Strategy - 6
Simple Rules" (https://tradingstrategyguides.com/parabolic-sar-moving-average-trade-strategy/,
visited this iteration via browser_exec after Google SERP fallback -- the
source's default settings are a fast 20-period MA and slow 40-period MA
overlaid with Wilder's Parabolic SAR (AF init 0.02, step 0.02, max 0.20)):
long entry requires BOTH (1) the PSAR dot flips from above-price to
below-price (bullish flip) AND (2) the 20-period MA is above the 40-period MA
(a "confirmed" reversal state -- either condition may occur first, but both
must hold), entered on the *next* bar's open after both conditions are first
simultaneously true. Exit on either the MA lines crossing back (20 crosses
below 40) or the PSAR dot flipping bearish again (source explicitly gives
both as valid exits -- this implementation exits on whichever comes first,
the more conservative "protective" choice), plus a max_hold_days time-stop
for safety.

This is distinct from every other Parabolic SAR variant already in this
repo (2026-09-04-042 plain PSAR+SMA(200) trend filter; 2026-09-05-062
DPO+DMI+PSAR triple-confirmation; 2026-09-06-093 PSAR-on-RSI; 2026-09-09-072/073
PSAR+ADX threshold gate) -- none of those use a dual-MA(fast/slow) crossover
as the confirming gate, which is this source's specific, fully disclosed
mechanism.

Signal logic
------------
- af_step / af_max: Wilder Parabolic SAR acceleration factor step/ceiling
  (source's stated defaults 0.02 / 0.20).
- fast_ma / slow_ma: the two SMA lengths (source's stated defaults 20 / 40).
- Long entry (next bar): PSAR bullish flip (dot moves from above to below
  price) has occurred AND fast_ma > slow_ma, both true as of the flip bar.
- Exit: fast_ma crosses back below slow_ma, OR PSAR flips bearish again,
  OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.20) -> pd.Series:
    """Classic Wilder Parabolic SAR. Returns the SAR value series."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(df)
    sar = np.empty(n, dtype=float)
    if n == 0:
        return pd.Series(sar, index=df.index)

    # Initialize: assume uptrend start, EP = first high, AF = af_step.
    uptrend = True
    af = af_step
    ep = high[0]
    sar[0] = low[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        if uptrend:
            cur_sar = prev_sar + af * (ep - prev_sar)
            cur_sar = min(cur_sar, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < cur_sar:
                uptrend = False
                cur_sar = ep
                ep = low[i]
                af = af_step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            cur_sar = prev_sar + af * (ep - prev_sar)
            cur_sar = max(cur_sar, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > cur_sar:
                uptrend = True
                cur_sar = ep
                ep = high[i]
                af = af_step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
        sar[i] = cur_sar

    return pd.Series(sar, index=df.index)


def _compute_state(
    df: pd.DataFrame, af_step: float, af_max: float, fast_ma: int, slow_ma: int
) -> pd.DataFrame:
    close = df["close"]
    sar = _parabolic_sar(df, af_step=af_step, af_max=af_max)
    psar_bullish = close > sar  # dot below price = bullish
    psar_flip_bullish = psar_bullish & (~psar_bullish.shift(1).fillna(False))
    psar_flip_bearish = (~psar_bullish) & (psar_bullish.shift(1).fillna(False))

    fast = close.rolling(fast_ma).mean()
    slow = close.rolling(slow_ma).mean()
    ma_bullish = fast > slow
    ma_cross_bearish = (~ma_bullish) & (ma_bullish.shift(1).fillna(False))

    out = pd.DataFrame(
        {
            "psar_bullish": psar_bullish,
            "psar_flip_bullish": psar_flip_bullish,
            "psar_flip_bearish": psar_flip_bearish,
            "ma_bullish": ma_bullish,
            "ma_cross_bearish": ma_cross_bearish,
        },
        index=df.index,
    )
    return out


def generate_signals(
    price_df: pd.DataFrame,
    af_step: float = 0.02,
    af_max: float = 0.20,
    fast_ma: int = 20,
    slow_ma: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    state = _compute_state(df, af_step, af_max, fast_ma, slow_ma)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            ma_exit = bool(state["ma_cross_bearish"].iloc[i]) if pd.notna(state["ma_cross_bearish"].iloc[i]) else False
            psar_exit = bool(state["psar_flip_bearish"].iloc[i]) if pd.notna(state["psar_flip_bearish"].iloc[i]) else False
            if ma_exit or psar_exit or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            # Entry condition true "as of" this bar: PSAR bullish AND MA fast>slow.
            # We require the state to have just become jointly true (either the PSAR
            # flip happened this bar with MA already bullish, or MA just turned
            # bullish with PSAR already bullish) -- entered on the SAME index here,
            # with generate_returns applying the standard next-bar shift for
            # realistic (no-lookahead) execution.
            psar_ok = bool(state["psar_bullish"].iloc[i]) if pd.notna(state["psar_bullish"].iloc[i]) else False
            ma_ok = bool(state["ma_bullish"].iloc[i]) if pd.notna(state["ma_bullish"].iloc[i]) else False
            just_flipped_psar = bool(state["psar_flip_bullish"].iloc[i]) if pd.notna(state["psar_flip_bullish"].iloc[i]) else False
            ma_prev_ok = bool(state["ma_bullish"].shift(1).iloc[i]) if i > 0 and pd.notna(state["ma_bullish"].shift(1).iloc[i]) else False
            just_flipped_ma = ma_ok and not ma_prev_ok
            entry_now = psar_ok and ma_ok and (just_flipped_psar or just_flipped_ma)
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    af_step: float = 0.02,
    af_max: float = 0.20,
    fast_ma: int = 20,
    slow_ma: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        af_step=af_step,
        af_max=af_max,
        fast_ma=fast_ma,
        slow_ma=slow_ma,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
