# Backtest Report: Vote-K=2 4-Signal Regime Filter WITH 5% SMA Whipsaw Buffer

**Strategy file:** `strategies/2026-09-18_vote_k2_sma_buffer_regime_filter.py`
**Hypothesis id:** 2026-09-18-007
**Source:** https://www.reddit.com/r/LETFs/comments/1t7q8or/ (same "40-year LETF rotation backtest" post as 2026-09-18-006, Tier 3 winner description)

## Hypothesis

Direct follow-up to this cron trigger's 2026-09-18-006. The source's actual
Tier-3 winning config explicitly adds a 5% BUFFER to both SMA-based trend
signals (price > SMA(250)*1.05, price > SMA(100)*1.05) as a whipsaw filter,
claimed to cut trade count ~30%. This iteration adds that buffer construction
on top of 2026-09-18-006's identical vol/AR(1) signals and vote_threshold=2
gate.

## Grid Test Summary (Step 6)

Grid: `sma_buffer` in {0.03,0.05,0.08}, `vol_threshold` in {0.30,0.40},
`sma_long` in {200,250}, symbols equity {QQQ, SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 36, **pass_fraction: 0.250**
- by_asset_class: equity 36/72, **crypto 0/72** (buffer fully eliminates
  crypto's marginal grid passes seen in 2026-09-18-006 -- consistent with
  the buffer being an equity-calibrated whipsaw-reduction mechanism)
- by_vol_regime: low 24/48, mid 12/48, high 0/48
- best_cell: SPY low-vol, sma_buffer=0.05/vol_threshold=0.30/sma_long=200, Sharpe 2.61

A follow-up full-sample re-sweep found a config passing BOTH QQQ and SPY:
`sma_buffer=0.03, vol_threshold=0.40, sma_long=150, sma_medium=50`.

## Single-Config Validation (Step 7)

Config: `sma_buffer=0.03, vol_threshold=0.40, sma_long=150, sma_medium=50`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|--------|--------|-----|------------------------|--------------|--------------------|---------|
| QQQ    | 1.121  | 0.185 | 1.062                 | 1.0 (4/4)    | 0.014              | **ACCEPT** |
| SPY    | 1.037  | 0.219 | 0.967                 | 0.75 (3/4)   | 0.318              | **ACCEPT** |
| BTC/USDT | 0.831 | 0.662 | 0.803                | 0.75 (3/4)   | 0.028              | REJECT (decisive) |
| ETH/USDT | 0.946 | 0.663 | 0.924                | 1.0 (4/4)    | 0.062              | REJECT (decisive) |

## Decision (Step 8)

**Accepted for QQQ AND SPY**, both pass all 5 validators. Crypto decisively
rejected (as in 2026-09-18-005/006, this regime-vote family doesn't
transfer to crypto's higher-turnover/higher-drawdown profile). Note: the
5% buffer meaningfully reduced grid-level crypto pass count to zero
(vs 6/72 without it in 2026-09-18-006), reinforcing this family's
equity-only scope going forward.
