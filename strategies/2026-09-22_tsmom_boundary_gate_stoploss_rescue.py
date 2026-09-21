"""Strategy: 12-month TSMOM + extreme-return boundary gate (direct fix
attempt for near-miss 2026-09-22-037) with a DAILY-checked hard
formation-price stop-loss layered on top of the monthly rebalance
decision.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-038):
Direct fix attempt for this cron trigger's own prior near-miss rejection
2026-09-22-037 (12-month TSMOM gated by a trailing-return-magnitude
extreme-percentile proxy for the "valuation boundary" effect in Suominen &
Hjalmarsson's "Boundaries of Time Series Momentum",
https://quantpedia.com/boundaries-of-time-series-momentum/). That entry's
own diagnosis: QQQ passed Sharpe (1.025, barely) but failed max drawdown
(0.286, parameter-invariant across 8 tested extreme_pctile/lookback_years
combos) because the MONTHLY-rebalanced extreme-return gate cannot react
fast enough to a violent regime break (the March 2020 COVID crash) --
trailing 12m momentum was still positive going into the crash, so neither
the base signal nor the gate had fired yet by the time price started
falling. The notes explicitly flagged the fix: "pair this extreme-return
gate ... with a FASTER-reacting daily circuit-breaker (hard stop-loss or
realized-vol kill-switch) rather than trying further pctile/lookback
tuning on the monthly signal". This entry implements exactly that fix,
reusing this repo's own already-validated formation-price hard-stop-loss
mechanism (strategies/2026-09-08_formation_price_stoploss_trend.py, id
2026-09-08-178/179, both accepted -- per Han, Zhou & Zhu "Taming Momentum
Crashes: A Simple Stop-Loss Strategy", https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/):
a fixed percentage stop-loss from the position's entry price, checked
EVERY trading day (not just at month boundaries), which can flatten the
position mid-month the instant the fast crash breaches the threshold,
something the purely-monthly extreme-return gate structurally cannot do.

Signal logic
------------
- Base entry/gate exactly as in 2026-09-22_tsmom_boundary_extreme_gate.py:
  trailing 252-day return > 0 AND its |magnitude| is NOT in the top
  `extreme_pctile` of its own rolling `lookback_years`-year history,
  evaluated/rebalanced monthly.
- NEW: once a monthly-rebalance decision opens a long position, track the
  entry (formation) price and check EVERY trading day (not just at the
  next month boundary) whether close has fallen below
  entry_price * (1 - stop_loss_pct). If so, exit immediately and stay flat
  until the NEXT monthly rebalance re-evaluates the base signal fresh
  (mirroring the reference formation-price-stop strategy's re-entry rule:
  no re-entry until a fresh signal, not an automatic same-month re-entry).

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


def _monthly_gated_signal(
    close: pd.Series,
    lookback_days: int,
    lookback_years: int,
    extreme_pctile: float,
) -> pd.Series:
    trailing_return = close / close.shift(lookback_days) - 1.0
    abs_return = trailing_return.abs()

    window = max(lookback_years * 252, lookback_days + 20)
    pct_rank = abs_return.rolling(window, min_periods=max(60, lookback_days)).apply(
        lambda x: (x < x[-1]).sum() / (len(x) - 1) * 100.0 if len(x) > 1 else 50.0,
        raw=True,
    )
    extreme = (pct_rank >= extreme_pctile).fillna(False)
    momentum_positive = (trailing_return > 0).fillna(False)
    raw_daily_signal = momentum_positive & (~extreme)

    month_end_signal = raw_daily_signal.resample("ME").last()
    monthly_position = month_end_signal.reindex(
        pd.date_range(month_end_signal.index.min(), close.index.max(), freq="D")
    ).ffill()
    return monthly_position.reindex(close.index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    lookback_years: int = 5,
    extreme_pctile: float = 90.0,
    stop_loss_pct: float = 0.10,
) -> pd.Series:
    """Return a {0,1} long/flat position series: monthly-rebalanced 12m
    TSMOM + extreme-return gate, with a daily-checked hard formation-price
    stop-loss overlay (re-entry only on the NEXT monthly signal, not
    automatic same-month re-entry after a stop-out).
    """
    df = _prep(price_df)
    close = df["close"]

    monthly_signal = _monthly_gated_signal(close, lookback_days, lookback_years, extreme_pctile)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = None
    stopped_out_this_month = False
    current_month = None

    for i in range(len(close)):
        px = close.iloc[i]
        month_key = (close.index[i].year, close.index[i].month)
        if month_key != current_month:
            current_month = month_key
            stopped_out_this_month = False

        wants_long = bool(monthly_signal.iloc[i])

        if in_position:
            stop_price = entry_price * (1.0 - stop_loss_pct)
            stopped_out = px < stop_price
            if stopped_out or not wants_long:
                in_position = False
                entry_price = None
                if stopped_out:
                    stopped_out_this_month = True
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if wants_long and not stopped_out_this_month:
                in_position = True
                entry_price = px
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
