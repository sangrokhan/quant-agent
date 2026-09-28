"""Strategy: Donchian breakout entry, exited by Marcos Lopez de Prado's
Triple Barrier Method (volatility-scaled take-profit/stop-loss + a vertical
time barrier) rather than a generic trailing stop / fixed time-stop.

Hypothesis (first Triple Barrier Method strategy in this repo -- 0 prior
hits in strategies_index.jsonl for "triple_barrier"/"meta_labeling"):
An N-day-high Donchian breakout (already accepted in this repo for
trend-following entries, e.g. 2026-09-03-008/2026-09-04-054) captures a
genuine entry edge, but a fixed-% or generic trailing-stop exit throws away
information about *current* volatility. Per the Triple Barrier Method
(Lopez de Prado, "Advances in Financial Machine Learning"; corroborated by
Google AI-overview summary of Interactive Brokers / LinkedIn (Arjun
Bhandari) / Medium sources on 2026-09-28, since the direct IBKR campus URL
404'd on fetch): setting BOTH take-profit and stop-loss as
entry_price * (1 +/- theta * sigma_t0), where sigma_t0 is the realized
daily-return volatility estimated AT ENTRY (not a static % or ATR-multiple
computed once historically), should adapt the exit distance to prevailing
volatility and improve on a static-%-exit Donchian breakout by avoiding
premature stops in high-vol regimes and giving back less profit in low-vol
regimes. A fixed vertical (time) barrier closes any position that hits
neither horizontal barrier within max_hold_days, exactly as in the
canonical Triple Barrier construction (upper/lower/vertical barriers, exit
at whichever is touched first).

Signal logic
------------
- Entry (long): close makes a new `donchian_window`-day high AND price is
  above its `trend_window`-day SMA (trend filter, consistent with this
  repo's prior finding that Donchian breakouts need a trend gate to avoid
  whipsaws in choppy/bidirectional conditions).
- At entry, sigma_t0 = trailing `vol_window`-day realized daily-return
  std (NOT annualized -- barriers are per-bar daily-return-scale).
  - Upper barrier (take-profit): entry_price * (1 + theta_up * sigma_t0)
  - Lower barrier (stop-loss):   entry_price * (1 - theta_dn * sigma_t0)
  - Vertical barrier (time-stop): max_hold_days bars after entry
- Exit: whichever of the three barriers is touched first (checked on close
  each bar after entry, consistent with the resolution of loaded OHLCV
  data -- a close-based approximation of the barrier-touch test, since we
  only have daily OHLCV, not intrabar ticks).
- Flat (no position) otherwise; long-only, no re-entry while in a position.

Interface contract for validators (see validation/validators.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    trend_window: int = 200,
    vol_window: int = 20,
    theta_up: float = 2.0,
    theta_dn: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series using triple-barrier exits."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()

    donchian_high = high.rolling(donchian_window).max().shift(1)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend
    new_high_breakout = close > donchian_high

    n = len(close)
    close_vals = close.values
    breakout_vals = new_high_breakout.fillna(False).values
    uptrend_vals = uptrend.fillna(False).values
    vol_vals = realized_vol.values

    position = pd.Series(0, index=close.index, dtype=int)

    in_pos = False
    entry_idx = -1
    upper_barrier = None
    lower_barrier = None

    for i in range(n):
        if not in_pos:
            if breakout_vals[i] and uptrend_vals[i] and vol_vals[i] == vol_vals[i] and vol_vals[i] > 0:
                in_pos = True
                entry_idx = i
                entry_price = close_vals[i]
                sigma0 = vol_vals[i]
                upper_barrier = entry_price * (1 + theta_up * sigma0)
                lower_barrier = entry_price * (1 - theta_dn * sigma0)
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            price = close_vals[i]
            hit_upper = price >= upper_barrier
            hit_lower = price <= lower_barrier
            hit_time = held >= max_hold_days
            if hit_upper or hit_lower or hit_time:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    trend_window: int = 200,
    vol_window: int = 20,
    theta_up: float = 2.0,
    theta_dn: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        donchian_window=donchian_window,
        trend_window=trend_window,
        vol_window=vol_window,
        theta_up=theta_up,
        theta_dn=theta_dn,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
