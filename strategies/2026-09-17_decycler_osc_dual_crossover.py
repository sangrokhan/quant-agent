"""Strategy: Ehlers Decycler Oscillator Dual-Timeframe Crossover (John Ehlers,
"Decyclers", TASC September 2015), read this iteration via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/09/TradersTips.html
(exact TradeStation EasyLanguage function/strategy code disclosed directly
in the Traders' Tips section -- including the article's OWN fast/slow
dual-timeframe crossover strategy rule, not a third-party reconstruction --
after web_search DDGS backend errored on prior queries this run; direct
traders.com archive URL navigation to a previously-unvisited month).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
This repo has ONE prior Decycler Oscillator entry (2026-09-05-046,
rejected), which used a single-oscillator countertrend-snapback rule
approximated from a paywalled third-party source (its own formula flagged
as "own reconstruction" in that entry's notes, not the article's exact
formula). THIS iteration uses Ehlers' own EXACT disclosed high-pass-filter
math (a 2-pole highpass filter applied twice -- once to price for the
"Decycle" trend line, once to the Decycle itself at half the HPPeriod for
the "DecycleOsc" oscillator, scaled by `100*K*DecycleOsc/Price`) AND the
article's OWN trading rule: compute TWO DecyclerOscillator readings at
different HPPeriod/K settings (a faster one and a slower one) and trade
their CROSSOVER against each other (not either one crossing a fixed
threshold). This is a genuinely different mechanical rule from the prior
rejected entry (dual-oscillator crossover vs. single-oscillator threshold
snapback) using the exact source formula rather than an approximation,
justifying a fresh test per this repo's novelty-check convention for
"exact formula supersedes prior approximation" cases. Long-only adaptation
of the source's long/short symmetric strategy.

Exact formula (from TASC Sep 2015 TradeStation EasyLanguage, as read this
iteration; trig functions in EasyLanguage operate in DEGREES, so `Cosine`/
`Sine` here use the same 360-degree convention translated to radians for
numpy):
    alpha1(period) = (cos(0.707*360/period) + sin(0.707*360/period) - 1)
                      / cos(0.707*360/period)
    HP[t] = (1-alpha1/2)^2 * (Price[t]-2*Price[t-1]+Price[t-2])
            + 2*(1-alpha1)*HP[t-1] - (1-alpha1)^2*HP[t-2]
    Decycle[t] = Price[t] - HP[t]
    alpha2 = alpha1(period/2)  (same formula, HPPeriod halved)
    DecycleOsc[t] = (1-alpha2/2)^2 * (Decycle[t]-2*Decycle[t-1]+Decycle[t-2])
                    + 2*(1-alpha2)*DecycleOsc[t-1] - (1-alpha2)^2*DecycleOsc[t-2]
    DecyclerOscillator = 100 * K * DecycleOsc / Price

    Fast_Val = DecyclerOscillator(Price, fast_hp_period, fast_k)
    Slow_Val = DecyclerOscillator(Price, slow_hp_period, slow_k)
    Long entry: Fast_Val crosses over Slow_Val.
    Long exit (long-only adaptation of source's SellShort-on-cross): Slow_Val
        crosses over Fast_Val.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _decycler_oscillator(price: pd.Series, hp_period: float, k: float) -> pd.Series:
    n = len(price)
    p = price.values

    def _alpha1(period: float) -> float:
        rad = np.deg2rad(0.707 * 360.0 / period)
        return (np.cos(rad) + np.sin(rad) - 1.0) / np.cos(rad)

    alpha1 = _alpha1(hp_period)
    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2) ** 2 * (p[i] - 2 * p[i - 1] + p[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )
    decycle = p - hp

    alpha2 = _alpha1(hp_period / 2.0)
    decycle_osc = np.zeros(n)
    for i in range(2, n):
        decycle_osc[i] = (
            (1 - alpha2 / 2) ** 2 * (decycle[i] - 2 * decycle[i - 1] + decycle[i - 2])
            + 2 * (1 - alpha2) * decycle_osc[i - 1]
            - (1 - alpha2) ** 2 * decycle_osc[i - 2]
        )

    with np.errstate(divide="ignore", invalid="ignore"):
        osc = 100.0 * k * decycle_osc / p
    return pd.Series(osc, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_hp_period: float = 100.0,
    fast_k: float = 1.2,
    slow_hp_period: float = 125.0,
    slow_k: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the Decycler-Oscillator
    dual-timeframe crossover rule (long-only adaptation)."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    fast_val = _decycler_oscillator(close, fast_hp_period, fast_k)
    slow_val = _decycler_oscillator(close, slow_hp_period, slow_k)

    cross_up = (fast_val > slow_val) & (fast_val.shift(1) <= slow_val.shift(1))
    cross_down = (slow_val > fast_val) & (slow_val.shift(1) <= fast_val.shift(1))

    cu_vals = cross_up.values
    cd_vals = cross_down.values

    # warm up: first few bars have HP filter transient, skip signals until
    # both oscillators have settled (use max period as a conservative burn-in)
    warmup = int(max(fast_hp_period, slow_hp_period))

    position = np.zeros(n, dtype=int)
    in_long = False
    for i in range(n):
        if i < warmup:
            position[i] = 0
            continue
        if cu_vals[i]:
            in_long = True
        elif cd_vals[i]:
            in_long = False
        position[i] = 1 if in_long else 0

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
