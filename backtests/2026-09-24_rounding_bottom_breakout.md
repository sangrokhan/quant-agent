# Backtest Report: Bulkowski Rounding Bottom Breakout (QQQ accepted, SPY near-miss)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_rounding_bottom_breakout.py`
**Source:** https://thepatternsite.com/roundb.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec — web_search's
DDGS backend returned unrelated/garbage results this iteration).

## Hypothesis
Rounding Bottom: a smooth, gradual U-shaped ("bowl") decline-then-recovery,
usually after a prior uptrend (67% act as continuation patterns per the
source). Confirmation = close above the "left saucer lip" (source's own
disclosed rule: "I use a close above the left peak because price on the
right might not pause at a minor high"). Per the source's own published
statistics, this pattern has a **break-even failure rate of only 4%** and
ranks 7th out of 39 bullish patterns overall — one of the strongest (lowest
failure) priors this repo has sourced from Bulkowski's catalog so far,
stronger than both the Rectangle Top (15% failure) and Three Rising
Valleys patterns already accepted this cron trigger. First "Rounding
Bottom" entry in this repo (0 prior index hits).

## Grid summary (Step 6)
`param_grid={"bowl_window": [40, 60, 90], "center_tolerance": [0.25, 0.35]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3` (normal workload).

- total_cells: 72, passed_cells: 17, **pass_fraction: 0.236**
- by_asset_class: equity 15/36, crypto 2/36
- by_vol_regime: low 10/24, mid 3/24, high 4/24
- best_cell: bowl_window=90, center_tolerance=0.35, QQQ, low-vol, Sharpe 2.265

## Single-config validators (best cell: bowl_window=90, center_tolerance=0.35)

### QQQ
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 64 trades) | **PASS** | 1.213 | >= 1.0 |
| Max drawdown | **PASS** | 0.136 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **PASS** | net Sharpe 1.095 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` bug |
| Parameter sensitivity (20-combo sweep) | **PASS** | rel_std 0.323 | <= 0.5 |

### SPY (same config, near-miss)
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 68 trades) | **FAIL (near-miss)** | 0.760 | >= 1.0 |
| Max drawdown | PASS | 0.161 | <= 0.25 |
| Transaction cost survival | PASS | net Sharpe 0.598 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | same repo bug |
| Parameter sensitivity | PASS | rel_std 0.257 | <= 0.5 |

## Decision: ACCEPT (QQQ only), NEAR-MISS/REJECT (SPY)
QQQ clears every runnable validator with comfortable margin. SPY is a
genuine near-miss — only Sharpe fails (0.760 vs 1.0), every other
validator passes cleanly with good margin — flagged as a rescue candidate
for a future iteration (e.g. per-symbol config retune, this repo's
established rescue pattern). Crypto not pursued (grid showed only 2/36
crypto cells passing, weaker than either equity symbol).
