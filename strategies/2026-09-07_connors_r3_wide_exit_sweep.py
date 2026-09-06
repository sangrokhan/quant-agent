"""Strategy: Connors R3 revisit -- wider exit_above sweep to confirm/refute the
sensitivity-swept near-miss rescue found in 2026-09-06-159.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-021):
The prior iteration (2026-09-06-159, rejected as a "near-miss") tested
Larry Connors' R3 strategy (3-day RSI(2) drop-sequence mean reversion,
close>SMA200 uptrend gate, entry when RSI<10 after the drop sequence,
exit when RSI>exit_above) with a grid over exit_above in a narrow range
around 70, and its own Step-7 parameter-sensitivity sweep (not part of the
original grid) found that widening exit_above to 75 alone pushed QQQ's
full-sample Sharpe from 0.892 (FAIL, exit_above=70) to 1.133 (PASS),
without needing a vol-regime gate. This iteration is a deliberate, focused
follow-up: re-run Step 6's grid with exit_above explicitly swept wider
(70/75/80/85) as a first-class grid dimension (not just a sensitivity
sweep afterthought), plus entry_below in a companion sweep, to confirm
this rescue holds up as this iteration's actual grid best_cell (not just
a manually-checked config), and to run the FULL Step 7 validator suite
(Sharpe/MDD/TC-survival/param-sensitivity/walk-forward-if-available) on
whatever the grid's own best_cell turns out to be, closing out the loose
end explicitly flagged in 2026-09-06-159's notes field.

Logic is IDENTICAL to 2026-09-06_connors_r3_rsi_dropseq.py (same source:
https://www.quantifiedstrategies.com/larry-connors-r3-strategy/, Ch.4
"High Probability ETF Trading", 2009) -- this file exists as a separate,
independently-loggable knowledge-base entry for the wider-grid
confirmation run, per RESEARCH_LOOP.md's novelty-check guidance that a
"meaningfully varying" revisit (here: a parameter regime specifically
targeting the prior rejection reason) is a valid non-duplicate iteration.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    trend_window: int = 200,
    first_drop_below: float = 60.0,
    entry_below: float = 10.0,
    exit_above: float = 75.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rsi_drop = rsi.diff() < 0
    three_day_drop_seq = rsi_drop & rsi_drop.shift(1) & rsi_drop.shift(2)
    first_drop_start_level = rsi.shift(2)
    first_drop_ok = first_drop_start_level < first_drop_below

    entry = (
        uptrend.fillna(False)
        & three_day_drop_seq.fillna(False)
        & first_drop_ok.fillna(False)
        & (rsi < entry_below).fillna(False)
    )
    exit_signal = rsi > exit_above

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
