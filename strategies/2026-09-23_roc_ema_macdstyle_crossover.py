"""Strategy: MACD-style smoothing applied directly to raw ROC (EMA-of-ROC crossover).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id): per
timinsight.com's "Price Rate of Change (ROC) Complete Guide"
(https://timinsight.com/price-rate-of-change-roc-guide-en, read via
browser_exec this iteration), "Strategy 4: Smoothed ROC Crossover System"
applies MACD-style smoothing directly to the raw ROC line itself (not to
price): compute a fast EMA and slow EMA of the ROC series, and trade the
crossover -- "golden cross (fast crosses above slow) -> Long, death cross
(fast crosses below slow) -> Short". This is structurally distinct from
every prior KST/Special-K/PMO/TCF strategy in this repo, all of which sum
multiple *separately-smoothed ROC legs at different lookback periods*
(Pring-style weighted composite); here there is only ONE underlying ROC
series (a single lookback period), and the "fast"/"slow" distinction comes
purely from applying two different EMA smoothing spans to that single ROC
series -- directly analogous to how MACD applies fast/slow EMAs to price,
but one level removed (applied to ROC instead of price). Trend-gated
long-only adaptation (close > SMA(trend_window)) added since the source's
short side isn't implementable cleanly in this repo's long/flat {0,1}
position contract.

Signal logic
------------
- roc = pct_change(close, roc_period) * 100.
- fast_ema = EMA(roc, fast_span); slow_ema = EMA(roc, slow_span).
- Entry (long): fast_ema crosses above slow_ema (golden cross) AND
  close > SMA(trend_window) (long-only trend gate, since we can't short).
- Exit: fast_ema crosses below slow_ema (death cross), OR the trend gate
  flips false, OR a max_hold_days time-stop.

Interface contract matches strategies/2026-09-03_bb_meanrev_qqq_volregime.py:
generate_signals(price_df, **params) -> pd.Series {0,1}
generate_returns(price_df, **params) -> pd.Series of daily strategy returns
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
    roc_period: int = 12,
    fast_span: int = 12,
    slow_span: int = 26,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = close.pct_change(roc_period) * 100.0
    fast_ema = roc.ewm(span=fast_span, adjust=False).mean()
    slow_ema = roc.ewm(span=slow_span, adjust=False).mean()

    sma_trend = close.rolling(trend_window).mean()
    trend_gate = close > sma_trend

    golden_cross = (fast_ema.shift(1) <= slow_ema.shift(1)) & (fast_ema > slow_ema)
    death_cross = (fast_ema.shift(1) >= slow_ema.shift(1)) & (fast_ema < slow_ema)

    entry_signal = golden_cross & trend_gate.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_cross = bool(death_cross.iloc[i]) if not pd.isna(death_cross.iloc[i]) else False
            trend_broke = not bool(trend_gate.iloc[i]) if not pd.isna(trend_gate.iloc[i]) else False
            if exit_cross or trend_broke or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
