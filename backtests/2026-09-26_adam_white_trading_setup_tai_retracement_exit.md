# Bulkowski/Adam White Trading Setup (HH/HL entry, TAI-gated retracement exit) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_adam_white_trading_setup_tai_retracement_exit.py`
**Source:** https://thepatternsite.com/AdamWhiteSetup.html (Thomas
Bulkowski, discussing Adam White's TASC June 1995 article), read via
browser_exec (web_extract's ddgs backend cannot fetch this domain).

## Hypothesis

Long entry on a higher-high/higher-low structure over 5/13-week windows
(scaled to 25/65 trading days). Exit only when BOTH a >5% retracement off
the 13-week high AND a Trend Analysis Index (range of a 26-week SMA over
5 weeks, normalized by close) below a threshold (source default 1.2,
meaning NOT strongly trending) are true -- the TAI is meant to suppress
the retracement exit during genuine uptrends, but source's own write-up
explicitly warns this exit mechanism has "a serious flaw" (median drawdown
up to 99% on some out-of-sample symbols) because a steep decline can still
register as "trending" by the TAI's high-low-range measure, indefinitely
delaying the exit. Bulkowski's own confirmed-optimal defaults (26-week
SMA, 5% retracement, 1.2 TAI) used as this iteration's starting grid
center.

## Grid test summary (Step 6)

`retracement_pct` in {0.03,0.05,0.08}, `tai_threshold` in {1.0,1.2,1.5},
equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108
cells.

- **pass_fraction: 0.287** (31/108)
- **by_asset_class:** equity 31/54, crypto 0/54 (crypto categorically
  fails -- no vol-regime cell passed for either BTC/USDT or ETH/USDT at
  any parameter combination)
- **by_vol_regime:** low 18/36, mid 13/36, high 0/36 (zero high-vol
  passes -- directly consistent with source's own documented exit flaw:
  the TAI-gated retracement exit is exactly the kind of mechanism that
  should fail hardest in high-vol/steep-decline regimes)
- **best_cell:** retracement_pct=0.03, tai_threshold=1.0, QQQ, low-vol,
  Sharpe 2.369
- **worst_cell:** retracement_pct=0.05, tai_threshold=1.5, SPY, high-vol,
  Sharpe -0.410
- **best shared config (both QQQ and SPY averaging positive Sharpe
  across regimes):** retracement_pct=0.08, tai_threshold=1.2 (QQQ avg
  1.410 2/3 passed; SPY avg 1.215 2/3 passed) -- matches source's own
  disclosed optimal TAI threshold (1.2).

## Single-config validation (Step 7)

Config: `short_window_days=25, long_window_days=65, retracement_pct=0.08,
tai_sma_days=130, tai_range_days=25, tai_threshold=1.2`. Full sample
2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 1.089 PASS | 0.286 **FAIL** | 1.083 PASS | 0.059 PASS | 9 |
| SPY | 0.805 **FAIL** | 0.341 **FAIL** | 0.796 PASS | 0.131 PASS | 11 |

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing).

Both symbols FAIL max drawdown at the full-sample single-config level
(28.6% QQQ, 34.1% SPY, both breaching the 25% threshold), even though the
grid-test's tercile-sliced cells looked reasonable in isolation -- this is
precisely the failure mode Bulkowski's own write-up warned about: a
multi-year holding period (this strategy trades only 9-11 times over 10.5
years, avg hold measured in months) means a single bad drawdown episode
dominates the full-sample MDD figure in a way the grid's shorter
vol-regime-tercile slices don't fully capture. Sample size is also very
sparse (9-11 trades total), consistent with the source's own reported low
frequency (avg hold 134-210 days weekly-scale) -- any full-sample metric
here rests on a small number of independent trades.

## Decision

**Rejected (all symbols).** QQQ passes Sharpe/TC-survival/param-sensitivity
but fails max drawdown (0.286 > 0.25 threshold); SPY fails Sharpe AND max
drawdown. This directly reproduces the specific weakness Bulkowski's own
source article disclosed for this exact setup: the TAI-gated retracement
exit can let a steep decline run because the TAI's range-based "trending"
measure doesn't distinguish a fast decline from a fast advance. Crypto
categorically fails (0/54 grid cells, no cell in any vol regime for either
BTC/USDT or ETH/USDT). Not worth a further parameter search within this
iteration's budget -- the flaw is structural (as the source itself
concludes, recommending an ADX-based exit replacement instead of TAI),
not a tunable-parameter issue; a future iteration could revisit this with
an ADX-gated retracement exit as a distinct, non-duplicate test.

Novelty: checked `strategies_index.jsonl` for "Adam White"/"Trend Analysis
Index"/"TAI" -- found 5 prior Vertical Horizontal Filter (VHF) entries
(Adam White's OTHER well-known indicator), all a completely different
construction (VHF trend-efficiency ratio vs this setup's higher-high/
higher-low entry + dual-condition TAI-gated retracement exit) -- confirmed
non-duplicate.
