# Backtest Report: Funding-Rate Momentum (Rate-of-Change) Contrarian Reversal

**Strategy file:** `strategies/2026-09-26_funding_rate_momentum_roc_reversal.py`
**KB id:** 2026-09-26-064
**Outcome:** REJECTED (decisive)

## Hypothesis

Source: https://www.chelseawelding.com/funding-rate-momentum-reversal-strategy-backtest-results/
(trading blog backtest writeup; read via `browser_exec` after `web_extract`'s
configured DDGS backend refused non-search URL extraction).

The source claims the **rate of change (momentum)** of the perpetual funding
rate — not its raw level — signals crowd-conviction extremes better: a
3-period hourly ROC beyond ±0.08% predicts a short-term reversal, faded
counter to the ROC direction. Adapted here to this repo's daily-summed
funding convention (established in 2026-09-20-031): a z-scored `roc_window`-day
rate-of-change of the daily-summed funding series, faded with a fixed
`max_hold_days` time-stop.

Distinct from every other funding-rate construction in this KB (level
threshold, level z-score sizing dial, level trend-confirmation gate, level
divergence state machine) — this is the first to use the **derivative** of
funding rather than its level.

## Grid summary (Step 6)

`param_grid={roc_window:[3,5], momentum_zscore_threshold:[1.5,2.0,2.5], max_hold_days:[3,5]}`,
symbols crypto-only (`BTC/USDT`, `ETH/USDT` — funding has no equity analog),
`vol_regime_splits=3`, 72 total cells.

| Metric | Value |
|---|---|
| pass_fraction | 0.083 (6/72) |
| by_vol_regime | low 1/24, mid 2/24, high 3/24 |
| best_cell | BTC/USDT, roc_window=5, threshold=1.5, hold=5, mid-vol tercile, Sharpe 1.73 |
| worst_cell | ETH/USDT, same params, low-vol tercile, Sharpe -1.25 |

The "best cell" was a narrow single-vol-tercile artifact.

## Single-config validation (Step 7) — best cell, full sample, BTC/USDT

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | -0.086 | ≥ 1.0 |
| Max drawdown | **FAIL** | 0.592 | ≤ 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe -0.100 (2232 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken in this install, per established repo workaround) | **FAIL** | 1/4 splits positive (0.25) | ≥ 0.75 |

All validators decisively fail on the full sample despite the promising
grid best-cell Sharpe — consistent with this KB's repeated finding that
funding-rate **momentum/derivative** constructions are noisier and more
overfit to narrow windows than level-based constructions (cf. accepted
2026-09-20-031 level-based sizing dial).

## Decision

**Reject.** Strategy file retained in `strategies/` as a rejected-attempt
record (not live).
