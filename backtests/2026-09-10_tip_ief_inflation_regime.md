# 2026-09-10 — TIP/IEF Inflation-Expectations Regime Filter (REJECTED)

## Hypothesis

Per AllocateSmartly's review of David Varadi's "Inflation Compass" strategy,
the 5-year TIPS breakeven inflation rate is a market-based inflation
expectations proxy that drives sector/asset rotation. Simplified,
fully-testable proxy tested here: the TIP/IEF price ratio (TIPS ETF vs
nominal Treasury ETF) as an inflation-expectations regime filter, gating a
long SPY/QQQ position via a rolling z-score + hysteresis band (same
mechanism as the already-tested copper/gold and gold/silver ratio filters).

Strategy file: `strategies/2026-09-10_tip_ief_inflation_regime.py`

## Parameter sweep (ratio_lookback x high_z_threshold x low_z_threshold, SPY/QQQ)

Best SPY config: ratio_lookback=252, high_z=0.5, low_z=-0.5 → Sharpe 0.796,
MDD 0.262 (Sharpe still below 1.0 threshold).

Best QQQ config: ratio_lookback=252, high_z=0.3, low_z=-1.0 → Sharpe 0.726,
MDD 0.328 (both Sharpe and MDD fail thresholds).

Across a 12-cell grid (ratio_lookback in {126,252} x high_z in {0.3,0.5,1.0}
x low_z in {-1.0,-0.5}) for both SPY and QQQ, **no configuration reaches
the 1.0 Sharpe threshold** — the highest observed was 0.796.

## Decision: REJECT

The TIP/IEF price-ratio proxy for inflation expectations does not produce
a usable equity-timing signal at any tested parameterization — full
validator suite/grid test skipped as unnecessary given the decisive
parameter-sweep result (best Sharpe 0.796, well short of 1.0). Plausible
explanation: TIP and IEF have very similar duration/rate sensitivity (both
Treasury-related ETFs), so their relative price ratio is a noisy,
low-amplitude signal — much weaker than a genuine breakeven-rate
calculation (nominal yield minus real TIPS yield) would be, since price
ratios convolve both yield-level and duration effects rather than isolating
the inflation-expectations component cleanly. A future loop wanting to
revisit this idea properly would need to source the actual T5YIE series
(e.g. from FRED, which is outside data/loaders.py's current yfinance/ccxt
scope) rather than a price-ratio proxy.
