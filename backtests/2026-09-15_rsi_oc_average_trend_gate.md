# 2026-09-15 RSI on Open-Close Average (Ehlers) Trend-Gated Mean Reversion

**Hypothesis:** Per Financial Hacker
(https://financial-hacker.com/open-or-close-why-not-both/), John Ehlers
(TASC Feb 2023) proposed using OC=(Open+Close)/2 rather than raw close as
the indicator input series for noise reduction. Source's own test found
"no clear tendency." This iteration tests RSI(OC-average,14) 30/70
crossover gated by an SMA(200) uptrend filter, more rigorously than the
source's own quick unfiltered check. First open-close-average-input
technique in this repo.

**Best joint-ish config:** rsi_period=14, oversold_threshold=30,
max_hold_days=20

## Single-config validator results (full 2018-2026 sample)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | 0.553 (**FAIL** decisive, thr 1.0) | 0.165 (pass) |
| SPY | 0.514 (**FAIL** decisive, thr 1.0) | 0.060 (pass) |

## Grid summary (rsi_period in [10,14,21] x oversold_threshold in
[25,30,35] x max_hold_days in [10,20], QQQ/SPY/BTC-USDT/ETH-USDT x
low/mid/high vol tercile, 216 cells)

- pass_fraction: 0.102 (22/216) -- one of the weakest grid results in this
  repo's history
- by_asset_class: equity 16/108; crypto 6/108
- No single parameter combo achieves a 3/3 vol-tercile pass on BOTH QQQ
  and SPY simultaneously; best per-symbol combos top out at 2/3.

## Outcome: REJECTED (both QQQ and SPY decisive full-sample Sharpe fail;
crypto also decisive)

Confirms the source's own honest caveat that the open-close-average
noise-reduction trick showed "no clear tendency" to improve results --
here, gated by a trend filter and tested with a proper grid/full-sample
validator suite, it performs decisively worse than this repo's many other
already-tested RSI variants (most of which cluster around Sharpe
0.6-1.5+). The half-bar-lag cost the source itself flagged appears to
outweigh the modest noise reduction for this particular oversold-bounce
construction. Not pursued further this cron trigger -- the technique
itself (rather than a specific parameter choice) appears to be the
limiting factor.
