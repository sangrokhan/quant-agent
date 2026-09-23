"""Strategy: McGinley Dynamic price-crossover trend-following with RSI>50
confirmation (long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per Angel One's McGinley Dynamic Indicator guide
(https://www.angelone.in/knowledge-center/online-share-trading/mcginley-dynamic-indicator):
the McGinley Dynamic (John R. McGinley, 1997) is an adaptive moving average
that self-adjusts its effective smoothing speed based on how far price has
diverged from its own prior value (via a 4th-power adaptive ratio term),
making it react faster during strong trends and slower/smoother during
consolidation than a fixed-period SMA/EMA. The source's own "Price
Crossover Strategy" + "McGinley Dynamic + RSI" composite rule: buy when
price crosses above the McGinley Dynamic line (confirmed by at least one
additional close above it) AND RSI is above 50 (momentum confirmation);
exit when price closes decisively back below the McGinley line. First
McGinley Dynamic entry in this repo (0 prior KB hits) -- distinct from
every existing SMA/EMA crossover strategy here because the McGinley line's
own smoothing speed is price-adaptive (self-regulating via the 4th-power
ratio), not a fixed-period average.

Signal logic (long side only)
------------------------------
- McGinley Dynamic (MD): MD_t = MD_{t-1} + (close_t - MD_{t-1}) /
  (k * N * (close_t / MD_{t-1})**4), seeded with MD_0 = close_0's rolling
  SMA(N) at the first valid bar. k=0.6 (McGinley's own recommended
  constant), N=`md_period`.
- Entry: close crosses above MD (close_t > MD_t AND close_{t-1} <= MD_{t-1})
  AND, `confirm_bars` bars later, close is still above MD (source's "at
  least one additional session closing above the line" confirmation) AND
  RSI(rsi_period) > `rsi_threshold` at the confirmation bar.
- Exit: close closes decisively below MD (close < MD * (1 - exit_buffer_pct)
  to avoid single-bar whipsaw noise around the line), or `max_hold_days`
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _mcginley_dynamic(close: pd.Series, n: int, k: float = 0.6) -> pd.Series:
    sma_seed = close.rolling(n).mean()
    md = pd.Series(index=close.index, dtype=float)
    seeded = False
    prev = None
    for i in range(len(close)):
        if not seeded:
            if pd.notna(sma_seed.iloc[i]):
                prev = sma_seed.iloc[i]
                md.iloc[i] = prev
                seeded = True
            continue
        c = close.iloc[i]
        if prev is None or prev == 0:
            md.iloc[i] = c
            prev = c
            continue
        ratio = c / prev
        denom = k * n * (ratio ** 4)
        if denom == 0 or pd.isna(denom):
            new_val = prev
        else:
            new_val = prev + (c - prev) / denom
        md.iloc[i] = new_val
        prev = new_val
    return md


def generate_signals(
    price_df: pd.DataFrame,
    md_period: int = 20,
    md_k: float = 0.6,
    confirm_bars: int = 1,
    rsi_period: int = 14,
    rsi_threshold: float = 50.0,
    exit_buffer_pct: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    md = _mcginley_dynamic(close, md_period, md_k)
    rsi = _rsi(close, rsi_period)

    above = (close > md).fillna(False)
    cross_up = above & (~above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_cond = (close.iloc[i] < md.iloc[i] * (1 - exit_buffer_pct)) or (held >= max_hold_days)
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        confirm_i = i - confirm_bars
        if confirm_i < 0:
            position.iloc[i] = 0
            continue
        if bool(cross_up.iloc[confirm_i]) and bool(above.iloc[i]) and rsi.iloc[i] > rsi_threshold:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
