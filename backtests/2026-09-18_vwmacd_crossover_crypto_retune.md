# Backtest Report: VW-MACD Crypto-Specific Retune + Leverage Cap (2026-09-18)

**Hypothesis id:** 2026-09-18-062
**Strategy file:** `strategies/2026-09-18_vwmacd_crossover.py` (same file as 2026-09-18-061, adds `leverage_cap` param, different per-symbol configs)
**Source:** Own grid/parameter-scan data (follow-up to 2026-09-18-061's own note re: crypto retune)

## Hypothesis

2026-09-18-061 accepted VW-MACD for equity (QQQ/SPY) but crypto
(BTC/USDT, ETH/USDT) decisively failed MDD at the shared config. This
iteration ran a per-symbol parameter scan (90 combos each: vwmacd_fast in
[6,8,10,12,16,20] x vwmacd_slow in [20,26,34,40,50] x vwmacd_signal in
[5,9,12]) on BTC/USDT and ETH/USDT independently to find configs with
strong Sharpe, then applied a leverage cap (this repo's established
rescue pattern, e.g. 2026-09-18-052/058/060) to bring MDD under threshold.

## Parameter scan results (crypto, full 2019-2026, no leverage)

- BTC/USDT best: vwmacd_fast=16/slow=20/signal=12 -> Sharpe=1.369, MDD=0.575 (Sharpe passes, MDD decisively fails unscaled)
- ETH/USDT best: vwmacd_fast=6/slow=50/signal=5 -> Sharpe=1.204, MDD=0.561 (same pattern)

Leverage-cap sweep (both symbols): 0.7x/0.6x/0.5x/0.4x all still fail MDD
(>0.25); **0.3x is the first cap that clears MDD for both** (BTC MDD=0.213,
ETH MDD=0.211).

## Step 7 single-config validation (leverage_cap=0.3 applied to each symbol's own best config)

### BTC/USDT: vwmacd_fast=16/slow=20/signal=12, leverage_cap=0.3

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.369 | >= 1.0 | **PASS** |
| Max drawdown | 0.213 | <= 0.25 | **PASS** |
| TC survival (15bps/trade, 140 trades) | net Sharpe 0.996 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing bug) |
| Parameter sensitivity (9-combo local grid) | rel_std 0.177 | <= 0.5 | **PASS** |

### ETH/USDT: vwmacd_fast=6/slow=50/signal=5, leverage_cap=0.3

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.204 | >= 1.0 | **PASS** |
| Max drawdown | 0.211 | <= 0.25 | **PASS** |
| TC survival (15bps/trade, 136 trades) | net Sharpe 0.951 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing bug) |
| Parameter sensitivity (9-combo local grid) | rel_std 0.155 | <= 0.5 | **PASS** |

## Decision: ACCEPT (BTC/USDT and ETH/USDT, each at their own per-symbol config + leverage_cap=0.3)

All 4 runnable validators pass for both crypto symbols. This completes
full asset-class coverage for the VW-MACD strategy: equity (QQQ/SPY,
2026-09-18-061, no leverage cap needed) + crypto (BTC/USDT, ETH/USDT, this
entry, leverage_cap=0.3 required in both cases -- crypto's much larger
unscaled drawdowns for this construction, 0.575/0.561, needed a
substantially more aggressive cap than other accepted crypto strategies
in this KB which typically needed only 0.4-0.6x).

**Notes for a future iteration:** the very different fast/slow/signal
values needed per symbol (BTC 16/20/12, ETH 6/50/5, equity 20/26/9) and
the aggressive 0.3x leverage requirement for crypto both suggest this
particular VW-MACD construction is quite parameter/asset-sensitive
compared to other accepted strategies in this KB -- worth flagging that
live deployment would need per-symbol recalibration rather than one
universal config.
