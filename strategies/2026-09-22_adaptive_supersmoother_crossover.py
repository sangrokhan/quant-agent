"""Strategy: Ehlers Adaptive SuperSmoother crossover (TASC September 2026).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per John F. Ehlers' "Improved Filter Performance" (TASC Traders' Tips,
September 2026 edition), replicated exactly per the TradingView editors'
pick port (https://www.tradingview.com/script/FnlMn99W-TASC-2026-09-Adaptive-SuperSmoother/,
read via browser_exec this iteration), the SuperSmoother (a 2-pole
recursive low-pass filter with substantially greater high-frequency
attenuation than an EMA of comparable lag) can be made adaptive by scaling
its own critical period based on the rate-of-change (ROC) of a
FIXED-period SuperSmoother of the same series, RMS-normalized:

    1. filt_fixed = SuperSmoother(price, base_period)   (fixed period)
    2. roc = filt_fixed[t] - filt_fixed[t-1]             (1-bar ROC of step 1)
    3. rms = sqrt(mean(roc[t-rms_length+1 .. t]^2))       (rolling RMS of roc)
    4. scaled_roc = clip(roc / rms, max=2.0)              (scale + cap at 2.0)
    5. factor = (1 - 0.5*scaled_roc)^2
    6. adaptive_period = max(2, base_period * factor)
    7. filt_adaptive = SuperSmoother(price, adaptive_period[t], time-varying)

Source's own disclosed trading rule (USAGE section): long when the
Adaptive SuperSmoother is above the fixed-period SuperSmoother, short
(here: flat, long-only per this repo's convention) otherwise.

Distinct from this repo's 5+ prior Ehlers-SuperSmoother-based entries
(MESA Stochastic, Roofing Filter, Trendflex, Even Better Sinewave, Reflex)
-- none of those implement Ehlers' own specific ADAPTIVE-PERIOD
SuperSmoother construction or its disclosed adaptive-vs-fixed crossover
rule; they all use a SuperSmoother as a component inside a different
downstream oscillator.

Signal logic
------------
- Entry (long): adaptive SuperSmoother crosses above (or is above,
  entered fresh) the fixed-period SuperSmoother.
- Exit: adaptive crosses back below the fixed-period line, or a
  max_hold_days time-stop backstop (source discloses no explicit
  stop/exit beyond the raw crossover direction; the long-only framing
  here treats "short" as "flat").
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _supersmoother_fixed(price: pd.Series, period: float) -> pd.Series:
    """Standard 2-pole Ehlers SuperSmoother, fixed period."""
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3

    values = price.tolist()
    n = len(values)
    filt = [0.0] * n
    for i in range(n):
        p0 = values[i]
        p1 = values[i - 1] if i >= 1 else p0
        f1 = filt[i - 1] if i >= 1 else p0
        f2 = filt[i - 2] if i >= 2 else p0
        filt[i] = c1 * (p0 + p1) / 2.0 + c2 * f1 + c3 * f2
    return pd.Series(filt, index=price.index)


def _supersmoother_adaptive_period(price: pd.Series, periods: pd.Series) -> pd.Series:
    """2-pole SuperSmoother with a TIME-VARYING period series."""
    values = price.tolist()
    period_vals = periods.tolist()
    n = len(values)
    filt = [0.0] * n
    for i in range(n):
        period = max(2.0, float(period_vals[i]))
        a1 = math.exp(-1.414 * math.pi / period)
        b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
        c2 = b1
        c3 = -a1 * a1
        c1 = 1.0 - c2 - c3

        p0 = values[i]
        p1 = values[i - 1] if i >= 1 else p0
        f1 = filt[i - 1] if i >= 1 else p0
        f2 = filt[i - 2] if i >= 2 else p0
        filt[i] = c1 * (p0 + p1) / 2.0 + c2 * f1 + c3 * f2
    return pd.Series(filt, index=price.index)


def _adaptive_supersmoother(
    close: pd.Series, base_period: int = 20, rms_length: int = 81
) -> tuple[pd.Series, pd.Series]:
    filt_fixed = _supersmoother_fixed(close, base_period)

    roc = filt_fixed.diff()
    rms = (roc.pow(2).rolling(rms_length).mean()) ** 0.5
    rms = rms.replace(0.0, pd.NA)
    scaled_roc = (roc / rms).clip(upper=2.0)
    scaled_roc = scaled_roc.fillna(0.0)

    factor = (1.0 - 0.5 * scaled_roc) ** 2
    adaptive_period = (base_period * factor).clip(lower=2.0)

    filt_adaptive = _supersmoother_adaptive_period(close, adaptive_period)
    return filt_fixed, filt_adaptive


def generate_signals(
    price_df: pd.DataFrame,
    base_period: int = 20,
    rms_length: int = 81,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt_fixed, filt_adaptive = _adaptive_supersmoother(
        close, base_period=base_period, rms_length=rms_length
    )

    above = (filt_adaptive > filt_fixed).fillna(False)
    above_prev = above.shift(1).fillna(False)

    entry = above & ~above_prev
    exit_signal = (~above) & above_prev

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
