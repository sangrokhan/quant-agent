# Backtest Report: IBS Range-Band Mean Reversion with Exhaustion Exit

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_ibs_rangeband_exhaustion_exit.py`
**Hypothesis id:** 2026-09-27-046

## Hypothesis

Per Quantitativo's "Murphy's Law: How a fragile mean reversion idea became
a +1.2 Sharpe strategy" (https://www.quantitativo.com/p/murphys-law, read
via `browser_exec` this iteration — `web_search`'s DDGS backend returned
empty/irrelevant results for several queries attempted, resolved via
Google SERP directly), switching a mean-reversion strategy's exit rule
from a plain "close > prior day's high" breakout exit to a dynamic
EXHAUSTION exit (IBS > 0.9 OR RSI(2) > 90) improved the source's own
expected-return-per-trade from +0.90% to +1.04% per trade (t-stat=5.37,
p=0.0). This repo already has the underlying entry logic tested with
other exits (2026-09-09-041 dynamic-SMA-stop exit, 2026-09-08-133 plain
breakout exit) but not this specific exhaustion-exit combination.

## Grid test summary (Step 6)

`param_grid={"band_mult": [2.0, 2.5, 3.0], "entry_ibs": [0.2, 0.3],
"exit_ibs": [0.85, 0.9]}`, symbols equity=[QQQ, SPY] crypto=[BTC/USDT,
ETH/USDT], `vol_regime_splits=3`, sample 2019-01-01 to 2026-09-01.

- **total_cells:** 144, **passed_cells:** 34, **pass_fraction:** 0.236
- **by_asset_class:** equity 34/72 (0.47), crypto 0/72 (0.0 — decisive
  crypto reject at every param combo/vol-regime tested)
- **by_vol_regime:** low 24/48 (0.50), mid 1/48 (0.02), high 9/48 (0.19)
  — edge is concentrated in low-vol regimes, mirroring this repo's usual
  pattern for range-band mean-reversion entries.
- **best_cell:** QQQ, low-vol, `band_mult=2.0/entry_ibs=0.2/exit_ibs=0.85`,
  Sharpe 2.42
- **worst_cell:** BTC/USDT, low-vol, `band_mult=2.0/entry_ibs=0.3/exit_ibs=0.85`,
  Sharpe -0.84

## Single-config validation (Step 7) — best cell config, full sample

Config: `band_mult=2.0, entry_ibs=0.2, exit_ibs=0.85` (default `exit_rsi=90`,
`trend_window=200`, `max_hold_days=15`).

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **PASS** 1.285 | FAIL 0.552 |
| Max drawdown (<=0.25) | PASS 0.080 | PASS 0.105 |
| Transaction-cost survival (net Sharpe >=0.5, 10bps/trade) | **PASS** 1.083 (83 trades) | FAIL 0.378 (63 trades) |
| Walk-forward (manual 4-split substitute, pass_fraction>=0.75) | **PASS** 1.0 (4/4 splits positive) | FAIL 0.5 (2/4 splits positive) |
| Parameter sensitivity (relative_std<=0.5, 27-cell local grid) | PASS 0.149 | PASS 0.262 |

QQQ: **all 5 validators pass**. SPY: fails Sharpe, TC-survival, and
walk-forward at the same config (edge doesn't transfer cleanly to SPY at
this parameterization). Crypto (BTC/USDT, ETH/USDT): decisively rejected
across the entire grid (0/72 cells) — the 200-day SMA trend gate combined
with this specific range-band construction does not translate to crypto's
different vol/liquidity regime, consistent with prior similar entries in
this repo (2026-09-09-041, 2026-09-08-133 both equity-only accepts).

## Decision

**Accepted for QQQ only** (`entry_ibs=0.2, exit_ibs=0.85, band_mult=2.0`).
SPY and crypto rejected at this config; SPY is a near-miss (Sharpe 0.552 is
not close enough to 1.0 for a superficial retune to be promising without
further investigation, unlike some prior 0.9-x near-misses in this repo —
left as a possible future per-symbol retune candidate, not pursued further
this iteration).
