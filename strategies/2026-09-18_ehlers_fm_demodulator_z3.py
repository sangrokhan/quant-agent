"""Strategy: Ehlers FM-Demodulated Z3 momentum ROC crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, source
https://traders.com/Documentation/FEEDbk_docs/2021/06/TradersTips.html,
TASC June 2021, John Ehlers "Creating More Robust Trading Strategies With
The FM Demodulator"):

This repo already tested the plain "Simple Strategy" baseline from the same
TASC article (id 2026-09-17-161: Z3 = sum of 4 consecutive 2-bar price
derivatives, SMA-smoothed into Signal, ROC-of-Signal zero-crossover entry,
Signal-crosses-under-zero exit). That baseline was accepted on QQQ but
failed universally in the high-vol regime tercile (0/108 grid cells) and
was rejected on SPY/crypto.

The article's actual "FM demodulator" contribution -- and the second
EasyLanguage strategy TradeStation discloses in the same Traders' Tips
entry -- adds an RMS-normalization + hard-clip step to the raw price
derivative BEFORE the same Nyquist-zeroed Z3 integration:

    Deriv = Close - Close[2]
    RMS   = sqrt(mean(Deriv[0..49]**2))           # trailing 50-bar RMS
    Clip  = clip(2 * Deriv / RMS, -1, 1)          # normalized, hard-limited
    Z3    = Clip + Clip[1] + Clip[2] + Clip[3]    # same Nyquist-zero integration
    Signal = SMA(Z3, sig_period)
    ROC    = Signal - Signal[roc_period]
    Buy next bar on Open when ROC crosses above 0
    Sell next bar on Open when Signal crosses below 0

Economic rationale (per the article, and Ehlers' stated purpose): the
RMS-normalization makes the derivative's magnitude vol-invariant across
regimes -- a fixed-size price move in a high-vol regime produces a SMALLER
normalized Clip value than the same move in a low-vol regime, damping the
whipsaw-prone reaction to noise. This directly targets the specific failure
mode recorded for the un-normalized baseline (2026-09-17-161): "universal
failure in high-vol regime". Distinct technique from the accepted baseline
(same Z3/ROC-crossover skeleton, but the normalization is the entire novel
mechanic under test here) -- not a near-duplicate since the derivative
transform materially changes which bars trigger the crossover.

Interface contract for validators (see validation/validators.py) and
grid_test.py (Step 6): generate_signals/generate_returns both accept
tunable parameters as keyword arguments.
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


def _fm_demod_z3_signal(
    close: pd.Series,
    rms_window: int = 50,
    sig_period: int = 8,
    roc_period: int = 1,
) -> pd.Series:
    """Compute the Signal series (SMA of Nyquist-zeroed Z3 of the
    RMS-normalized, hard-clipped 2-bar derivative)."""
    deriv = close.diff(2)

    # Trailing rms_window RMS of the derivative (matches EasyLanguage's
    # `for count = 0 to 49: RMS += Deriv[count]**2` then RMS/50 inside sqrt).
    rms = np.sqrt((deriv ** 2).rolling(rms_window).mean())

    clip = (2 * deriv / rms).clip(lower=-1.0, upper=1.0)
    clip = clip.fillna(0.0)

    z3 = clip + clip.shift(1) + clip.shift(2) + clip.shift(3)
    signal = z3.rolling(sig_period).mean()
    return signal


def generate_signals(
    price_df: pd.DataFrame,
    rms_window: int = 50,
    sig_period: int = 8,
    roc_period: int = 1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: ROC(Signal, roc_period) crosses above 0 (buy next bar on open,
    approximated here as taking effect the following bar via the standard
    T+1 shift applied in generate_returns).
    Exit: Signal crosses below 0, or max_hold_days reached (avoid
    indefinite holds, consistent with other momentum strategies in this
    repo, e.g. 2026-09-17-161's own max_hold_days convention).
    """
    df = _prep(price_df)
    close = df["close"]

    signal = _fm_demod_z3_signal(close, rms_window, sig_period, roc_period)
    roc = signal - signal.shift(roc_period)

    entry = (roc > 0) & (roc.shift(1) <= 0)
    exit_signal_neg = (signal < 0) & (signal.shift(1) >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal_neg.iloc[i]) or held >= max_hold_days:
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
