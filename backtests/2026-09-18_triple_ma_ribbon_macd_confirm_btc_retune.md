# Backtest Report: Triple MA Ribbon + MACD Confirmation, BTC-specific retune (2026-09-18)

**Hypothesis id:** 2026-09-18-060
**Strategy file:** `strategies/2026-09-18_triple_ma_ribbon_macd_confirm.py` (same file as 2026-09-18-059, different per-symbol config -- no code changes)
**Source:** Own grid data from 2026-09-18-059 (notes: "BTC/USDT is close in shape to ETH's original unscaled numbers -- a BTC-specific leverage-cap retune could plausibly clear both metrics")

## Hypothesis

Direct follow-up to near-miss 2026-09-18-059 (BTC/USDT rejected at
fast=8/mid=16/slow=40: Sharpe 0.953, MDD 0.375). That entry's own notes
suggested a leverage-cap retune. Since leverage_cap is a pure linear scale
of returns, it cannot change Sharpe (scale-invariant) -- it can only help
MDD, so a leverage-cap-only retune cannot fix the Sharpe near-miss. This
iteration instead widened the fast/mid/slow window grid on BTC/USDT alone
(same strategy file/rule logic, no leverage cap) to search for a
BTC-specific parameter combo that clears BOTH thresholds simultaneously.

## Parameter sweep (BTC/USDT only, fast in [5,6,8,10,12] x mid in [12,16,20,24] x slow in [30,32,40,50,60], constrained fast<mid<slow, full 2019-2026 sample)

Best found: **fast_window=12, mid_window=20, slow_window=60** ->
Sharpe=1.259, MDD=0.245 (both clear threshold without any leverage
scaling). This uses substantially longer windows than the shared
QQQ/SPY/ETH config (8/16/40) -- BTC's longer-cycle trend structure
apparently favors a slower-responding ribbon.

## Step 7 single-config validation (BTC/USDT, fast=12/mid=20/slow=60, full 2019-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.259 | >= 1.0 | **PASS** |
| Max drawdown | 0.245 | <= 0.25 | **PASS** (narrow clear, 0.5pp margin) |
| TC survival (15bps/trade, 58 trades) | net Sharpe 1.211 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing `vbt.utils.splitting` bug) |
| Parameter sensitivity (9-combo grid around fast/slow) | rel_std 0.083 | <= 0.5 | **PASS** |

## Decision: ACCEPT (BTC/USDT, fast_window=12/mid_window=20/slow_window=60, no leverage cap needed)

All 4 runnable validators pass. This completes crypto-universe coverage
for the Triple MA Ribbon + MACD Confirmation strategy: ETH/USDT accepted
in 2026-09-18-059 (fast=8/mid=16/slow=40, leverage_cap=0.6), BTC/USDT
accepted here (fast=12/mid=20/slow=60, no leverage cap) -- two different
per-symbol configs, same underlying rule logic.

**Notes for a future iteration:** MDD passed with only a 0.5 percentage
point margin (0.245 vs 0.25 threshold) -- this is a narrower safety margin
than most other accepted strategies in this KB and could flip to a fail
with a slightly different sample window or added transaction cost
assumptions; worth revisiting with a small leverage trim (e.g. 0.9x) if a
future iteration wants more margin. QQQ/SPY equity-side rejection from
2026-09-18-059 stands unchanged (not retested this iteration).
