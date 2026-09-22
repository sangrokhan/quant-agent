"""Strategy: QLD regime-timing rotation + 8% trailing stop on the leveraged
leg (direct fix attempt for this cron trigger's rejected sibling
2026-09-23-007).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Direct rescue attempt of 2026-09-23-007 (QLD single-leg regime-timing
rotation, same QQQ 200d-SMA+126d-momentum risk-on gate, rejected on decisive
MDD fail: realized 0.442 vs this repo's 0.25 threshold, vs. the FinLab
source's own reported -17.9% headline MDD). That prior entry's `notes`
field diagnosed the gap as likely explained by this repo's simplified
single-leg + cash-only adaptation missing the source's execution-engine
mechanisms -- specifically its "8% trailing stop on the leveraged leg"
(explicitly stated in https://finlab.finance/en/blog/us-etf-rotation-strategy:
"Rebalancing is monthly, with an 8% trailing stop on the leveraged leg").
This iteration adds EXACTLY that missing mechanism -- an 8% trailing stop
referenced to each trade's own running peak price since entry (not a fixed
formation-price stop like this repo's existing Han/Zhou/Zhu overlay
strategies/2026-09-08_formation_price_stoploss_trend.py, since the source
specifically says "trailing", i.e. it ratchets up with the running high, not
a fixed level from entry) -- with the identical unmodified QQQ regime gate
otherwise.

Signal logic
------------
- Regime filter (on QQQ): close > SMA(trend_sma) AND momentum_window-day
  return > 0 -> risk-on.
- Enter QLD (position=1) when risk-on and not already in a position.
- While in position, track the running peak close since entry; exit
  immediately (go flat) if close falls stop_loss_pct below that peak
  (trailing stop), OR if the regime flag flips to risk-off (whichever comes
  first).
- Re-entry only on a fresh risk-on signal after either exit type.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_regime_series(index: pd.DatetimeIndex, symbol: str) -> pd.Series:
    """Fetch the regime-gate symbol's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min() - timedelta(days=400)
    end = index.max() + timedelta(days=2)
    df = load_equity(symbol, start, end)
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    regime_symbol: str = "QQQ",
    trend_sma: int = 150,
    momentum_window: int = 126,
    stop_loss_pct: float = 0.08,
) -> pd.Series:
    """Return a {0,1} position series: QQQ regime-gated QLD entry with an
    8%-trailing-stop overlay on the leveraged leg."""
    df = _prep(price_df)
    close = df["close"]

    regime_close = _load_regime_series(df.index, regime_symbol)
    regime_close = regime_close.reindex(
        regime_close.index.union(close.index), method="ffill"
    ).reindex(close.index, method="ffill")

    regime_sma = regime_close.rolling(trend_sma, min_periods=trend_sma).mean()
    regime_mom = regime_close.pct_change(momentum_window)
    risk_on = (regime_close > regime_sma) & (regime_mom > 0)
    valid = regime_sma.notna() & regime_mom.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    running_peak = None

    for i in range(len(close)):
        if not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue

        px = close.iloc[i]

        if in_position:
            running_peak = px if running_peak is None else max(running_peak, px)
            trailing_stop_hit = px <= running_peak * (1 - stop_loss_pct)
            regime_off = not bool(risk_on.iloc[i])
            if trailing_stop_hit or regime_off:
                in_position = False
                running_peak = None
            position.iloc[i] = 1 if in_position else 0
        else:
            if bool(risk_on.iloc[i]):
                in_position = True
                running_peak = px
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    regime_symbol: str = "QQQ",
    trend_sma: int = 150,
    momentum_window: int = 126,
    stop_loss_pct: float = 0.08,
) -> pd.Series:
    """Return daily strategy returns (position held from signal close to next bar close)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        regime_symbol=regime_symbol,
        trend_sma=trend_sma,
        momentum_window=momentum_window,
        stop_loss_pct=stop_loss_pct,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
