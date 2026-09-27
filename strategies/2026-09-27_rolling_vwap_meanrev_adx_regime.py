"""Strategy: Rolling VWAP mean-reversion with ADX regime filter + rejection candle.

Hypothesis (source: https://crosstrade.io/learn/trading-strategies/vwap-reversion,
read 2026-09-27): fade price extensions away from VWAP back toward VWAP,
but ONLY in non-trending regimes (ADX(14) <= 25) and only after a rejection
candle confirms the extreme (long lower wick for longs). Source's original
construction is intraday session-VWAP on ES/NQ futures with a full Pine
Script v6 disclosed. This repo's data/loaders.py is daily-bar-only (no
intraday session data), so this is adapted to a ROLLING N-day
volume-weighted VWAP (and rolling std-dev bands) instead of a session-reset
VWAP, keeping the source's core mechanics: regime filter (ADX), 2-sigma
band extension trigger, rejection-candle confirmation, ATR-based stop,
VWAP-itself as the profit target.

First VWAP-reversion strategy in this repo (0 prior hits for
"vwap_reversion" in strategies_index.jsonl); distinct from prior VWAP-band
strategies (e.g. "vwbb_meanrev", "anchored_vwap_swinglow") because this adds
the source's specific ADX regime-filter + rejection-candle-trigger
combination rather than a raw band-touch entry.

Signal logic
------------
- Rolling VWAP over `vwap_window` days: sum(typical_price * volume) /
  sum(volume), where typical_price = (H+L+C)/3.
- Rolling std dev of (typical_price - vwap) over the same window ->
  lower_band = vwap - std_mult * std.
- ADX(14) <= adx_threshold => "good regime" (non-trending).
- Setup: low <= lower_band (price touched/pierced the lower band).
- Trigger (rejection candle): lower_wick > wick_body_mult * body AND
  close > open (bullish rejection bar).
- Entry: long on the bar AFTER the trigger bar closes (next-day open,
  matching source's "market order on the next bar open").
- Stop: entry_low - atr_mult * ATR(atr_window), evaluated at the trigger bar.
- Target: the rolling VWAP itself (source's own exit rule).
- max_hold_days time-stop as a repo-convention safety net (source's
  original is intraday EOD-flatten, no direct analog here).

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    prior_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prior_close).abs(),
            (df["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move
    tr = _true_range(df)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, pd.NA)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, pd.NA)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    std_mult: float = 2.0,
    adx_threshold: float = 25.0,
    wick_body_mult: float = 2.0,
    atr_window: int = 14,
    atr_mult: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    typical = (h + l + c) / 3.0
    pv = typical * v
    sum_pv = pv.rolling(vwap_window).sum()
    sum_v = v.rolling(vwap_window).sum()
    vwap = sum_pv / sum_v.replace(0, pd.NA)

    dev = typical - vwap
    std = dev.rolling(vwap_window).std()
    lower_band = vwap - std_mult * std

    adx = _adx(df, period=14)
    good_regime = adx <= adx_threshold

    body = (c - o).abs()
    lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l
    bullish_rejection = (lower_wick > wick_body_mult * body) & (c > o)

    setup = (l <= lower_band).fillna(False)
    trigger = setup & good_regime.fillna(False) & bullish_rejection.fillna(False)
    # Entry happens on the NEXT bar after the trigger bar closes.
    entry = trigger.shift(1).fillna(False)

    atr = _true_range(df).rolling(atr_window).mean()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop = 0.0
    target = 0.0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            hit_stop = bool(l.iloc[i] <= stop) if not pd.isna(l.iloc[i]) else False
            hit_target = bool(h.iloc[i] >= target) if not pd.isna(h.iloc[i]) else False
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) and i > 0:
                trig_i = i - 1
                trig_low = l.iloc[trig_i]
                trig_atr = atr.iloc[trig_i]
                trig_vwap = vwap.iloc[i]
                if pd.isna(trig_low) or pd.isna(trig_atr) or pd.isna(trig_vwap):
                    position.iloc[i] = 0
                    continue
                sp = trig_low - atr_mult * trig_atr
                ep = c.iloc[i]
                if ep <= sp or trig_vwap <= ep:
                    position.iloc[i] = 0
                    continue
                in_position = True
                entry_idx = i
                stop = sp
                target = trig_vwap
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
