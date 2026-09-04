# Awesome Oscillator Bullish Twin Peaks (QQQ) — REJECTED (near-miss, sparse signal)

**Hypothesis:** Bill Williams' Awesome Oscillator (AO = SMA(5,median) -
SMA(34,median)) Bullish Twin Peaks: AO below zero, two swing lows with
the second higher than the first (rising-bottoms divergence), confirmed
by AO ticking up on the bar after the second low. Long entry gated by
close > 200d SMA; exit on AO crossing below zero, trend break, or
max_hold_days time-stop.

**Source:** https://www.tradingsim.com/blog/awesome-oscillator (rates
Twin Peaks their favorite of the 3 common AO strategies).

**Novelty:** Distinct from the raw AO zero-line-cross (2026-09-04-041,
near-miss Sharpe 0.89) and Bullish Saucer (2026-09-04-111) strategies
already tested in this repo — Twin Peaks is specifically a
higher-low/bullish-divergence pattern below zero.

## Best config: swing_window=3, max_hold_days=10 (QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.988 | >= 1.0 | **FAIL (near-miss)** |
| Max drawdown | 0.77% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 8 trades) | net Sharpe 0.949 | >= 0.5 | PASS |
| Walk-forward | SKIPPED | n/a | Repo-wide `vectorbt.utils.splitting` API issue, see 2026-09-04-154 |
| Parameter sensitivity | not computed | n/a | Grid pass_fraction (9.7%) and trade sparsity already decisive |

Only 8 trades over the full 7.7-year sample — the compound "two rising
swing lows below zero + confirmation bar + uptrend filter" condition is
very rare, similar to the sparse-signal problem noted for Mass Index
(2026-09-04-075).

## Step 6 grid summary (swing_window in [2,3,4] x max_hold_days in [10,15], symbols QQQ/SPY equity + BTC/ETH crypto, vol_regime_splits=3)

- **Overall pass_fraction: 9.7%** (7/72 cells)
- **By asset class:** equity 7/36 (19.4%); crypto 0/36 (0%).
- **By vol regime:** low 0/24, mid 3/24, high 4/24 — no low-vol passes at all, unusual compared to most other mean-reversion/oscillator strategies in this repo which tend to concentrate in low-vol.
- **Best cell:** QQQ, swing_window=3, max_hold_days=10, mid-vol regime, Sharpe 1.36.

## Decision: REJECT (near-miss, sparse signal)

Full-sample QQQ Sharpe (0.988) is essentially at the 1.0 threshold and
both MDD and TC-survival pass comfortably, but only 8 trades occur over
7.7 years — too few observations to trust the Sharpe estimate as
statistically meaningful, and consistent with the broader pattern in this
repo (see Mass Index 2026-09-04-075) that highly compound
multi-condition setups (divergence + confirmation + trend filter) produce
too sparse a signal for reliable standalone testing. A future loop could
either (a) drop the trend filter requirement to generate more signals and
re-test, since Twin Peaks is itself already a contrarian/divergence
condition that may not need an additional trend gate, or (b) test it as a
confirmation LAYER on top of an already-passing trend-following signal
rather than as a standalone entry.
