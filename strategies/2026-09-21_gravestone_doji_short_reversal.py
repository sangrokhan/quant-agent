"""Strategy: Gravestone Doji bearish-reversal short, ATR stop/target exits.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-228):
Per PineScriptForge's "Gravestone Doji" strategy page
(https://pinescriptforge.com/strategy/gravestone-doji, read via browser_exec
this iteration -- web_extract's ddgs backend cannot extract page content, so
the fallback path was used directly): a Gravestone Doji has a long upper
shadow with open, close, AND low all at/near the session low -- price
pushed up intraday but sellers overwhelmed buyers by the close. At
resistance / after an uptrend this is described as "a powerful bearish
reversal signal". The source's own disclosed rules:
    ENTRY: "Enter short when Gravestone Doji forms at resistance or after
    an uptrend. Confirm with next candle."
    EXIT: "Target the nearest support level. Stop above the upper shadow.
    Risk 1x ATR."

This is the first Gravestone/Dragonfly Doji entry in this repo (0 prior
hits in strategies_index.jsonl for either -- Doji Reversal generically and
other single/multi-candle patterns like Hanging Man, Shooting Star, Morning
Star, Three Black Crows are all distinct shapes already tried). Distinct
from Hanging Man (2026-09-11-116, small body + long LOWER shadow, i.e. the
opposite shadow orientation) and from Shooting Star (small body near the
LOW of the range but NOT requiring open/close/low to all coincide at the
bar's low the way a true doji does).

Operationalization of the source's qualitative rules into numeric,
backtestable parameters:
  - Gravestone Doji shape: body (|close-open|) <= doji_body_max_pct of the
    bar's high-low range (near-equal open/close, the "doji" requirement);
    AND the lower shadow (min(open,close) - low) <= lower_shadow_max_pct of
    the range (open, close, AND low all near the bar's low, per source's
    explicit description); AND the upper shadow (high - max(open,close))
    >= upper_shadow_min_pct of the range (the "long upper shadow").
  - Context ("at resistance or after an uptrend"): close > SMA(trend_window)
    (uptrend proxy, consistent with this repo's other single-candle
    reversal strategies e.g. Hanging Man/Matching Low).
  - Confirmation ("confirm with next candle"): source doesn't specify the
    confirmation direction explicitly, but combined with a bearish-reversal
    thesis the natural mechanical reading is a bearish confirmation candle
    (close < open) within confirm_window bars after the doji, entering
    short at that candle's close.
  - Exit ("stop above the upper shadow, risk 1x ATR; target nearest
    support"): stop_price = doji bar's high (the top of the upper shadow)
    + atr_stop_mult * ATR(atr_period) computed at entry (source's "risk 1x
    ATR" sized off the stop-above-shadow level, atr_stop_mult=1.0 default
    reproduces the source's literal rule). "Nearest support" has no
    universal numeric definition, so it is operationalized as a fixed
    target_atr_mult * ATR profit target below the entry price (a common,
    source-consistent proxy for "the next support level" in ATR-based
    systems), with a max_hold_days time-stop as a final fallback exit if
    neither stop nor target is hit.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    doji_body_max_pct: float = 0.10,
    lower_shadow_max_pct: float = 0.10,
    upper_shadow_min_pct: float = 0.60,
    confirm_window: int = 3,
    atr_period: int = 14,
    atr_stop_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()
    uptrend = c > sma

    rng = (h - l).replace(0.0, 1e-12)
    body = (c - o).abs()
    lo_body = df[["open", "close"]].min(axis=1)
    hi_body = df[["open", "close"]].max(axis=1)
    lower_shadow = lo_body - l
    upper_shadow = h - hi_body

    is_gravestone = (
        (body / rng <= doji_body_max_pct)
        & (lower_shadow / rng <= lower_shadow_max_pct)
        & (upper_shadow / rng >= upper_shadow_min_pct)
    ).fillna(False)

    pattern_at_t = (uptrend.fillna(False) & is_gravestone).fillna(False)
    bearish_confirm = c < o

    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)

    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None
    pending_pattern_bar = None

    for i in range(n):
        if in_position:
            hit_stop = h.iloc[i] >= stop_price
            hit_target = l.iloc[i] <= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
            continue

        if pattern_at_t.iloc[i]:
            pending_pattern_bar = i

        if pending_pattern_bar is not None:
            bars_since = i - pending_pattern_bar
            if 0 < bars_since <= confirm_window:
                if bool(bearish_confirm.iloc[i]):
                    doji_bar = pending_pattern_bar
                    entry_atr = atr.iloc[i]
                    if pd.notna(entry_atr) and entry_atr > 0:
                        stop_price = h.iloc[doji_bar] + atr_stop_mult * entry_atr
                        target_price = c.iloc[i] - target_atr_mult * entry_atr
                        in_position = True
                        hold_days_left = max_hold_days
                        position.iloc[i] = -1
                        pending_pattern_bar = None
                        continue
                    pending_pattern_bar = None
            elif bars_since > confirm_window:
                pending_pattern_bar = None

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
