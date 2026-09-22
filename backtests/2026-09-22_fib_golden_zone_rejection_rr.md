# Fibonacci Golden-Zone Rejection + Fixed R:R (QQQ) — REJECTED

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_fib_golden_zone_rejection_rr.py`
**Source:** Google AI Overview (2026-09-22) synthesizing apptrading.ai / FX
Replay / Smart Risk content, plus
https://www.vtmarkets.com/discover/fibonacci-retracement-levels-a-practical-trading-guide/
for level definitions.

## Hypothesis
Distinct from prior KB entries 2026-09-03-022 (near-miss, zone-based entry,
swing-breakout exit) and its rescue 2026-09-20-086 (also rejected): this
iteration tested a more specific 3-part rule the source article gives:
EMA(50)>EMA(200) trend filter, a rejection-candle trigger AT the 61.8%
level specifically (wick pierce + close-back-above), and a fixed 2:1 R:R
exit via ATR stop beyond the 78.6% level.

## Grid summary (swing_lookback∈{20,30,50}, rr_multiple∈{1.5,2.0}, equity QQQ/SPY + crypto BTC/ETH, 3 vol terciles)
- pass_fraction: 0.111 (8/72 cells)
- by_asset_class: equity 8/36, crypto 0/36 (crypto decisive fail)
- by_vol_regime: low 6/24, mid 2/24, high 0/24
- Best QQQ aggregate config: swing_lookback=20, rr_multiple=2.0, avg Sharpe
  0.81 (2/3 vol regimes passed)

## Single-config validation (QQQ, swing_lookback=20, rr_multiple=2.0, atr_stop_mult=1.0)
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.579 | ≥1.0 |
| Max drawdown | **FAIL** | 26.5% | ≤25% |
| Transaction cost survival (10bps, 135 trades) | **FAIL** | net Sharpe 0.415 | ≥0.5 |
| Walk-forward (4 splits) | pass | 100% positive | ≥75% |
| Parameter sensitivity | **FAIL** | rel std 0.647 | ≤0.5 |

## Decision: REJECT
Decisive failure on 4 of 5 validators (only walk-forward passes). The
rejection-candle-at-exact-61.8%-level trigger is far more restrictive than
the zone-based entry of the prior attempts, and combined with the fixed
2:1 R:R exit produces mediocre risk-adjusted returns that don't clear the
Sharpe/MDD/cost/sensitivity bars. Crypto fails entirely (0/36 cells) —
same qualitative conclusion as prior Fibonacci-family entries: this
indicator family does not translate well to BTC/ETH's noisier/near-random-
walk dynamics on daily bars.

## Notes
This is now the 3rd Fibonacci-retracement-pullback variant tested in this
repo (2026-09-03-022 zone-entry/swing-exit near-miss, 2026-09-20-086 direct
param-retune rescue also rejected, this entry's rejection-candle+fixed-R:R
variant also rejected). The core 61.8% pullback continuation concept does
not appear robust on this repo's equity/crypto universe across multiple
distinct implementations of entry/exit mechanics. Future loops should treat
this indicator family as effectively exhausted unless a genuinely novel
mechanic (e.g. multi-timeframe confluence, volume-at-level confirmation)
surfaces from research.
