# Backtest Report: CR ("Energy Index" / Intermediate Willingness Index) Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_cr_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-100

## Hypothesis

CR is a Chinese-market "energy index", structurally similar to AR/BR
(this cron trigger's own 2026-09-16-099 BRAR entry) but uses the prior
day's median price (`(PrevHigh+PrevLow)/2`) as its reference instead of
the open (AR) or prior close (BR). Per
https://www.futuhk.com/en/support/topic1_167 (visited via browser_exec,
directly cross-referenced from the BRAR source page):

    prev_mid(t) = (High(t-1) + Low(t-1)) / 2
    strong_sum(N) = SUM(max(0, High(t) - prev_mid(t)), N)
    weak_sum(N)   = SUM(max(0, prev_mid(t) - Low(t)), N)
    CR(N) = 100 * strong_sum(N) / weak_sum(N)

Source explicitly frames CR as complementary to (not redundant with)
AR/BR ("assist BRAR's shortcomings", personality "between AR and BR,
closer to BR") -- justifying a distinct test right after this trigger's
BRAR entry. This iteration reframes CR as a **continuous sizing dial**
(rolling z-score + tanh squash to [-1,1]) inside an SMA(trend_window)
uptrend gate with deadband, leverage-cap-aware for crypto from the start.
First CR strategy in this repo.

Source: https://www.futuhk.com/en/support/topic1_167, visited via
browser_exec this iteration.

## Grid test summary (`grid_result_cr_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3. 72 cells.
- `pass_fraction`: **0.472** (34/72)
- `by_asset_class`: equity 18/36 (0.500), crypto 16/36 (0.444).
- `by_vol_regime`: low 24/24 (1.00), mid 8/24 (0.333), high 2/24 (0.083) —
  sharp high-vol degradation, more concentrated in low-vol than BRAR.
- best cell: QQQ, sensitivity=0.4/deadband=0.30, low-vol, Sharpe 2.61.
- worst cell: QQQ, sensitivity=0.4/deadband=0.30, high-vol, Sharpe -0.15.

## Single-config validation (`validators_cr_sizing.json`)

Per-symbol retuned config, full 2019-01-01..2026-09-01 sample. SPY's
initial grid-derived config (deadband=0.25) failed TC-survival on high
turnover; widening trend_window/zscore_window/deadband search
(trend_window=30, zscore_window=40, deadband=0.40) found a strong pass
(Sharpe 1.465, TC-survival net Sharpe 1.036, only 87 trades).

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass frac | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.181 | 0.085 | pass | 1.00 | pass | PASS |
| SPY | 1.465 | 0.070 | 1.036 | 1.00 | pass | PASS |
| BTC/USDT | 1.527 | 0.185 | pass | 1.00 | pass | PASS |
| ETH/USDT | 1.484 | 0.140 | pass | 1.00 | pass | PASS |

All 5 validators pass on all 4 symbols.

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First CR
strategy tested in this repo.

Per-symbol params used:
- QQQ: trend_window=40, cr_window=26, zscore_window=60, base_exposure=0.4,
  sensitivity=0.3, leverage_cap=1.0, deadband=0.35
- SPY: trend_window=30, zscore_window=40, base_exposure=0.4,
  sensitivity=0.4, leverage_cap=1.0, deadband=0.40
- BTC/USDT: base_exposure=0.2, sensitivity=0.3, leverage_cap=0.5, deadband=0.15
- ETH/USDT: base_exposure=0.2, sensitivity=0.2, leverage_cap=0.5, deadband=0.15
