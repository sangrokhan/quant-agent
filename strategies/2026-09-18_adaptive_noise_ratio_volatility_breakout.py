"""Strategy: Adaptive-K Larry Williams Volatility Breakout using a trailing
average NOISE RATIO as the breakout coefficient (instead of a fixed K).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per multiple Korean quant-trading blog sources (tenmillionquant.tistory.com
"트레이딩 전략 13: 평균 노이즈 비율 + 마켓타이밍 + 변동성 돌파" and Google's AI
summary of "래리 윌리엄스 변동성 돌파 전략 K값" sources, both read this
iteration via browser_exec Google SERP -- web_search DDGS backend returned
empty results), the classic Larry Williams Volatility Breakout strategy
(buy target = today's open + K * (prior day's high - prior day's low), long
if today's price exceeds that target, exit at tomorrow's open) is commonly
adapted by making K itself DATA-DRIVEN rather than a fixed constant:

  noise_t = 1 - abs(close_t - open_t) / (high_t - low_t)
  K_t = mean(noise_{t-n_lookback+1} ... noise_t)   # trailing average noise ratio

Per the source's own stated rationale, "노이즈가 작을 수록 변동성 돌파에 더
유리하다" ("the smaller the noise, the more favorable for volatility
breakout") -- i.e. days where price closes near one extreme of its range
(low noise) indicate directional/trending conditions where a breakout target
is more likely to be genuine follow-through rather than a false intraday
spike that reverses. Using the trailing average noise ratio as K makes the
breakout threshold self-adjust: in choppy/noisy regimes K rises toward 1.0
(harder to trigger, filtering false breakouts), while in trending/low-noise
regimes K falls (easier to trigger, capturing more genuine breakout days).
This is a genuinely distinct construction from this repo's prior fixed-K
Larry Williams Volatility Breakout entries (e.g. 2026-09-04-069,
2026-09-04-094) since K is now a rolling, self-normalizing statistic derived
from price-bar geometry rather than a hand-tuned constant.

Signal logic
------------
- noise_t = 1 - |close_t - open_t| / (high_t - low_t) (bounded in [0, 1];
  clamp any zero-range bars to noise=1, i.e. "maximally noisy/no info").
- K_t = rolling mean of noise over the trailing `noise_lookback` bars
  (using noise up to and including bar t-1, since K for day t's breakout
  target must be knowable before trading starts that day).
- target_t = open_t + K_t * (high_{t-1} - low_{t-1}).
- Long entry: that day's high >= target_t (breakout triggers intraday).
  Since we only have daily OHLC (not intrabar), approximate "price touched
  target during the day" with high_t >= target_t, and assume a fill AT the
  target price itself (standard simplification for this class of strategy
  when only daily bars are available).
- Exit: always flat by the next day's open (single-day hold, per the
  source's own standard "buy today, sell at tomorrow's open" rule) --
  position return realized as (next_open / target - 1) when triggered.
- No position (flat) on days the breakout doesn't trigger.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _noise_ratio(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    noise = 1.0 - (df["close"] - df["open"]).abs() / rng
    noise = noise.fillna(1.0).clip(lower=0.0, upper=1.0)
    return noise


def generate_signals(
    price_df: pd.DataFrame,
    noise_lookback: int = 20,
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} position series: 1 on days the breakout triggers
    (held for that single day only), 0 otherwise.

    `trend_window` (0 = disabled) optionally requires close > SMA(trend_window)
    on the prior close as an additional long-only trend filter, per common
    practice of pairing the volatility breakout with a market-timing filter.
    """
    df = _prep(price_df)
    noise = _noise_ratio(df)
    k = noise.rolling(noise_lookback).mean().shift(1)

    prior_range = (df["high"] - df["low"]).shift(1)
    target = df["open"] + k * prior_range

    breakout = df["high"] >= target

    if trend_window and trend_window > 0:
        sma_trend = df["close"].rolling(trend_window).mean().shift(1)
        trend_ok = df["close"].shift(1) > sma_trend
        breakout = breakout & trend_ok.fillna(False)

    position = breakout.fillna(False).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    noise_lookback: int = 20,
    trend_window: int = 0,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    On a triggered day, the realized return approximates buying at the
    breakout target price and selling at that same day's close (a
    conservative daily-bar approximation of "exit before end of day" since
    we lack intrabar data to fill at next day's open precisely without
    look-ahead in the position series indexing used by grid_test/validators,
    which expect the returns series aligned 1:1 to price_df's index).
    """
    df = _prep(price_df)
    position = generate_signals(price_df, noise_lookback=noise_lookback, trend_window=trend_window)

    noise = _noise_ratio(df)
    k = noise.rolling(noise_lookback).mean().shift(1)
    prior_range = (df["high"] - df["low"]).shift(1)
    target = df["open"] + k * prior_range

    day_return = (df["close"] / target - 1.0).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    strategy_ret = position * day_return
    return strategy_ret
