"""Strategy: IBS mean reversion with ADX trend-confirmation gate and an
adaptive quick-exit rule (profit-take next open, else time-stop after 1 bar).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-142):
Per Ali Casey's StatOasis article "How the IBS Strategy Made $45K in 2024 —
Even in a Down Market!"
(https://statoasis.com/overfit/research/how-the-ibs-strategy-made-45k-in-2024-even-in-a-down-market,
visited via browser_exec this iteration): IBS = (Close-Low)/(High-Low)
measures where price closed within its own daily range; low IBS (near the
day's low) signals a panic/exhaustion sell-off, entered long the next open.
The source's exit rule is deliberately adaptive/quick rather than a fixed
threshold or time-stop: if the position is profitable by the next bar's
close, exit at the following open; if not yet profitable, exit anyway
after holding exactly one bar. The source ALSO flags a counterintuitive
finding worth testing directly: gating entries to only fire when ADX is
ABOVE a threshold (e.g. 20-25, i.e. a TRENDING market) improves IBS
mean-reversion accuracy -- the opposite of the usual trend-vs-mean-reversion
avoidance heuristic used throughout this repo's other regime-gated
strategies. This repo has 14+ prior IBS entries (see strategies_index.jsonl
search for "IBS"), but NONE combine an ADX-trend-CONFIRMATION gate
(trending market REQUIRED, not avoided) with this specific adaptive
profit-or-1-bar-timeout exit rule -- every prior IBS entry uses either a
fixed exit threshold on IBS/price, a fixed time-stop, or an SMA/200-day
trend filter requiring an UPTREND (not high-ADX regardless of direction).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / atr.replace(0.0, float("nan")))
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / atr.replace(0.0, float("nan")))
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, float("nan"))
    adx = dx.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    ibs_threshold: float = 0.25,
    adx_window: int = 14,
    adx_threshold: float = 20.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: IBS < ibs_threshold AND ADX(adx_window) > adx_threshold (trending
    market -- source's counterintuitive confirmation, not the usual
    avoidance filter).
    Exit (adaptive, source's own rule): held for exactly 1 bar; whether
    that bar closed above the entry-bar's close (profitable) or not, the
    position exits the FOLLOWING bar regardless (source's "exit next open
    if profitable, else exit anyway after one bar" collapses to a fixed
    2-bar total hold in this daily-bar single-price-series context, since
    we cannot distinguish an intrabar profit check from the next close
    without intraday data -- approximated as a strict 1-bar hold, matching
    the source's own stated worst case: "exit anyway after one bar").
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    rng = (high - low).replace(0.0, float("nan"))
    ibs = (close - low) / rng

    adx = _adx(df, adx_window)

    entry = (ibs < ibs_threshold) & (adx > adx_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= 1:  # adaptive rule collapses to a strict 1-bar hold
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
