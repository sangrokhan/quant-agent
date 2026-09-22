"""Strategy: ICT Order Block retrace + formation-price hard stop-loss rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-045/046):
Direct rescue attempt of this same cron trigger's own prior rejection
(2026-09-22-045, ICT Order Block retrace per Ali Casey StatOasis
https://statoasis.com/overfit/research/ict-backtest-what-survives). That
entry passed Sharpe/TC-survival/walk-forward/parameter-sensitivity on QQQ
but failed decisively on max-drawdown (0.364 vs 0.25 threshold) with zero
grid cells passing in the high-vol tercile -- a fixed-time-exit-only
construction has no defense against a sustained drawdown event. This
sub-iteration adds a fixed formation-price hard stop-loss overlay (this
repo's already-accepted mechanism from
strategies/2026-09-08_formation_price_stoploss_trend.py, per Han/Zhou/Zhu
"Taming Momentum Crashes", https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/)
on top of the UNCHANGED order-block entry/zone-retrace logic: exit
immediately if close falls more than `stop_loss_pct` below the trade's own
entry price, in addition to the existing fixed-time exit. No new external
research this sub-iteration (pure mechanism combination of two
already-sourced ideas from this repo's own knowledge base).

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
    stop_loss_pct: float = 0.08,
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

    confirmed_zones.sort(key=lambda z: z[0])
    zone_ptr = 0
    active_zones = []

    in_position = False
    entry_idx = None
    entry_price = None

    for i in range(n):
        while zone_ptr < len(confirmed_zones) and confirmed_zones[zone_ptr][0] <= i:
            _, zlo, zhi, exp = confirmed_zones[zone_ptr]
            active_zones.append((zlo, zhi, exp))
            zone_ptr += 1
        active_zones = [z for z in active_zones if z[2] >= i]

        if in_position:
            held = i - entry_idx
            stop_price = entry_price * (1.0 - stop_loss_pct)
            stopped_out = close[i] < stop_price
            time_exit = held >= hold_days
            if stopped_out or time_exit:
                in_position = False
                entry_idx = None
                entry_price = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        entered = False
        for zlo, zhi, exp in active_zones:
            if low[i] <= zhi and close[i] >= zlo:
                entered = True
                break
        if entered:
            in_position = True
            entry_idx = i
            entry_price = close[i]
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
