# Bulkowski DB (Double Bottom) Fixed-Target Trading Setup — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_db_trading_setup_fixed_target.py`
**Source:** https://thepatternsite.com/DBTradingSetup.html (Thomas
Bulkowski), read via browser_exec.

## Hypothesis

Bulkowski's disclosed double-bottom swing-trade rules: detect a confirmed
swing low (11-bar centered window), followed 20-120 days later by a
similar-price second swing low (after a >=15% interim rise off the first
bottom). Buy next open once close crosses above the highest high of the
window around the second bottom (confirmation price). Exit via limit order
at that same confirmation price (fixed profit target) or stop below the
second bottom's low. Source's own 571-stock in-sample (2000-2007) +
out-of-sample (2007-2010) test: 70-72% win rate, win/loss ratio 2.43-4.06,
average hold 46-57 days.

Distinct from the already-tested Double Bottom breakout-continuation
strategy (2026-09-06-180): that one enters on neckline breakout and rides
the trend; this one enters similarly but takes profit at a FIXED target
(the confirmation high itself), reflecting the source's own literal
limit-order economics.

## Grid test summary (Step 6)

`min_rise_pct` in {0.10, 0.15}, `low_similarity_pct` in {0.05, 0.08}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 48 cells.

- **pass_fraction: 0.0** (0/48) -- no cell passed the grid's Sharpe/MDD bar.
- **best_cell:** min_rise_pct=0.10, low_similarity_pct=0.05, ETH/USDT,
  mid-vol, Sharpe 0.897 (still short of the >=1.0 bar).
- **worst_cell:** min_rise_pct=0.10, low_similarity_pct=0.08, QQQ, low-vol,
  Sharpe -1.099.

Quick single-config sanity check (defaults, QQQ, full sample 2016-2026-09):
only 5 trades total over 10.5 years -- the pattern's specific two-bottom,
20-120-day-gap, 11-bar-swing-confirmed detection criteria are quite rare on
daily bars for large-cap ETFs, consistent with Bulkowski's own test being
run across 571 individual stocks (far more idiosyncratic volatility/pattern
occurrence than 2-4 liquid ETFs/pairs).

## Decision

**Rejected outright at the grid stage** -- 0/48 cells passed (best Sharpe
0.897, still below the 1.0 threshold). No single-config validator suite run
given the grid's unanimous fail (per Step 7, skip full validation when the
grid result is already decisively negative). The extremely low trade
frequency (single digits per symbol over a decade) is the likely root cause
-- this setup needs a broad, idiosyncratic stock universe (571 names per
the source) to generate enough signal density, not a handful of large,
efficient ETFs/major crypto pairs.

## Notes for future revisit

If revisited, test across a broader basket of higher-volatility individual
equities (not just QQQ/SPY) to better match the source's own testing
universe and trade-frequency assumptions.
