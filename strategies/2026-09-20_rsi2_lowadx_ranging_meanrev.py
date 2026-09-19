"""Strategy: Short-period RSI(2-3) mean reversion gated by a LOW short-period
ADX (weak trend / ranging-market) filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per quantifiedstrategies.com's "RSI & ADX Trading Strategies" (read in-browser,
https://www.quantifiedstrategies.com/rsi-adx-trading-strategy/, the paywalled
"Trading Rules" boxes are members-only but the article's own Key Takeaways/
body text give explicit, testable parameter guidance): RSI and IBS work best
for short-term mean-reversion with SHORT lookbacks (2-3 days), while ADX
measures trend STRENGTH (not direction) and performs best with a SHORT
period (5-10 days, vs the popular default of 14) and a threshold around
30-40 (source's own optimization, vs the popular 25). The article frames ADX
as complementary to RSI: "RSI and IBS are best suited for mean-reversion...
ADX is primarily a trend-strength indicator." A natural, testable synthesis
not yet in this repo's log: use ADX as a RANGING-market gate (ADX BELOW a
threshold, i.e. the opposite polarity from all this repo's prior ADX
filters, which gated entries on ADX ABOVE a threshold to confirm a strong
trend) to confirm mean-reversion RSI(2-3) entries only fire when the market
is genuinely non-trending/choppy -- exactly the regime where the article
says mean reversion (RSI/IBS) rather than trend-following (ADX) is the
right tool. Distinct from 2026-09-08-002 (also a low-ADX gate, but on a
percentage-distance-from-SMA BIAS-style signal, not RSI) and from
2026-09-03-005 (Connors-style RSI(2) with a 200-SMA trend filter and NO
ADX gate at all). Also distinct in using ADX(5-10) rather than the
repo-standard ADX(14).

Signal logic
------------
- RSI(rsi_period, short e.g. 2 or 3) computed via Wilder's smoothing.
- ADX(adx_period, short e.g. 5-10) computed via the classic Wilder
  DM/ADX construction (based on high/low, not close).
- Long entry: RSI closes at/below `rsi_oversold` (e.g. 10) AND
  ADX is at/below `adx_max` (ranging-market confirmation, e.g. 30).
- Exit: RSI closes at/above `rsi_exit` (mean-reversion target reached,
  e.g. 60) OR a `max_hold_days` time-stop (avoid indefinite holds if the
  bounce never comes).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _wilder_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Classic Wilder ADX (via +DM/-DM/TR, Wilder-smoothed)."""
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_mask = (up_move > down_move) & (up_move > 0)
    minus_mask = (down_move > up_move) & (down_move > 0)
    plus_dm[plus_mask] = up_move[plus_mask]
    minus_dm[minus_mask] = down_move[minus_mask]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0, 1e-12))
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0, 1e-12))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    adx_period: int = 7,
    rsi_oversold: float = 10.0,
    rsi_exit: float = 60.0,
    adx_max: float = 30.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long while RSI(rsi_period) has closed at/below `rsi_oversold` AND
    ADX(adx_period) is at/below `adx_max` (ranging-market confirmation) on
    the entry bar; exit when RSI closes back at/above `rsi_exit`, or after
    `max_hold_days`.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi = _wilder_rsi(close, rsi_period)
    adx = _wilder_adx(high, low, close, adx_period)

    entry_signal = (rsi <= rsi_oversold) & (adx <= adx_max)
    exit_signal = rsi >= rsi_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
