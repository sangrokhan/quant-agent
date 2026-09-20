# 2026-09-20: Ehlers Stochastic (Roofing-Filter, Predictive Mode) — REJECTED

**Hypothesis:** Per
https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/E-F/EhlersStochastic
(John F. Ehlers, TASC Jan 2014 "Predictive Indicators For Effective
Trading Strategies"): a standard %K Stochastic applied to price after
passing through Ehlers' Roofing Filter (high-pass + SuperSmoother
bandpass, 10-48 bar cycle band), with the source's own novel "predictive"
signal mode: buy when Stochastic crosses BELOW oversold, sell when it
crosses ABOVE overbought (inverse of the ordinary crossover convention).

**Source:**
https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/E-F/EhlersStochastic
(browser_exec).

**Grid test** (length in [14,20,30], overbought in [70,80], oversold in
[20,30], mode in [predictive,conventional], QQQ/SPY/BTC-USDT/ETH-USDT, 3
vol terciles, 288 cells):
- pass_fraction: 0.184 (53/288)
- by_asset_class: equity 51/144, crypto 2/144
- by_vol_regime: low 42/96, mid 10/96, high 1/96
- best_cell: QQQ low-vol, sharpe 2.47 (length=14, overbought=70,
  oversold=30, mode=predictive)

**Full-sample confirmation** at 5 configs (predictive mode, QQQ/SPY):

| Config | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| len=14, 70/30 | 0.961 | 0.694 |
| len=10, 70/30 | 0.871 | 0.632 |
| len=14, 80/20 | 0.847 | 0.630 |
| len=20, 70/30 | 0.740 | 0.634 |
| len=14, 75/25 | 0.921 | 0.612 |

Best achieved: QQQ Sharpe 0.961 (length=14, overbought=70, oversold=30) --
a near-miss just under the 1.0 threshold; SPY never exceeds 0.694 across
any config tried, and MDD also fails for SPY at every config (0.26-0.31 vs
0.25 threshold).

**Decision: REJECTED.** QQQ is a near-miss (0.961) but SPY fails
decisively on both Sharpe and MDD across all 5 configs tried; grid
pass_fraction 0.184 with only 2/144 crypto cells passing. Flagging QQQ
0.961 as a potential future retune candidate (per this repo's near-miss
convention), but not pursuing further within this iteration's budget
given SPY's consistently weaker performance suggests the signal isn't
broadly robust across even the two equity symbols. Walk-forward/
parameter-sensitivity/tx-cost validators skipped given SPY's decisive
failure.

**Rescue attempt (same iteration budget):** a finer local sweep around the
near-miss config (length in [12,14,16,18], overbought/oversold pairs
65/35, 68/32, 70/30, 72/28) found a marginally better QQQ config
(length=14, overbought=72, oversold=28, Sharpe 0.974) -- still below the
1.0 threshold, and SPY at that same config drops further to 0.678. This
confirms the near-miss is a genuine ceiling rather than a tuning artifact;
not pursued further.

Strategy file (`strategies/2026-09-20_ehlers_stochastic_predictive.py`)
kept as a record of a rejected attempt (near-miss on QQQ) — not live.
