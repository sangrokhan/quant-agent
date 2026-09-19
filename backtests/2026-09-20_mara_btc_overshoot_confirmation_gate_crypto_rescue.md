# MARA/BTC Overshoot Confirmation Gate — Crypto Leverage-Cap Rescue (Iteration 5)

**Direct follow-up to accepted 2026-09-20-043** (QQQ+SPY accepted at full
exposure; BTC/USDT and ETH/USDT decisively rejected on max-drawdown at
leverage_cap=1.0 despite occasionally clearing Sharpe).

## Fix

Added a `leverage_cap` parameter to `generate_signals`/`generate_returns`
(default 1.0, unchanged behavior for equity legs) — same established
leverage-cap-aware retune pattern used throughout this repo for crypto
legs of money-flow/sizing-dial strategies. Swept `leverage_cap in
{0.3,0.4,0.5,0.6}` on BTC/USDT and ETH/USDT at their best-found configs
from -043's grid.

| Symbol | leverage_cap | trend_sma_window | zscore_window | entry_z | Sharpe | MDD |
|---|---|---|---|---|---|---|
| BTC/USDT | 0.3 | 50 | 40 | 0.7 | 1.086 | 0.086 |
| BTC/USDT | **0.4** | 50 | 40 | 0.7 | **1.086** | **0.113** |
| ETH/USDT | **0.4** | 50 | 40 | 0.7 | **1.100** | **0.130** |

`leverage_cap=0.4` chosen for both symbols (comfortable margin under the
0.25 MDD threshold while keeping Sharpe above 1.0).

## Full-sample validators (leverage_cap=0.4)

**BTC/USDT** (tw=50/zw=40/entry_z=0.7):

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.086 | >= 1.0 | PASS |
| Max drawdown | 0.113 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 152 trades) | 0.764 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 1.00 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo local grid) | 0.126 | <= 0.5 | PASS |

**ETH/USDT** (tw=50/zw=40/entry_z=0.7):

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.100 | >= 1.0 | PASS |
| Max drawdown | 0.130 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 166 trades) | 0.842 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 1.00 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo local grid) | 0.094 | <= 0.5 | PASS |

QQQ sanity-checked unaffected by the `leverage_cap` param addition
(default 1.0, Sharpe 1.626 unchanged from -043).

## Decision

**ACCEPT for BTC/USDT and ETH/USDT** at `leverage_cap=0.4` (both pass all
5 validators). Combined live scope after this sub-iteration: ALL FOUR
symbols (QQQ, SPY at leverage_cap=1.0; BTC/USDT, ETH/USDT at
leverage_cap=0.4) — a full 4-for-4 acceptance for this strategy family,
the first in this repo's mNAV/leveraged-beta cross-asset campaign this
cron trigger to clear every tested symbol.
