"""Strategy: SMA(trend_window) directional gate with continuous DFA
(Detrended Fluctuation Analysis) scaling-exponent sizing overlay + deadband,
leverage-cap-aware for crypto.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Direct rescue/reframe of this repo's prior rejected DFA-alpha regime-
TRANSITION strategy (2026-09-10-078, strategies/2026-09-10_dfa_alpha_regime_transition_trend.py):
that strategy traded a binary up-cross of DFA alpha through a fixed
threshold (0.55) combined with an SMA trend filter, and was rejected --
decisive full-sample Sharpe fail, though the grid showed an interesting
low-vol-regime-only pass_fraction of 11/12 with mid/high-vol at 0/12 each
(scope note in that entry), and crypto was never tested (compute-cost
scope limitation noted in that entry's notes).

This repo has an established, repeatedly-successful pattern for rescuing
binary threshold-crossing regime indicators: reframe the RAW LEVEL of the
statistic as a CONTINUOUS SIZING DIAL instead of a hard on/off gate (already
applied successfully to Hurst-exponent [2026-09-16-XXX, this file's direct
sibling/template], CBOE SKEW, VPT, Disparity Index, DPO, DSP, Kalman slope,
RVI, TII, VHF, MAMA-FAMA spread). DFA alpha is theoretically bounded roughly
[0,1] like the Hurst exponent (in fact DFA-alpha and the classical Hurst
exponent H are closely related/near-identical for stationary series per
the DFA literature) -- alpha<0.5 anti-persistent, alpha=0.5 random walk,
alpha>0.5 persistent/trending. This strategy rescales alpha the same way
this repo's Hurst-sizing-dial strategy does: dial=(alpha-0.5)*2 clipped to
[-1,1], used as a continuous sizing signal inside an SMA(trend_window)
uptrend gate with deadband (to cut turnover), leverage-cap-aware so crypto
can be tested for the first time on this specific DFA construction (the
prior 2026-09-10-078 entry explicitly scoped crypto out for compute-cost
reasons; this iteration includes it since DFA's O(n) rolling-window cost
at reasonable window sizes is manageable).

Unlike Hurst's R/S-based estimator, DFA uses local-linear detrending on
non-overlapping segments across multiple scales (log-log slope of the RMS
fluctuation function vs segment length) -- a genuinely different estimator
construction, known in the literature to behave more robustly on
non-stationary series (daily equity/crypto prices) than raw R/S analysis.
Source: pyquantlab.com's DFA article (same source cited in 2026-09-10-078,
already in this repo's ledger; own BTC worked example found alpha=0.57,
"persistent behavior").

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _dfa_alpha_single(x: np.ndarray, scales) -> float:
    """DFA scaling exponent for one 1-D array of returns (unchanged
    methodology from strategies/2026-09-10_dfa_alpha_regime_transition_trend.py)."""
    x = x[~np.isnan(x)]
    if len(x) < max(scales) * 2:
        return np.nan
    y = np.cumsum(x - np.mean(x))
    fluct = np.zeros(len(scales))
    for i, scale in enumerate(scales):
        n_seg = len(y) // scale
        if n_seg < 2:
            fluct[i] = np.nan
            continue
        shape = (n_seg, scale)
        seg = y[: n_seg * scale].reshape(shape)
        scale_ax = np.arange(scale)
        rms_vals = np.empty(n_seg)
        for j in range(n_seg):
            coeff = np.polyfit(scale_ax, seg[j], 1)
            fit = np.polyval(coeff, scale_ax)
            rms_vals[j] = np.sqrt(np.mean((seg[j] - fit) ** 2))
        fluct[i] = np.sqrt(np.mean(rms_vals**2))
    valid = ~np.isnan(fluct) & (fluct > 0)
    if valid.sum() < 3:
        return np.nan
    coeff = np.polyfit(np.log2(np.array(scales)[valid]), np.log2(fluct[valid]), 1)
    return float(coeff[0])


def _rolling_dfa_alpha(
    log_ret: pd.Series,
    dfa_window: int,
    scale_min: int,
    scale_max: int,
    n_scales: int,
    step: int = 5,
) -> pd.Series:
    """Rolling DFA alpha, computed every `step` bars for speed and
    forward-filled in between (perf optimization, same idea as this repo's
    Hurst-sizing-dial strategy's step-based computation)."""
    scales = sorted(set(np.linspace(scale_min, scale_max, n_scales).astype(int)))
    arr = log_ret.values.astype(float)
    values = [np.nan] * len(arr)
    for i in range(dfa_window, len(arr) + 1, step):
        window = arr[i - dfa_window : i]
        values[i - 1] = _dfa_alpha_single(window, scales)
    result = pd.Series(values, index=log_ret.index)
    return result.ffill()


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dfa_window: int = 100,
    scale_min: int = 5,
    scale_max: int = 20,
    n_scales: int = 5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    DFA alpha is bounded roughly [0,1] -- rescaled to [-1,1] via
    (alpha-0.5)*2, used directly as a sizing dial: exposure =
    clip(base_exposure + sensitivity*dial, 0, cap), gated to 0 whenever
    close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ratios = close / close.shift(1)
    log_ret = np.log(ratios.where(ratios > 0))
    dfa_alpha = _rolling_dfa_alpha(log_ret, dfa_window, scale_min, scale_max, n_scales)

    dial = (dfa_alpha - 0.5) * 2.0
    dial = dial.clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    dfa_window: int = 100,
    scale_min: int = 5,
    scale_max: int = 20,
    n_scales: int = 5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        dfa_window=dfa_window,
        scale_min=scale_min,
        scale_max=scale_max,
        n_scales=n_scales,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
