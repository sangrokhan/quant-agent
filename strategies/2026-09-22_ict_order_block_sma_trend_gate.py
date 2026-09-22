"""Strategy: ICT Order Block retrace + SMA(200) trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-047):
Second rescue attempt for this cron trigger's ICT Order Block family
(2026-09-22-045 rejected on decisive MDD; 2026-09-22-046's per-trade
formation-price stop-loss rescue failed to fix it -- root cause flagged in
that entry's notes was that drawdown accumulates from a SERIES of trades
during a sustained adverse regime, not any single trade, and the grid showed
0/36 high-vol-tercile cells ever passing). This sub-iteration instead gates
NEW entries to only fire when close > SMA(trend_window) (this repo's
standard trend-regime-gate construction, reused unchanged from
strategies/2026-09-03_bb_meanrev_qqq_volregime.py's sibling pattern and
strategies/2026-09-08_formation_price_stoploss_trend.py), addressing the
root cause directly: block new order-block entries during established
downtrends/high-vol regimes rather than trying to cap each trade's own loss.
No new external research this sub-iteration -- same underlying entry
mechanism and source (Ali Casey StatOasis ICT study,
https://statoasis.com/overfit/research/ict-backtest-what-survives) as
2026-09-22-045, with an added portfolio-level regime filter.

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
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(df_in := price_df)
    n = len(df)
    open_ = df["open"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    atr = _atr(df, atr_window).values

    sma = df["close"].rolling(trend_window).mean()
    uptrend = (df["close"] > sma).values

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

    for i in range(n):
        while zone_ptr < len(confirmed_zones) and confirmed_zones[zone_ptr][0] <= i:
            _, zlo, zhi, exp = confirmed_zones[zone_ptr]
            active_zones.append((zlo, zhi, exp))
            zone_ptr += 1
        active_zones = [z for z in active_zones if z[2] >= i]

        if in_position:
            held = i - entry_idx
            trend_flip = not bool(uptrend[i]) if not pd.isna(uptrend[i]) else False
            time_exit = held >= hold_days
            if trend_flip or time_exit:
                in_position = False
                entry_idx = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        if not bool(uptrend[i]) if not pd.isna(uptrend[i]) else True:
            position.iloc[i] = 0
            continue

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
