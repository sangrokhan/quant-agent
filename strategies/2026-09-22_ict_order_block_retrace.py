"""Strategy: ICT "Order Block" retrace entry, long-only, fixed time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Per Ali Casey's StatOasis 648-backtest study "I Backtested ICT / Smart Money
Concepts -- What Survives" (https://statoasis.com/overfit/research/ict-backtest-what-survives,
read via browser_exec this iteration -- web_search DDGS backend TLS-errored on
all queries this iteration). Of the four codified ICT concepts (Order Block,
Fair Value Gap, Liquidity Sweep, Optimal Trade Entry), Order Block showed the
most structure: on SPY, 81.5% of its 18 parameter variants beat a
frequency-matched random-entry baseline, and it had the highest (though still
sub-significance) forward-return t-stat of the four (+1.22 at 5 days). The
source's own conclusion was that NONE of the four beat buy-and-hold on raw
net profit across all four index ETFs tested -- this repo tests the same
codified rule against this repo's own Sharpe/MDD/walk-forward/TC bar instead,
which is a different (often more tractable) hurdle than "beat buy-and-hold".

Signal logic (source's own codified definition)
-------------------------------------------------
- An "Order Block" candidate bar is a down-close bar (close < open).
- It is CONFIRMED if, within the next `confirm_bars` (K) trading days, price
  makes an up-impulse of at least `atr_mult` (M) x ATR(20) measured from the
  order-block bar's own low.
- Once confirmed, the order-block bar's own [low, high] range becomes a
  "zone". We enter long on the first later bar (within `zone_expiry_bars` of
  confirmation) whose LOW retraces back down into that zone
  (low <= zone_high) while still closing above the zone low (zone still
  holds as support, not broken).
- Exit: fixed time exit after `hold_days` bars (source's own standardized
  "protective time exit" methodology -- isolates entry quality, no
  discretionary trade management).
- Long-only, flat otherwise. Only one open position at a time (skip new
  entries while already in a trade).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int = 20) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    confirm_bars: int = 5,
    atr_mult: float = 1.0,
    atr_window: int = 20,
    zone_expiry_bars: int = 15,
    hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    n = len(df)
    open_ = df["open"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    atr = _atr(df, atr_window).values

    position = pd.Series(0, index=df.index, dtype=int)

    # Step 1: find candidate order-block bars (down-close) and confirm them.
    # confirmed_zones: list of (confirm_idx, zone_low, zone_high, expiry_idx)
    confirmed_zones = []
    for i in range(n):
        if not (close[i] < open_[i]):
            continue
        ob_low = low[i]
        ob_high = high[i]
        a = atr[i]
        if a is None or pd.isna(a) or a <= 0:
            continue
        target = ob_low + atr_mult * a
        confirm_idx = None
        end_k = min(n, i + 1 + confirm_bars)
        for j in range(i + 1, end_k):
            if high[j] >= target:
                confirm_idx = j
                break
        if confirm_idx is not None:
            expiry_idx = min(n - 1, confirm_idx + zone_expiry_bars)
            confirmed_zones.append((confirm_idx, ob_low, ob_high, expiry_idx))

    # Step 2: walk forward, single position at a time, enter on first
    # retrace into an active (unexpired) zone, hold for hold_days.
    in_position = False
    entry_idx = None
    # Sort zones by confirm_idx to process chronologically.
    confirmed_zones.sort(key=lambda z: z[0])
    zone_ptr = 0
    active_zones = []  # list of (zone_low, zone_high, expiry_idx)

    for i in range(n):
        # Activate any zones confirmed as of bar i.
        while zone_ptr < len(confirmed_zones) and confirmed_zones[zone_ptr][0] <= i:
            _, zlo, zhi, exp = confirmed_zones[zone_ptr]
            active_zones.append((zlo, zhi, exp))
            zone_ptr += 1
        # Drop expired zones.
        active_zones = [z for z in active_zones if z[2] >= i]

        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        # Look for entry: low retraces into any active zone, close still above zone low.
        entered = False
        for zlo, zhi, exp in active_zones:
            if low[i] <= zhi and close[i] >= zlo:
                entered = True
                break
        if entered:
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
