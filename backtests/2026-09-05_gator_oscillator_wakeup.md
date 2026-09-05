# Gator Oscillator Wake-Up Trend Entry — QQQ/SPY/BTC/ETH (2026-09-05)

## Hypothesis

Gator Oscillator (dual histogram of |Jaw-Teeth| and |Teeth-Lips| Alligator
gaps) both bars flipping from contracting (red) to simultaneously
expanding (green) signals the Alligator "waking up" -- a fresh trend
starting. Long entry on this wake-up transition filtered by bullish line
ordering (Lips > Teeth > Jaw); exit when either gap turns red again, or a
max_hold_days time-stop. Source: QuantifiedStrategies.com Gator Oscillator
article (https://www.quantifiedstrategies.com/gator-oscillator/). Distinct
from the already-accepted (QQQ) Alligator Lips-crosses-both-lines strategy
(2026-09-04-112).

## Strategy file

`strategies/2026-09-05_gator_oscillator_wakeup.py`

## Step 6 — Grid test summary

Grid: `jaw_period in [13,21]` (teeth/lips periods held at standard 8/5) ×
`max_hold_days in [15,20,30]` (6 combos) × symbols `{QQQ, SPY, BTC/USDT,
ETH/USDT}` × 3 vol-regime terciles = 72 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 6/72 = 0.083** (weak)
- By asset class: equity 6/36 (0.167); **crypto 0/36 (0.0) — decisive fail**
- By vol regime: low 3/24 (0.125), mid 3/24 (0.125), high 0/24 (0.0)
- Best cell: `jaw_period=13, max_hold_days=15`, QQQ, mid-vol regime, Sharpe 1.04
- Worst cell: `jaw_period=13, max_hold_days=15`, QQQ, high-vol regime, Sharpe -0.96

## Step 7 — Single best-config validators

Config: `jaw_period=13, max_hold_days=15` (teeth=8/lips=5 default), full
sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.220 | -0.081 | ≥ 1.0 | QQQ ❌ / SPY ❌ |
| Max drawdown | 0.184 | 0.126 | ≤ 0.25 | QQQ ✅ / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | -0.048 | -0.367 | ≥ 0.5 | QQQ ❌ / SPY ❌ |
| Num trades | 145 | 155 | — | high trade frequency |
| Parameter sensitivity (relative_std, 6-cell sweep, QQQ) | 0.131 | — | ≤ 0.5 | ✅ |

`check_walk_forward` skipped (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED** (all symbols/asset classes)

Decisive failure. Full-period Sharpe is near-zero-to-negative on both QQQ
and SPY, and net-of-cost Sharpe is deeply negative on both (-0.05 QQQ,
-0.37 SPY) because the wake-up signal fires very frequently (145-155
trades over ~7.5 years) generating a lot of whipsaw noise that transaction
costs eat alive. Crypto rejected decisively across the grid (0/36 cells).
Parameter sensitivity itself is stable (relative_std 0.13) but stable
around a bad mean -- this is not a fragile-parameter near-miss, it's a
genuinely weak signal: the Gator's histogram-expansion "wake up" event is
too noisy/frequent on daily bars to be a standalone entry trigger, unlike
the related Alligator Lips-crossover strategy (2026-09-04-112, accepted
QQQ) which requires a stronger, less frequent crossover condition.
