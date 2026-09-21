"""Strategy: Combined Keltner/Donchian breakout entry + ratcheting trailing
stop exit (per Antonacci & Concretum's "A Century of Profitable Industry
Trends", 2025 Charles H. Dow Award winner).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-033):
Per Concretum Research's blog post "Backtest a Profitable Trend-Following
Strategy using Python" (https://concretumgroup.substack.com/p/backtest-a-profitable-trend-following,
visited this iteration, browser_exec/Quantocracy mashup listing --
web_search DDGS backend TLS-erroring on every query attempted this
iteration), summarizing the academic paper "A Century of Profitable
Industry Trends" (Antonacci & Concretum, 2025 Charles H. Dow Award, tested
on Kenneth French US industry data 1926-2024, CAGR 18.2% vs 9.7%
buy-and-hold, Sharpe 1.39 vs 0.63, MDD 33% vs 84%):

Entry (breakout, "tighter of two bands"):
  UpperBand(t) = min(DonchianUp(20), KeltnerUp(20, k=2))
    where KeltnerUp = EMA(price, 20) + 2 * 1.4 * mean(|daily price change|, 20)
    (source's own disclosed ATR-proxy adjustment: since French's data is
    close-only with no OHLC, they use 1.4x the rolling mean absolute daily
    price change as an ATR(20) proxy -- this repo has real OHLC via
    data/loaders.py, so this adaptation uses actual ATR(20) computed from
    high/low/close directly instead of the proxy, which is a strict
    improvement given real OHLC is available)
  Long entry when close >= UpperBand(t-1) (source's own asymmetric
  20-day-up / 40-day-down bias, intentional to "stay long through moderate
  pullbacks").

Exit (ratcheting trailing stop, "never eases"):
  LowerBand(t) = max(DonchianDown(40), KeltnerDown(40, k=2))
  LongTrailingStop(t+1) = max(LongTrailingStop(t), LowerBand(t))
    (the stop only ever moves UP, never down, while a position is open)
  Position closes when close crosses below the (ratcheted) trailing stop.

Source's own paper used volatility-scaled position sizing across a
cross-sectional industry universe (out of scope for this repo's
single-symbol generate_returns_fn contract) -- this test isolates the
entry/exit TIMING mechanism only, applied long-only/full-size to a single
equity or crypto symbol, matching this repo's existing convention for
adapting multi-asset papers to single-symbol tests (e.g. GTAA/dual-momentum
entries 2026-09-11-037/041).

This is distinct from this repo's existing Keltner (16+ prior entries) and
Donchian/Turtle (20+ prior entries) families via the specific COMBINED
"tighter-of-two-bands" entry logic (not either indicator alone) plus the
ratcheting-never-eases trailing-stop exit built from the WIDER/slower
40-period bands (not a fixed ATR-multiple stop or a symmetric-window
crossover).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 40,
    keltner_mult: float = 2.0,
) -> pd.Series:
    """Combined Keltner/Donchian breakout entry ("tighter of two bands"),
    ratcheting-never-eases trailing-stop exit ("wider/slower of two
    bands"). Returns a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_entry = close.ewm(span=entry_window, adjust=False).mean()
    atr_entry = _atr(df, entry_window)
    keltner_up = ema_entry + keltner_mult * atr_entry
    donchian_up = close.rolling(entry_window).max()
    upper_band = pd.concat([donchian_up, keltner_up], axis=1).min(axis=1)

    ema_exit = close.ewm(span=exit_window, adjust=False).mean()
    atr_exit = _atr(df, exit_window)
    keltner_down = ema_exit - keltner_mult * atr_exit
    donchian_down = close.rolling(exit_window).min()
    lower_band = pd.concat([donchian_down, keltner_down], axis=1).max(axis=1)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    trailing_stop = float("-inf")
    in_position = False

    upper_prev = upper_band.shift(1)
    close_vals = close.values
    upper_prev_vals = upper_prev.values
    lower_vals = lower_band.values

    for i in range(n):
        c = close_vals[i]
        if c != c:  # NaN
            position.iloc[i] = 1 if in_position else 0
            continue
        if not in_position:
            up = upper_prev_vals[i]
            if up == up and c >= up:
                in_position = True
                trailing_stop = lower_vals[i] if lower_vals[i] == lower_vals[i] else float("-inf")
        else:
            lo = lower_vals[i]
            if lo == lo:
                trailing_stop = max(trailing_stop, lo)
            if c < trailing_stop:
                in_position = False
                trailing_stop = float("-inf")
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` scales the {0,1} position uniformly (default 1.0 =
    full-size, matching the original equity-only test); crypto retunes use
    a lower leverage_cap (e.g. 0.3) to control drawdown, following this
    repo's established leverage-cap-aware rescue pattern."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * leverage_cap) * daily_ret
    return strategy_ret
