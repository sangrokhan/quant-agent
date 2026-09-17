"""Strategy: Ehlers RocketRSI mean-reversion (TASC May 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-150):
John Ehlers' TASC May 2018 article "RocketRSI -- A Solid Propellant For
Your Rocket Science Trading" builds a new RSI variant and Fisher-transforms
it for sharper, more statistically-precise turning-point spikes:
    Mom = Close - Close[RSILength-1]          (half-dominant-cycle momentum)
    Filt = SuperSmoother(Mom, SmoothLength)     (2-pole low-pass filter)
    CU = sum of positive Filt[i]-Filt[i+1] differences over RSILength bars
    CD = sum of negative differences (as positive magnitudes)
    MyRSI = (CU - CD) / (CU + CD), clipped to [-0.999, 0.999]
    RocketRSI = 0.5 * ln((1+MyRSI)/(1-MyRSI))   (Fisher Transform)
Unlike classic RSI (bounded 0-100, averages of up/down closes), RocketRSI
is Fisher-transformed onto an effectively unbounded Gaussian-ish scale
centered at zero, with the momentum SuperSmoothed BEFORE the up/down
accumulation (not after, unlike classic Wilder smoothing of raw closes).
Ehlers' own claim: "the resultant output is statistically significant
spikes that indicate cyclic turning points with precision."

Source's own disclosed TradeStation strategy is a MEAN-REVERSION rule:
long when RocketRSI crosses BELOW -OBOSLevel (oversold spike, expecting a
snap-back), short when it crosses above +OBOSLevel. Long-only adaptation
per SAFETY.md (SellShort branch dropped). Source's own exit is a fixed-
dollar stop-loss (SetStopLoss) -- replaced here with a mean-reversion
target (RocketRSI crossing back above an exit_level near zero) plus a
max_hold_days time-stop, since fixed-dollar stops aren't comparable across
QQQ/SPY/BTC/ETH price scales (both our own additions, flagged as such).

This is a genuinely novel Ehlers construction for this repo (distinct from
all prior Ehlers RSI-family entries -- Laguerre RSI, MESA Stochastic --
since RocketRSI applies SuperSmoothing to MOMENTUM before an up/down-close
accumulation, then a Fisher Transform, none of which appear in Laguerre RSI
or MESA Stochastic's construction). Also distinct from the forward Fisher
Transform of raw price (2026-09-04-051/2026-09-05-086) since here the
Fisher Transform is applied to the RocketRSI ratio, not price directly.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/05/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _rocket_rsi(close: pd.Series, smooth_length: int, rsi_length: int) -> pd.Series:
    n = len(close)
    vals = close.to_numpy(dtype=float)

    a1 = math.exp(-1.414 * math.pi / smooth_length)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180 / smooth_length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    mom = [0.0] * n
    for i in range(n):
        if i >= rsi_length - 1:
            mom[i] = vals[i] - vals[i - (rsi_length - 1)]
        else:
            mom[i] = 0.0

    filt = [0.0] * n
    for i in range(n):
        mom_1 = mom[i - 1] if i > 0 else mom[i]
        filt_1 = filt[i - 1] if i > 0 else 0.0
        filt_2 = filt[i - 2] if i > 1 else 0.0
        filt[i] = c1 * (mom[i] + mom_1) / 2 + c2 * filt_1 + c3 * filt_2

    rocket = [0.0] * n
    for i in range(n):
        if i < rsi_length:
            continue
        cu = 0.0
        cd = 0.0
        for count in range(rsi_length):
            idx = i - count
            diff = filt[idx] - filt[idx - 1]
            if diff > 0:
                cu += diff
            elif diff < 0:
                cd += -diff
        denom = cu + cd
        if denom == 0:
            my_rsi = 0.0
        else:
            my_rsi = (cu - cd) / denom
        my_rsi = max(-0.999, min(0.999, my_rsi))
        rocket[i] = 0.5 * math.log((1 + my_rsi) / (1 - my_rsi))

    return pd.Series(rocket, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    smooth_length: int = 10,
    rsi_length: int = 10,
    obos_level: float = 2.0,
    exit_level: float = 0.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rocket_rsi = _rocket_rsi(close, smooth_length, rsi_length)

    entry = (rocket_rsi < -obos_level) & (rocket_rsi.shift(1) >= -obos_level)
    exit_meanrev = rocket_rsi > exit_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
