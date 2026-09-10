# Backtest Report: MACD Zero-Line Slope + ADX/DI Rising-Trend Confluence

**Strategy file:** `strategies/2026-09-11_macd_adx_confluence.py`
**Date:** 2026-09-11
**Source:** https://www.forextester.com/blog/macd-and-adx-strategy ("MACD+ADX trading strategy: how two perfect trading tools will pass the test", Forex Tester Online blog)

## Hypothesis

Per the Forex Tester article's disclosed buy rule, combining MACD's
trend-reversal detection with ADX's trend-strength confirmation should
filter false signals better than either alone: (1) MACD line above zero AND
rising, (2) +DI crosses above -DI, (3) ADX itself rising. Long entry when
all three align; exit on MACD turning non-positive or -DI crossing back
above +DI. Distinct from prior single-indicator MACD (2026-09-03-013,
zero-line-only) and ADX/DMI (2026-09-03-017, threshold-only crossover)
strategies in this repo by requiring genuine 3-way confluence.

## Grid test summary (Step 6)

Grid: `dmi_period` in {10,14,20} x `adx_slope_window` in {3,5,8},
vol_regime_splits=3, symbols equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 3/54 cells passed (pass_fraction 0.056). Spread thin across
  all three vol regimes (1 pass each in low/mid/high) rather than
  concentrated in one regime. Best cell: dmi_period=10, adx_slope_window=3,
  SPY, low-vol, Sharpe 1.32. Worst: dmi_period=20, adx_slope_window=3, QQQ,
  mid-vol, Sharpe -1.12.
- **Crypto:** 0/54 cells passed (pass_fraction 0.0). Best Sharpe only 0.375.

## Single-config validation (Step 7): dmi_period=10, adx_slope_window=3

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.335 ❌ | 0.578 ❌ | ≥ 1.0 |
| Max drawdown | 0.105 ✅ | 0.055 ✅ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.228 ❌ | 0.482 ❌ | ≥ 0.5 |

Full-sample Sharpe fails decisively for both symbols. MDD is very low
(the triple-condition filter is highly restrictive, producing few, short
holding periods) but transaction-cost survival fails because trade
frequency (48 trades for QQQ over ~8.5yr, still meaningful) combined with
the low raw Sharpe erodes further under costs. Walk-forward/param-sens not
run given decisive full-sample failure and thin grid pass_fraction.

## Decision: REJECTED

Decisive rejection -- lowest grid pass_fraction of the strategies tested
this cron trigger (0.056), no regime concentration pattern worth pursuing
with a targeted fix (unlike the Dow Theory lineage's clean low-vol-only
split). The triple-confluence requirement (MACD zero-line+slope AND DI
cross AND ADX slope) appears to over-filter, producing too few/weak signals
to clear the Sharpe bar even where the raw MDD looks favorable.
