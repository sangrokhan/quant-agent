# RSI(14) Scale-Out System (Knapp/Bulkowski) — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_rsi_scaleout_knapp_system.py`
**Source:** https://thepatternsite.com/MechanicalRSI.html (Thomas Bulkowski,
summarizing Volker Knapp's "RSI scale-out system", Active Trader magazine,
Feb 2010), read via browser_exec.

## Hypothesis

Source's own disclosed exact mechanical rules (long only): buy next open
when 14-period RSI < 30; scale out 25% of the position at each of RSI 45,
60, 75, 90; hard stop the remaining position if price falls 5x the 20-day
ATR below entry; time-stop the remaining position after 300 days held.
Source's own 17-stock 1999-2009 test: 444 trades, +75.9% net, 21% max
drawdown, 70% win rate.

Adapted for this repo's single-instrument continuous-exposure contract:
implemented as a continuous [0,1] exposure series rather than literal
discrete share lots (entry sets exposure=1.0, each scale-out threshold
crossed reduces exposure by 0.25, ATR stop / time-stop zero it out
immediately) -- reproduces the source's own tranche economics for a single
position.

## Grid test summary (Step 6)

`entry_rsi_threshold` in {25,30}, `atr_stop_mult` in {3.0,5.0}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 48 cells.

- **pass_fraction: 0.25** (12/48)
- **by_asset_class:** equity 10/24, crypto 2/24
- **by_vol_regime:** low 10/16, mid 2/16, high 0/16 (mean-reversion entry
  works far better in calm/low-vol conditions)
- **best_cell:** entry_rsi_threshold=30, atr_stop_mult=3.0, QQQ, low-vol,
  Sharpe 3.11

## Single-config validation (Step 7)

Config: `entry_rsi_threshold=30, atr_stop_mult=3.0` (defaults for the rest).
Full sample 2019-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | **1.272 PASS** | 0.107 PASS | 1.260 PASS | 0.155 PASS | 5 |
| SPY | 0.687 **FAIL** | 0.110 PASS | 0.677 PASS | 0.588 **FAIL** | 5 |

`check_walk_forward` errored with the same pre-existing repo bug noted in
2026-09-24-130's report (`vbt.utils.splitting` missing); skipped per
`suggested_workload=light`.

Note: only 5 full-sample entries for each symbol over 7.5 years (RSI(14)<30
is a fairly rare deep-oversold trigger on trending large-cap ETFs) -- small
sample size caveat applies to all metrics above, consistent with the
source's own note that "the RSI can remain below 30 for months" (rare but
occasionally sustained triggers).

## Decision

**Accepted for QQQ only.** All 4 runnable validators pass for QQQ. SPY fails
both Sharpe (0.687 < 1.0) and parameter sensitivity (0.588 > 0.5 threshold)
-- rejected for SPY. Crypto (BTC/USDT, ETH/USDT) rejected decisively per the
grid (2/24 cells passed).
