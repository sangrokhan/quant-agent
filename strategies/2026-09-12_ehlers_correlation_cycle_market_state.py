"""Strategy: Ehlers Correlation Cycle / Correlation Angle / Market State
regime-switching trend+cycle system.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-138):
Per John F. Ehlers' original paper "Correlation As A Cycle Indicator"
(https://www.mesasoftware.com/papers/CORRELATION%20AS%20A%20CYCLE%20INDICATOR.pdf,
via browser_exec direct-PDF-open then read_file PDF extraction -- web_search
DDGS backend gave no useful direct source this iteration), price is
Pearson-correlated against a Cosine wave (Real component) and a negative
Sine wave (Imag component) over a fixed period, giving a phasor whose angle
= 90 + arctan(Real/Imag) (quadrant-corrected). The source's own exact rule:

    "when the market is in a cycle mode you want to be in a long position
    if the angle is less than zero and you want to be in a short position
    if the angle is greater than zero."

    "the phase angle is not allowed to regress... when the phase display
    flatlines... the interpretation is that the cycle mode has failed and
    therefore the market is now in a trend mode... the correct position is
    to establish a short trend mode position when the phase angle
    flatlines below zero and to establish a long trend mode position when
    the phase angle flatlines above zero."

State variable (source's own EasyLanguage, Code Listing 1): State=0 (cycle
mode) by default; State=-1 (trend down) when |Angle-Angle[1]|<9 AND
Angle<0; State=+1 (trend up) when |Angle-Angle[1]|<9 AND Angle>=0.

Combined position rule (long-only, consistent with this repo's convention):
    long when State==+1 (established trend up)
    long when State==0 AND Angle<0 (cycle mode, angle below zero = ascending
        toward cycle peak per source's phasor convention)
    flat otherwise (State==-1 trend down, or State==0 with Angle>=0)

This is the first Ehlers Correlation-Cycle/Phasor/Market-State strategy in
this repo -- distinct from all other Ehlers-family entries already tested
(Instantaneous Trendline, Cyber Cycle, Even Better Sinewave, Voss Predictive
Filter, Deviation-Scaled MA/Oscillator, Trendflex, Roofing Filter, MESA
Adaptive MA/Sine Wave/Stochastic) since none of those use a Pearson-
correlation-based phasor angle with an explicit trend-mode/cycle-mode state
machine derived from angle-regression detection.

Source: https://www.mesasoftware.com/papers/CORRELATION%20AS%20A%20CYCLE%20INDICATOR.pdf

Interface contract for validators/grid_test:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _correlation_cycle(close: np.ndarray, period: int):
    """Ehlers' Correlation Cycle / Angle / State, direct transliteration of
    the paper's EasyLanguage Code Listing 1 (real-valued Pearson correlation
    of the last `period` closes against a Cosine wave (Real) and a negative
    Sine wave (Imag), then phasor angle + state machine)."""
    n = len(close)
    real = np.full(n, np.nan)
    imag = np.full(n, np.nan)
    angle = np.full(n, np.nan)
    state = np.zeros(n, dtype=int)

    cos_wave = np.array([math.cos(math.radians(360 * k / period)) for k in range(period)])
    neg_sin_wave = np.array([-math.sin(math.radians(360 * k / period)) for k in range(period)])

    for t in range(period - 1, n):
        # window: count=1..Length maps to Price[count-1] i.e. close[t], close[t-1], ...
        window = close[t - period + 1 : t + 1][::-1]  # window[0]=close[t] (count=1 -> Price[0])
        x = window
        y_cos = cos_wave
        y_sin = neg_sin_wave

        sx = x.sum()
        sxx = (x * x).sum()

        sy_c = y_cos.sum()
        sxy_c = (x * y_cos).sum()
        syy_c = (y_cos * y_cos).sum()
        denom_c = (period * sxx - sx * sx) * (period * syy_c - sy_c * sy_c)
        r = (period * sxy_c - sx * sy_c) / math.sqrt(denom_c) if denom_c > 0 else np.nan

        sy_s = y_sin.sum()
        sxy_s = (x * y_sin).sum()
        syy_s = (y_sin * y_sin).sum()
        denom_s = (period * sxx - sx * sx) * (period * syy_s - sy_s * sy_s)
        im = (period * sxy_s - sx * sy_s) / math.sqrt(denom_s) if denom_s > 0 else np.nan

        real[t] = r
        imag[t] = im

        if im is not None and not np.isnan(im) and im != 0:
            ang = 90 + math.degrees(math.atan(r / im))
        else:
            ang = np.nan
        if im is not None and not np.isnan(im) and im > 0:
            ang = ang - 180

        prev_angle = angle[t - 1] if t > period - 1 else np.nan
        if not np.isnan(prev_angle) and not np.isnan(ang) and (prev_angle - ang) < 270 and ang < prev_angle:
            ang = prev_angle

        angle[t] = ang

        if t > period - 1 and not np.isnan(angle[t]) and not np.isnan(angle[t - 1]):
            d = abs(angle[t] - angle[t - 1])
            if d < 9 and angle[t] < 0:
                state[t] = -1
            elif d < 9 and angle[t] >= 0:
                state[t] = 1
            else:
                state[t] = 0

    return real, imag, angle, state


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)

    _real, _imag, angle, state = _correlation_cycle(close, period)

    position = np.zeros(n, dtype=int)
    for i in range(n):
        if state[i] == 1:
            position[i] = 1
        elif state[i] == 0 and not np.isnan(angle[i]) and angle[i] < 0:
            position[i] = 1
        else:
            position[i] = 0

    return pd.Series(position, index=df.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
