"""Strategy: Approximate-Entropy chaos-to-structure transition trend entry
("Predictability Emergence Trend"), with drift/EMA confirmation and ATR-based
stop/target/breakeven/trail risk management.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Algobot's "Predictability Emergence Trend" MetaTrader-5 EA documentation
(https://www.algobot.live/predictability-emergence-trend-ea-mt5/, read via
curl/regex-extract this iteration since the rendered page redirected to an
image in browser_exec and web_extract's ddgs backend cannot fetch content),
Approximate Entropy (ApEn, Pincus 1991) measured on a rolling window of
z-scored closes captures how "organised"/self-similar recent price action
is, independent of price level or volatility (thanks to the z-scoring).
A fresh down-cross of ApEn through a fixed threshold (ApEn was >= threshold
on the prior bar, now < threshold) signals the market just transitioned from
chaos/noise to structure -- historically a precursor to a tradable directional
move. Direction is taken from the least-squares regression slope of closes
over the same short lookback, confirmed by price vs. a baseline EMA of the
same length (both must agree, else stand aside). This is the FIRST
Approximate-Entropy-based strategy in this repo (distinct from the existing
Hurst-exponent, DFA, and Shannon-entropy [2026-09-27, same cron trigger]
entries, which use different entropy/complexity estimators and different
entry triggers -- this one specifically fires on a fresh threshold
DOWN-CROSS, i.e. a transition event, not a continuously-gated regime).

Source disclosed no numeric backtest stats (marketing page for an MT5 EA
download, not a research paper) -- all default parameter VALUES below are
taken directly from the source's own documented defaults (EntropyWindow=30,
EmbedTolerance(r)=0.20, EntropyThreshold=0.55, SlopePeriod=12, AtrPeriod=14,
AtrStopMult=1.6, RewardRiskRatio=2.2, BreakevenAtr=1.0, TrailAtr=1.4), and
this repo's grid test (Step 6) supplies the empirical evidence the source
article omitted.

Approximate Entropy implementation notes
-----------------------------------------
ApEn(m, r, N) with embedding dimension m=2 (standard default), computed on
the z-scored close window: for each window length m and m+1, count how many
pairs of length-m subsequences are within tolerance r (Chebyshev/max-norm)
of each other, average the log of that fraction across all subsequences
(phi(m)), then ApEn = phi(m) - phi(m+1). This is the same construction cited
by the source (Pincus 1991) and by this repo's `entropy` window standard
formula elsewhere. Note this is O(n^2) per window and can be slow for very
large windows -- kept to the source's own small default (window=30).

Signal logic
------------
- Rolling z-score the close series within each `entropy_window`-bar window,
  compute ApEn(m=2, r=embed_tolerance) on that window.
- Entry signal (long or short) arms when ApEn crosses from >= entropy_threshold
  (prior bar) to < entropy_threshold (current bar).
- Direction: least-squares slope of raw close over the trailing
  `slope_period` bars; long if slope > 0 AND close > EMA(slope_period), short
  if slope < 0 AND close < EMA(slope_period) (this repo trades long-only, so
  the short case is simply "stay flat" -- no short-selling per SAFETY.md
  scope; only the long side is implemented as an actual position).
- Exit: ATR-based stop (entry - atr_stop_mult*ATR) / take-profit
  (entry + reward_risk_ratio*atr_stop_mult*ATR), with breakeven lock once
  price advances breakeven_atr*ATR (stop moves to entry), then an ATR
  trailing stop at trail_atr*ATR once breakeven is reached. All computed on
  daily bars (this repo's data/loaders.py provides daily OHLCV, not the
  M15-H1 intraday bars the source recommends -- noted as a scope difference
  in the log entry's notes).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept params as keyword arguments per Step 5 of RESEARCH_LOOP.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _approx_entropy(window: np.ndarray, m: int, r: float) -> float:
    """Approximate Entropy (Pincus 1991) of a z-scored window, embedding dim m."""
    n = len(window)
    if n < m + 2:
        return np.nan

    def _phi(m_dim: int) -> float:
        templates = np.array([window[i : i + m_dim] for i in range(n - m_dim + 1)])
        count = len(templates)
        if count < 2:
            return 0.0
        # Chebyshev distance between all pairs
        diffs = np.max(np.abs(templates[:, None, :] - templates[None, :, :]), axis=2)
        matches = (diffs <= r).sum(axis=1)  # includes self-match
        c = matches / count
        c = c[c > 0]
        return float(np.mean(np.log(c)))

    try:
        phi_m = _phi(m)
        phi_m1 = _phi(m + 1)
    except Exception:
        return np.nan
    return phi_m - phi_m1


def _compute_apen_series(
    close: pd.Series, entropy_window: int, embed_tolerance: float, embed_dim: int = 2
) -> pd.Series:
    def _apply(w: pd.Series) -> float:
        arr = w.values
        std = arr.std()
        if std == 0 or np.isnan(std):
            return np.nan
        z = (arr - arr.mean()) / std
        return _approx_entropy(z, embed_dim, embed_tolerance)

    return close.rolling(entropy_window).apply(_apply, raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    entropy_window: int = 30,
    embed_tolerance: float = 0.20,
    entropy_threshold: float = 0.55,
    slope_period: int = 12,
    atr_period: int = 14,
    atr_stop_mult: float = 1.6,
    reward_risk_ratio: float = 2.2,
    breakeven_atr: float = 1.0,
    trail_atr: float = 1.4,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    apen = _compute_apen_series(close, entropy_window, embed_tolerance)
    apen_prev = apen.shift(1)
    entropy_downcross = (apen_prev >= entropy_threshold) & (apen < entropy_threshold)

    # least-squares slope over trailing slope_period bars
    x = np.arange(slope_period)

    def _slope(w: pd.Series) -> float:
        y = w.values
        if np.any(np.isnan(y)):
            return np.nan
        A = np.vstack([x, np.ones(len(x))]).T
        m_, _ = np.linalg.lstsq(A, y, rcond=None)[0]
        return m_

    slope = close.rolling(slope_period).apply(_slope, raw=False)
    baseline_ema = close.ewm(span=slope_period, adjust=False).mean()

    long_entry_signal = entropy_downcross & (slope > 0) & (close > baseline_ema)

    # ATR (Wilder-style simple rolling mean of true range)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_price = None
    stop_price = None
    take_profit = None
    breakeven_hit = False

    closes = close.values
    highs = high.values
    lows = low.values
    atrs = atr.values
    entries = long_entry_signal.values

    for i in range(len(close)):
        if in_pos:
            atr_i = atrs[i]
            # update breakeven / trail
            if not breakeven_hit and atr_i is not None and not np.isnan(atr_i):
                if closes[i] >= entry_price + breakeven_atr * atr_i:
                    breakeven_hit = True
                    stop_price = max(stop_price, entry_price)
            if breakeven_hit and atr_i is not None and not np.isnan(atr_i):
                trail_level = closes[i] - trail_atr * atr_i
                stop_price = max(stop_price, trail_level)

            exit_now = (lows[i] <= stop_price) or (highs[i] >= take_profit)
            if exit_now:
                in_pos = False
                position.iloc[i] = 0
                entry_price = None
                stop_price = None
                take_profit = None
                breakeven_hit = False
            else:
                position.iloc[i] = 1
        else:
            if bool(entries[i]) and not np.isnan(atrs[i]):
                in_pos = True
                entry_price = closes[i]
                stop_price = entry_price - atr_stop_mult * atrs[i]
                take_profit = entry_price + reward_risk_ratio * atr_stop_mult * atrs[i]
                breakeven_hit = False
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entropy_window: int = 30,
    embed_tolerance: float = 0.20,
    entropy_threshold: float = 0.55,
    slope_period: int = 12,
    atr_period: int = 14,
    atr_stop_mult: float = 1.6,
    reward_risk_ratio: float = 2.2,
    breakeven_atr: float = 1.0,
    trail_atr: float = 1.4,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        entropy_window=entropy_window,
        embed_tolerance=embed_tolerance,
        entropy_threshold=entropy_threshold,
        slope_period=slope_period,
        atr_period=atr_period,
        atr_stop_mult=atr_stop_mult,
        reward_risk_ratio=reward_risk_ratio,
        breakeven_atr=breakeven_atr,
        trail_atr=trail_atr,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
