# RAVI (Range Action Verification Index) Trend Confirmation

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_ravi_trend_confirmation.py`
**Knowledge base id:** 2026-09-10-079

## Hypothesis

Per technicalresources.in's "How to Trade Using the Range Action Verification
Index (RAVI)" (visited this iteration,
https://technicalresources.in/how-to-trade-using-the-range-action-verification-index-ravi-strategies-and-examples/):
RAVI = 100 * (SMA_short - SMA_long) / SMA_long (Tushar Chande, default
7/65-period SMAs). Source's disclosed "Trend Confirmation Strategy": enter
long when RAVI crosses above a threshold (default 3%); exit when RAVI
starts declining back toward zero. First RAVI strategy in this repo.

## Grid test summary (Step 6)

Equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT) x
`entry_threshold in [2.0,3.0,4.0]` x `exit_slope_window in [3,5]` x
vol_regime_splits=3 = 72 cells.

- total_cells: 72, passed_cells: 9, **pass_fraction: 0.125**
- by_asset_class: equity 9/36 passed, **crypto 0/36 (decisive reject)**
- by_vol_regime: low 8/24, mid 1/24, high 0/24 -- low-vol-concentrated
- best_cell: `entry_threshold=2.0, exit_slope_window=3`, QQQ, low-vol,
  Sharpe 2.38

## Full-sample validators on best config (`entry_threshold=2.0, exit_slope_window=3`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.572 (FAIL) | 0.457 (FAIL) | >= 1.0 |
| Max drawdown | 0.120 (pass) | 0.102 (pass) | <= 0.25 |
| TC survival (10bps/trade, 23/28 trades) | 0.512 (pass) | 0.361 (FAIL) | >= 0.5 |
| Walk-forward (4 manual date-slices) | 1.0 (pass, 4/4) | 1.0 (pass, 4/4) | >= 0.75 |
| Parameter sensitivity (6-cell grid) | rel_std 0.198 (pass) | rel_std 0.731 (FAIL) | <= 0.5 |

## Decision: REJECT

Full-sample Sharpe fails decisively on both QQQ and SPY (0.57 / 0.46,
below the 1.0 bar) despite a perfect 4/4 walk-forward and generally low
drawdown -- this is a real near-miss (low turnover, robust across time
splits) but not a strong enough edge to accept. Crypto rejected
decisively (0/36 grid cells) -- RAVI's SMA-ratio construction with these
periods does not translate to BTC/ETH's higher-frequency regime shifts.
Worth a future revisit tightening entry_threshold below 2.0 or shortening
long_window for crypto, but not pursued further this iteration per
novelty/scope budget.
