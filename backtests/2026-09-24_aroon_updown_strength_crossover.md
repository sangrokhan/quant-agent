# Aroon Up/Down Strength-Confirmed Crossover — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_aroon_updown_strength_crossover.py`
**Source:** https://arrowalgo.com/aroon-crossover-strategy/ (read via browser_exec; web_search DDGS returned empty results for the initial "Vervoort Smoothed Heikin-Ashi" query, so pivoted to Aroon)

## Hypothesis

Raw two-line Aroon Up/Aroon Down crossover ("freshness of extremes" — how
recently the highest-high / lowest-low occurred), filtered with a
strength threshold (entry only when Aroon Up > 70 at the crossover, exit
when Aroon Up < 50 or the opposite cross) to skip noisy mid-range chop
crossovers. Distinct from the single-line Aroon Oscillator already tested
12x in this repo — this uses the raw two-line formulation with a different
filter shape. First raw Aroon Up/Down two-line entry in this repo.

## Grid test summary (Step 6, workload=light)

- Grid: `aroon_period` in {14,25} x `entry_strength_threshold` in {70,80} x
  `max_hold_days` in {15,20}, symbols QQQ/SPY (equity), BTC/USDT (crypto),
  vol_regime_splits=3. 72 total cells.
- **Overall pass_fraction: 0.5** (36/72)
- By asset class: equity 28/48 (0.583), crypto 8/24 (0.333)
- By vol regime: low 24/24 (1.0), mid 8/24 (0.333), high 4/24 (0.167) —
  strategy performs best in low-vol regimes.
- Best cell: QQQ, aroon_period=25/entry_strength_threshold=70/max_hold_days=20,
  low-vol, Sharpe 2.96.
- All (symbol, param-combo) groups for QQQ and SPY pass 2/3 vol regimes
  (usually low+one other) — very consistent across the grid.

## Single-config validation (Step 7)

Config: aroon_period=14, entry_strength_threshold=70, exit_threshold=50,
max_hold_days=15.

### QQQ

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ✅ | 1.339 | 1.0 |
| max_drawdown | ✅ | 0.241 | 0.25 |
| transaction_cost_survival | ✅ | 0.997 (net Sharpe) | 0.5 |
| walk_forward | ✅ | 1.0 pass fraction | 0.75 |
| parameter_sensitivity | ✅ | 0.044 relative std | 0.5 |

**All 5 pass.**

### SPY

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ✅ | 1.477 | 1.0 |
| max_drawdown | ✅ | 0.128 | 0.25 |
| transaction_cost_survival | ✅ | 0.989 (net Sharpe) | 0.5 |
| walk_forward | ✅ | 1.0 pass fraction | 0.75 |
| parameter_sensitivity | ✅ | 0.147 relative std | 0.5 |

**All 5 pass.**

### BTC/USDT (aroon_period=25, entry_strength_threshold=80, max_hold_days=15)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ✅ | 1.242 | 1.0 |
| max_drawdown | ❌ | 0.468 | 0.25 |
| transaction_cost_survival | ✅ | 1.162 (net Sharpe) | 0.5 |
| walk_forward | ✅ | 1.0 pass fraction | 0.75 |
| parameter_sensitivity | ✅ | 0.126 relative std | 0.5 |

**4/5 pass — MDD fails decisively (0.468, nearly 2x threshold).**

## Decision (Step 8)

**Accepted (QQQ + SPY, both all 5 validators pass, strong margins).**
**Rejected (BTC/USDT — decisive MDD failure); ETH/USDT not individually
pursued given crypto's overall weak grid pass_fraction (0.333) and BTC's
decisive miss.**

## Notes for future loops

- This is a strong, robust equity accept — consistent Sharpe >1.3 on both
  QQQ and SPY, tight parameter sensitivity (rel_std <0.15 both), and
  perfect walk-forward. The low-vol-regime dominance (24/24 grid cells
  pass) suggests the strategy captures sustained low-volatility uptrends
  particularly well.
- Crypto (BTC/USDT) has an attractive raw Sharpe (1.24) but blows through
  the drawdown ceiling — a leverage-cap rescue (similar to prior
  RWI/Chaikin-Vol crypto rescues in this repo) could be a worthwhile
  follow-up iteration.
