# 2026-09-18 — Ehlers Synthetic Oscillator, low-vol-gate rescue (fails, rejected)

## Rescue hypothesis

Direct rescue attempt for near-miss id 2026-09-18-077 (Ehlers Synthetic
Oscillator momentum crossover, TASC April 2026, unchanged source
https://traders.com/Documentation/FEEDbk_docs/2026/04/TradersTips.html).
Parent grid found edge concentrated in low-vol regime cells
(low 18/36 pass, mid 6/36, high 0/36) with both equity symbols near-missing
full-sample Sharpe (QQQ 0.971, SPY 0.870). This sub-iteration reused the
identical filter-chain implementation and added this repo's standard
low-vol regime gate (20d realized vol <= trailing 252d median) to the entry
condition, plus fixed the parent's flagged crypto data issue by using
DAILY crypto bars (interval="1d") instead of hourly.

## Grid summary

`grid_cells_synthosc_volgate.json` — 216 cells: hann_length in {8,12,16} x
max_hold_days in {15,20,30} x vol_regime_ratio in {0.8,1.0}, QQQ/SPY +
BTC/USDT/ETH/USDT (now daily bars), vol_regime_splits=3.

- Overall pass_fraction: 27/216 = 12.5%
- by_asset_class: equity 18/108 (16.7%), crypto 9/108 (8.3%)
- by_vol_regime: low 27/72 (37.5%), mid 0/72, high 0/72 — as intended, the
  gate concentrates trading in low-vol conditions, but this REDUCED the
  overall pass_fraction vs the parent's ungated version (parent: 22.2%
  overall). Fixing crypto to daily bars did help crypto marginally
  (parent crypto 0/54; this iteration 9/108).

## Full-sample validators (2019-01-01 to 2026-09-01)

`validators_synthosc_volgate.json`.

| Symbol | Sharpe | MDD | TC-net-Sharpe | Walk-forward | Param-sensitivity |
|---|---|---|---|---|---|
| QQQ (hann=12/hold=15) | 0.413 (fail, thr 1.0) | 0.147 (pass) | 0.266 (fail, thr 0.5) | 1.0 (pass, 4/4) | 2.817 (fail, thr 0.5) |
| ETH/USDT (hann=16/hold=30) | 0.982 (fail, thr 1.0, near-miss) | 0.464 (fail, thr 0.25) | 0.932 (pass) | 1.0 (pass, 4/4) | 0.574 (fail, thr 0.5) |

The vol gate made QQQ's full-sample Sharpe WORSE (0.413 vs. the parent's
unconditional-entry 0.971 near-miss) — restricting entries to low-vol
regimes cut the trade count enough (66 trades) that the remaining sample is
noisier/less representative, and parameter-sensitivity is now catastrophic
(2.82 relative std) since different hann_length choices produce wildly
different (sometimes near-zero) trade counts under the gate. ETH/USDT
improved slightly on daily bars (Sharpe 0.982 near-miss vs parent's hourly
0.086 decisive fail) but MDD is still 2x the budget (0.464) and
param-sensitivity narrowly fails (0.574 vs 0.5).

## Decision: REJECT

The low-vol regime gate does not rescue the parent near-miss — it makes
QQQ's full-sample performance worse, and while it substantially improves
ETH/USDT (by fixing the hourly/daily data mismatch, not the vol gate
itself), MDD and parameter-sensitivity still fail. This confirms the
parent's own observation that the edge is concentrated in low-vol regimes
was correct directionally, but gating on it isn't sufficient to rescue
full-sample robustness — the underlying oscillator crossover signal itself
appears too noisy/parameter-sensitive across all regimes. Future rescue
angle: instead of a binary vol gate, try a continuous-sizing-dial pattern
(this repo's established fix for near-misses like this, e.g. Andean/GAPO/BBW)
scaling exposure by vol rather than gating entirely, or add an explicit
stop-loss to contain ETH/USDT's MDD.

Source: https://traders.com/Documentation/FEEDbk_docs/2026/04/TradersTips.html
(unchanged from parent 2026-09-18-077; no new external research this
sub-iteration).
