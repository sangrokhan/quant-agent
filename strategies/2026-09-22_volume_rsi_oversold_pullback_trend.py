"""Strategy: Volume RSI (VoRSI) oversold pullback-in-uptrend, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-101):
Per QuantifiedStrategies.com's "Volume RSI Trading Strategy" article
(https://www.quantifiedstrategies.com/volume-rsi/), Volume RSI applies the
classic RSI formula to up-volume vs down-volume instead of price changes
(same VoRSI formula as this repo's existing 2026-09-09-098 50-line-crossover
strategy: VoRSI = 100 - 100/(1+VoRS), VoRS = avg_up_volume/avg_down_volume
over a lookback window). Source's own disclosed example rule is a distinct
MEAN-REVERSION construction, not a trend-following 50-line crossover:

    "Buy when: Close is above its 200-day moving average AND Volume RSI(10)
    drops below 25. Sell when: Volume RSI crosses above 55."

Source's own rationale: "During uptrends, sharp short-term drops with weak
volume often represent temporary pullbacks rather than trend reversals.
Volume RSI helps identify these spots."

This is distinct from this repo's existing VoRSI entries:
  - 2026-09-09-098 (50-line crossover, trend-following/momentum-style,
    entry on VoRSI crossing ABOVE 50 -- opposite mechanic, treats bullish
    volume-dominance itself as the signal)
  - 2026-09-14-188 (continuous sizing dial, no discrete threshold at all)
This strategy instead treats a DIP in bullish volume (VoRSI falling to an
oversold extreme <25) during an already-confirmed uptrend (close>SMA200) as
a buying opportunity -- a genuine mean-reversion-on-a-pullback mechanic with
different thresholds (25/55 vs 50/50) and an explicit trend-regime gate the
50-line-crossover version lacks.

Signal logic
------------
- up_volume[t] = volume[t] if close[t] > close[t-1] else 0
- down_volume[t] = volume[t] if close[t] < close[t-1] else 0
- avg_up = SMA(up_volume, window); avg_down = SMA(down_volume, window)
- VoRS = avg_up / avg_down (guarded against division by zero)
- VoRSI = 100 - 100 / (1 + VoRS)
- Trend filter: close > SMA(trend_window) (source uses 200)
- Entry (long): trend filter true AND VoRSI crosses from >=25 to <25
  (dips into oversold volume-weakness during confirmed uptrend)
- Exit: VoRSI crosses back above exit_threshold (55, source's exact rule),
  backstopped by a max_hold_days time-stop, or trend filter breaking.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_vorsi(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    price_change = close.diff()
    up_volume = volume.where(price_change > 0, 0.0)
    down_volume = volume.where(price_change < 0, 0.0)

    avg_up = up_volume.rolling(window).mean()
    avg_down = down_volume.rolling(window).mean()

    safe_down = avg_down.where(avg_down != 0, 1.0)
    vors = avg_up / safe_down
    vorsi = 100 - 100 / (1 + vors)
    vorsi = vorsi.where(avg_down != 0, 100.0)
    vorsi = vorsi.where(~((avg_down == 0) & (avg_up == 0)), 50.0)
    return vorsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 10,
    oversold_threshold: float = 25.0,
    exit_threshold: float = 55.0,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    vorsi = _compute_vorsi(close, volume, window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    below_os = vorsi < oversold_threshold
    entry_trigger = below_os & (~below_os.shift(1).fillna(False)) & uptrend
    exit_trigger = vorsi > exit_threshold

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days or not bool(uptrend.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
