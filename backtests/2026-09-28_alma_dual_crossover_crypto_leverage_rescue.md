# ALMA Dual Crossover, Crypto Leverage-Cap Rescue (2026-09-28)

## Hypothesis

Direct rescue attempt for this same cron trigger's own near-miss
(2026-09-28-050, plain ALMA dual crossover, BTC/USDT and ETH/USDT both
passed Sharpe/TC-survival/walk-forward/param-sensitivity but decisively
failed max-drawdown at full leverage: 0.584 and 0.537 vs the 0.25 cap).
Applies this repo's established successful leverage-cap-recalibration
rescue pattern (previously validated for BOS BTC/USDT at leverage_cap=0.7,
Elder-Ray/Chaikin-Oscillator/Twiggs-Money-Flow/Ultimate-Oscillator in
earlier iterations): scales position size to a fixed `leverage_cap`
fraction instead of full 1.0 exposure while in a trade. No new external
source consulted -- internal parameter rescue of this cron trigger's own
prior iteration.

## Strategy

`strategies/2026-09-28_alma_dual_crossover_crypto_leverage_rescue.py` --
identical entry/exit logic to the parent (ALMA(14) crosses above ALMA(34)
-> long at `leverage_cap` size; crosses below -> exit; 60-day time-stop),
only the position sizing constant changes.

## Leverage sweep (fast=14, slow=34, full-sample Sharpe/MDD)

| leverage_cap | BTC/USDT Sharpe | BTC/USDT MDD | ETH/USDT Sharpe | ETH/USDT MDD |
|---|---|---|---|---|
| 0.3 | 1.083 | **0.209 PASS** | 1.085 | **0.178 PASS** |
| 0.4 | 1.083 | 0.271 FAIL | 1.085 | 0.235 PASS |
| 0.5 | 1.083 | 0.329 FAIL | 1.085 | 0.290 FAIL |
| 0.6 | 1.083 | 0.384 FAIL | 1.085 | 0.344 FAIL |
| 0.7 | 1.083 | 0.437 FAIL | 1.085 | 0.396 FAIL |

Sharpe is leverage-invariant for this pure long/flat exposure (no vol
targeting); only MDD scales with leverage. leverage_cap=0.3 is the largest
value that clears MDD on BOTH symbols with a single shared config.

## Full validator suite at leverage_cap=0.3

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel_std) | Trades | Result |
|---|---|---|---|---|---|---|---|
| BTC/USDT | 1.083 (PASS >=1.0) | 0.209 (PASS <=0.25) | 0.953 (PASS >=0.5) | 1.00 (PASS >=0.75) | 0.087 (PASS <=0.5) | 91 | **ALL PASS** |
| ETH/USDT | 1.085 (PASS) | 0.178 (PASS) | 0.990 (PASS) | 1.00 (PASS) | 0.116 (PASS) | 96 | **ALL PASS** |

Walk-forward computed manually (4 equal-length splits) per this repo's
established workaround (vectorbt.utils.splitting.RangeSplitter
unavailable in the installed version).

## Decision

**Accept for crypto (BTC/USDT, ETH/USDT) at leverage_cap=0.3.** Combined
with the parent's equity accept (QQQ/SPY at full leverage), the ALMA dual
crossover is now a full-universe accepted strategy family: full-leverage
equity + leverage-capped (0.3x) crypto.

Files:
- `strategies/2026-09-28_alma_dual_crossover_crypto_leverage_rescue.py` (kept, live for BTC/ETH)
- `validate_result_alma_crypto_leverage_rescue.json`
