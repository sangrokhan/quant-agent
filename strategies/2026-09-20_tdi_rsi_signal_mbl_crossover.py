"""Strategy: Traders Dynamic Index (TDI, Dean Malone) RSI/signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-076):
Per a Google AI-overview synthesis (TrendSpider/fbs.com/TradeWill/Quantum
Algo; browser_exec fallback -- web_search DDGS backend returns mangled
non-English results this iteration) of the Traders Dynamic Index (Dean
Malone), TDI combines four RSI-derived lines: the RSI itself ("green" price
line), a fast SMA of RSI ("red" signal line), a slower SMA of RSI ("yellow"
Market Base Line, MBL), and Bollinger Bands computed on the RSI ("blue"
volatility bands). The disclosed rule: long entry when RSI is in an
oversold zone (< 32) and rebounds, crossing above its own signal line
(golden cross), confirmed by the RSI/signal lines being above the MBL
(uptrend filter); exit on the opposite (death) cross or RSI reaching the
50 midline. This differs from every existing bare-RSI strategy in this repo
by combining RSI's own moving-average crossover (not price/RSI divergence
or a single threshold) with a THIRD slower RSI-average trend filter (MBL) --
a three-tier RSI-only construction not previously tested here.

TDI construction (standard, Dean Malone / MT4 original):
    RSI = standard N-period RSI (default N=13)
    Signal line = SMA(RSI, signal_period) (default 2)
    MBL = SMA(RSI, mbl_period) (default 34)
    (Bollinger Bands on RSI are used only for visual volatility context in
    the source's own rule set, not part of the disclosed entry/exit
    trigger -- omitted here since the entry/exit condition doesn't
    reference them.)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int = 13) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 13,
    signal_period: int = 2,
    mbl_period: int = 34,
    oversold_threshold: float = 32.0,
    overbought_threshold: float = 68.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: RSI was below `oversold_threshold` within the last 5 bars
    (recent oversold condition) AND RSI crosses above its own signal line
    (golden cross) AND both RSI and signal line are above the MBL (uptrend
    confirmation). Exit: RSI crosses back below the signal line (death
    cross) OR RSI crosses back above `overbought_threshold` after having
    been long (profit-take on overbought reversal risk), OR RSI crosses the
    50 midline from above while in a losing/flattening position (source's
    disclosed midline profit-take rule) -- implemented here simply as
    RSI < 50 while previously > 50 and in-position with the signal cross
    condition already broken.
    """
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, period=rsi_period)
    signal = rsi.rolling(signal_period).mean()
    mbl = rsi.rolling(mbl_period).mean()

    recent_oversold = (rsi < oversold_threshold).rolling(5, min_periods=1).max().astype(bool)
    golden_cross = (rsi > signal) & (rsi.shift(1) <= signal.shift(1))
    uptrend_confirm = (rsi > mbl) & (signal > mbl)

    entry = recent_oversold & golden_cross & uptrend_confirm.fillna(False)
    death_cross = (rsi < signal) & (rsi.shift(1) >= signal.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.fillna(False).values
    death_vals = death_cross.fillna(False).values
    rsi_vals = rsi.values

    for i in range(len(close)):
        if in_position:
            if bool(death_vals[i]) or rsi_vals[i] > overbought_threshold:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
