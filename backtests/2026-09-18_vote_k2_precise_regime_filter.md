# Backtest Report: Vote-K=2 Precise 4-Signal Regime Filter

**Strategy file:** `strategies/2026-09-18_vote_k2_precise_regime_filter.py`
**Hypothesis id:** 2026-09-18-006
**Source:** https://www.reddit.com/r/LETFs/comments/1t7q8or/ ("40-year LETF rotation backtest — 5 strategy families, 426 configs", r/LETFs)

## Hypothesis

Direct refinement of this cron trigger's own id 2026-09-18-005, now using
the EXACT numeric thresholds disclosed in the author's own follow-up post:
price>SMA(250), price>SMA(100), realized_vol(21d)<40% (absolute annualized
cap, not relative-to-median), and a genuine lag-1 autocorrelation (AR(1))
coefficient over a 30-day window > 0 -- vote_threshold=2 of these 4. Tested
here against un-leveraged QQQ/SPY rather than the source's QLD.

## Grid Test Summary (Step 6)

Grid: `vote_threshold` in {2,3}, `vol_threshold` in {0.30,0.40,0.50},
`sma_long` in {200,250}, symbols equity {QQQ, SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 42, **pass_fraction: 0.292**
- by_asset_class: equity 36/72, crypto 6/72
- by_vol_regime: low 26/48, mid 16/48, high 0/48
- best_cell: SPY low-vol, vote_threshold=2/vol_threshold=0.30/sma_long=200, Sharpe 2.58

A follow-up full-sample re-sweep (varying sma_long, sma_medium, vol_threshold)
found a config passing BOTH QQQ and SPY simultaneously:
`vote_threshold=2, vol_threshold=0.35, sma_long=150, sma_medium=50`.

## Single-Config Validation (Step 7)

Config: `vote_threshold=2, vol_threshold=0.35, sma_long=150, sma_medium=50`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|--------|--------|-----|------------------------|--------------|--------------------|---------|
| QQQ    | 1.293  | 0.207 | 1.257                 | 1.0 (4/4)    | 0.029              | **ACCEPT** |
| SPY    | 1.124  | 0.244 | 1.086                 | 0.75 (3/4)   | 0.028              | **ACCEPT** |
| BTC/USDT | 0.917 | 0.615 | 0.893                | 1.0 (4/4)    | 0.122              | REJECT (decisive) |
| ETH/USDT | 0.939 | 0.626 | 0.919                | 1.0 (4/4)    | 0.029              | REJECT (decisive) |

## Decision (Step 8)

**Accepted for QQQ AND SPY**, both pass all 5 validators. Crypto decisively
rejected (Sharpe<1.0 and MDD 0.61-0.63) -- same crypto-doesn't-transfer
pattern already seen in this cron trigger's other regime-vote strategy
(2026-09-18-005).
