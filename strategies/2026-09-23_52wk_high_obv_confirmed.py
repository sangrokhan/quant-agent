"""Strategy: 52-week-high nearness momentum, gated by OBV volume confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-133):
Combines two independently-researched signals already in this repo: (1) the
52-week-high nearness anchoring effect (George & Hwang 2004; accepted for
QQQ in strategies/2026-09-23_52wk_high_nearness_momentum.py, but a near-miss
on SPY), and (2) On-Balance Volume trend confirmation (Granville 1963; this
cron trigger's earlier iteration, strategies/2026-09-23_obv_sma_trend_rsi_gate.py,
rejected standalone on walk-forward but with the edge concentrated in
low/mid-vol equity). Per multiple SERP-corroborated sources this iteration
(Universidad Evangelica del Paraguay course notes and Instagram/QuanterLab
snippets on "52-week high + volume confirmation", read via browser_exec --
web_search DDGS/Yahoo backend TLS-errored on every query attempted; the
primary PDF source 404'd, so this hypothesis is grounded in the SERP's own
disclosed summary text plus this repo's own already-validated OBV and
52-week-high building blocks rather than fabricated parameters): requiring
OBV to be rising (above its own short SMA) at the moment of a 52-week-high
nearness breakout should filter out "hollow" breakouts on weak conviction
and reduce the whipsaw that caused the standalone nearness strategy's SPY
near-miss, without needing options/breadth data this repo doesn't have.

Signal logic
------------
- nearness = close / rolling_252d_high (as in the accepted nearness strategy).
- OBV = cumulative volume-direction sum (Granville); OBV rising = OBV above
  its own obv_sma_window-period SMA.
- Entry (long): nearness crosses above entry_threshold (default 0.95) AND
  OBV is rising (OBV > its own SMA) at that same bar.
- Exit: nearness falls below exit_threshold (default 0.85), OR OBV falls
  below its own SMA (volume confirmation breaks down), OR hold_days reached.

Interface contract matches strategies/2026-09-23_52wk_high_nearness_momentum.py:
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
    lookback_days: int = 252,
    entry_threshold: float = 0.95,
    exit_threshold: float = 0.85,
    hold_days: int = 126,
    obv_sma_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    nearness = close / rolling_high
    entry_cross = (nearness.shift(1) < entry_threshold) & (nearness >= entry_threshold)

    direction = close.diff().apply(lambda d: 1 if d > 0 else (-1 if d < 0 else 0))
    obv = (direction * volume).fillna(0).cumsum()
    obv_sma = obv.rolling(obv_sma_window).mean()
    obv_rising = obv > obv_sma

    entry = entry_cross & obv_rising.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            n = nearness.iloc[i]
            fell_below_exit = bool(n < exit_threshold) if not pd.isna(n) else False
            obv_broke_down = not bool(obv_rising.iloc[i]) if not pd.isna(obv_rising.iloc[i]) else False
            if fell_below_exit or obv_broke_down or held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False:
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
