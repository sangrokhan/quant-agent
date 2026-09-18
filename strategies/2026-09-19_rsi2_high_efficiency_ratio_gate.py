"""Strategy: Connors RSI(2) mean-reversion gated by a HIGH Kaufman Efficiency
Ratio filter (counter-intuitive ER-direction finding).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-004):
Cesar Alvarez's "Efficiency Ratio and Mean Reversion"
(https://alvarezquanttrading.com/blog/efficiency-ratio-and-mean-reversion/,
read via browser_exec after web_search DDGS backend returned unusable
results this iteration) tested adding a Kaufman Efficiency Ratio (ER)
filter to his own mean-reversion strategy's setup day. His a priori
expectation (based on Perry Kaufman's own TASC article) was that LOW ER
(choppy, noisy price action) should favor mean reversion, but empirically
he found the OPPOSITE: filtering for HIGH ER (>= 20 on a 0-100 scale,
i.e. a comparatively clean/efficient recent price move rather than pure
noise) improved every major backtest metric (CAGR, MDD, Sharpe, avg %p/l)
on two independently tested mean-reversion portfolios (though it did not
help on a third). This strategy tests that counter-intuitive finding by
adding a `require ER(10) >= er_threshold` gate to this repo's own
already-accepted Connors RSI(2) mean-reversion strategy
(strategies/2026-09-03_rsi2_meanrev_trend200.py, id=2026-09-03-005): only
take an RSI(2) oversold-dip entry when the recent N-day price move has
been comparatively "clean" (high ER) rather than pure random noise (low
ER), on top of the existing 200-day SMA trend filter.

Efficiency Ratio (Kaufman):
    ER(n) = |close - close.shift(n)| / sum(|close.diff()|, n) * 100
    (0-100 scale; near 100 = a straight, efficient trend move; near 0 =
    pure noise/chop with no net progress despite lots of daily movement)

Signal logic
------------
- Same base rule as 2026-09-03-005: close > SMA(trend_window) (uptrend
  filter) AND RSI(rsi_window) <= rsi_entry (oversold dip) triggers a long
  entry; exit when close > SMA(exit_sma_window) OR the trend filter
  breaks.
- ADDED gate: entry additionally requires ER(er_window) >= er_threshold
  at the moment of the RSI trigger (the setup day, per Alvarez's exact
  methodology of evaluating ER "on the setup day").

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _efficiency_ratio(close: pd.Series, window: int) -> pd.Series:
    """Kaufman Efficiency Ratio, 0-100 scale."""
    net_change = (close - close.shift(window)).abs()
    total_movement = close.diff().abs().rolling(window).sum()
    er = 100.0 * (net_change / total_movement.replace(0.0, pd.NA))
    return er.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    rsi_entry: float = 5.0,
    trend_window: int = 200,
    exit_sma_window: int = 5,
    er_window: int = 10,
    er_threshold: float = 20.0,
) -> pd.Series:
    """Long-only {0,1} position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    trend_sma = close.rolling(trend_window).mean()
    exit_sma = close.rolling(exit_sma_window).mean()
    er = _efficiency_ratio(close, er_window)

    above_trend = (close > trend_sma).fillna(False)
    er_ok = (er >= er_threshold).fillna(False)
    entry_trigger = (above_trend & (rsi <= rsi_entry) & er_ok).fillna(False)
    exit_trigger = ((close > exit_sma) | (~above_trend)).fillna(True)

    in_position = False
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            if exit_vals[i]:
                in_position = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
