# Awesome Oscillator Saucer Continuation — QQQ (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ao_saucer_continuation.py`
**KB id:** 2026-09-22-006

## Hypothesis

Per TradingStrategyGuides' disclosed rule
(https://tradingstrategyguides.com/bill-williams-awesome-oscillator-strategy/):
AO = SMA(median_price,5) - SMA(median_price,34). A bullish "Saucer" signals
momentum continuation: AO above zero, two consecutive declining (red) bars,
then a 3rd bar ticking back up (green) higher than the 2nd. Distinct from
this repo's 5 prior Awesome Oscillator entries (zero-line crossover, Twin
Peaks divergence) -- first test of the Saucer-specific 3-bar continuation
pattern.

## Grid test summary (Step 6)

`param_grid={max_hold_days:[10,15,20]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 36 cells total.

- Overall pass_fraction: 0.333 (12/36)
- By asset class: equity 8/18, crypto 4/18
- By vol regime: low 10/12, mid 2/12, high 0/12 (edge concentrated
  entirely in low-vol; high-vol regime decisively fails, negative Sharpes
  on both equity symbols)
- Best cell: SPY, max_hold_days=20, low-vol, Sharpe=2.80
- QQQ max_hold_days=10 and 20 both passed low+mid vol regimes (2/3 each);
  max_hold_days=10 selected as primary config (shorter hold, closer to the
  source's own continuation-trade framing).

## Single-config validation (Step 7) — QQQ, max_hold_days=10

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.082 | ≥1.0 | ✅ |
| Max drawdown | 0.175 | ≤0.25 | ✅ |
| TC survival (10bps/trade, 63 trades) | net Sharpe 0.940 | ≥0.5 | ✅ |
| Walk-forward (4 splits) | 1.0 pass fraction | ≥0.75 | ✅ |
| Parameter sensitivity (max_hold_days∈{8,10,12,15}) | rel std 0.182 | ≤0.5 | ✅ |

**All 5 validators pass on QQQ.**

## SPY (same params) — near-miss, NOT accepted

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 0.942 | ≥1.0 | ❌ |
| Max drawdown | 0.083 | ≤0.25 | ✅ |
| TC survival | net Sharpe 0.768 | ≥0.5 | ✅ |
| Walk-forward | 0.75 | ≥0.75 | ✅ (exactly at threshold) |
| Param sensitivity | 0.139 | ≤0.5 | ✅ |

SPY fails only Sharpe (4/5 pass) -- near-miss, not accepted this iteration.

## Decision

**Accept for QQQ only** (max_hold_days=10). SPY near-miss (Sharpe 0.942,
otherwise clean) -- reject this iteration, flagged for a future rescue.
Crypto grid results mixed (4/18 pass) but no config held up across all 3
vol regimes on either BTC or ETH -- not pursued as a primary accept target
this iteration.
