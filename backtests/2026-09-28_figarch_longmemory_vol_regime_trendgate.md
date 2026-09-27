# Backtest Report: FIGARCH (Baillie, Bollerslev & Mikkelsen 1996) Long-Memory Volatility Regime Gate + Trend Filter

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_figarch_longmemory_vol_regime_trendgate.py`
**Status:** ACCEPTED (crypto only: BTC/USDT, ETH/USDT) -- equity legs (QQQ, SPY) REJECTED

## Hypothesis

Per Baillie, Bollerslev & Mikkelsen (1996), formula confirmed via the
`rugarch` R package vignette (Section 2.2.10, FIGARCH -- same PDF already
read this cron trigger for the Component GARCH, TGARCH, NAGARCH, and
apARCH entries, fifth distinct submodel consulted). Genuinely novel for
this repo (0 prior "FIGARCH"/"fractionally integrated"/"long memory
volatility" hits): every other GARCH-family model this trigger assumes
EXPONENTIAL shock decay (persistence alpha+beta<1); FIGARCH instead uses a
FRACTIONAL differencing operator (1-L)^d, 0<d<1, giving HYPERBOLIC decay --
a genuinely different persistence STRUCTURE, implemented via the standard
truncated ARCH(infinity) representation (Baillie et al. 1996/Chung 1999
weight recursion, truncated to 100 lags; negative weights outside the
strict positivity region clipped to zero, a pragmatic from-scratch
simplification).

## Grid/tuning findings

- **Equity (QQQ, SPY): does not clear Sharpe >= 1.0 at ANY tested
  parameter combination.** QQQ peaked at Sharpe 0.983 (trend_window=200,
  vol_threshold_quantile=0.7); SPY peaked at 0.953 (trend_window=200,
  vol_threshold_quantile=0.9). Both close but consistently short of the
  threshold across an extensive sweep (trend_window in [100,150,200,250]
  x vol_threshold_quantile in [0.4..0.9]).
- **Crypto (BTC/USDT, ETH/USDT): clears the bar comfortably.** BTC/USDT
  best at trend_window=100/vol_threshold_quantile=0.9 (raw Sharpe 1.131,
  but at a shorter trend_window=50 initially found 549 trades that failed
  transaction-cost-survival -- retuned to trend_window=100 which cut
  trades to 329 and restored tx-cost survival). ETH/USDT best at
  trend_window=50/vol_threshold_quantile=0.7 (Sharpe 1.468).

## Single-config validation (Step 7) -- crypto legs only

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) | Walk-forward (4-split) |
|---|---|---|---|---|
| BTC/USDT (lev 0.4) | 1.131 (pass) | 0.172 (pass) | 0.695 (pass), 329 trades | 4/4 splits positive (pass) |
| ETH/USDT (lev 0.4) | 1.468 (pass) | 0.209 (pass) | 1.219 (pass), 205 trades | 4/4 splits positive (pass) |

Parameter sensitivity (BTC/USDT, trend_window in [75,100,125] x
vol_threshold_quantile in [0.85,0.9]): relative_std = 0.075 (mean Sharpe
0.923, std 0.070), threshold 0.5. **PASS.**

Walk-forward used a manual 4-equal-chunk split (vectorbt's `RangeSplitter`
API broken in this repo per this cron trigger's now-standard workaround
note).

## Decision: ACCEPT (crypto only: BTC/USDT, ETH/USDT); REJECT equity legs (QQQ, SPY)

Per RESEARCH_LOOP.md Step 6's guidance ("a strategy that only works in one
asset class is not automatically rejected -- record that finding
precisely"), this strategy is accepted for its CRYPTO scope only. Both
BTC/USDT and ETH/USDT pass all 5 validators. Equity legs are recorded as
rejected (never cleared Sharpe 1.0 across an extensive parameter sweep) so
a future loop does not over-trust this strategy outside its crypto scope.
10th distinct GARCH/HAR/CARR-family volatility model tested this cron
trigger, and the first to show a genuine asset-class split with the
same underlying model (equity structurally fails, crypto structurally
succeeds) rather than needing leverage-cap tuning alone.
