# CMO Continuous Sizing Overlay on SMA(200) Trend Gate — Backtest Report

**Date:** 2026-09-13 | **KB id:** 2026-09-13-076 | **Outcome:** REJECTED (decisive on equity; crypto not run — equity already fails)

## Hypothesis
Chande Momentum Oscillator (CMO, Tushar Chande 1994) = 100*(SumUp-SumDown)/(SumUp+SumDown),
bounded [-100,100]. Sources: howtotrade.com, theforexgeek.com, quantifiedstrategies.com
(via `web_search`, this iteration). Repo has 4 prior CMO entries, all binary
threshold/signal-line/pullback entry triggers (all rejected). This iteration reuses the
"bounded oscillator as continuous sizing dial" pattern (accepted for %B, Aroon, Williams %R
elsewhere this cron trigger) applied to CMO: exposure = clip(base_exposure +
cmo_sensitivity*(cmo/100), 0, leverage_cap) on an SMA(200) trend gate.

## Grid test (Step 6)
`scripts/run_grid_cmo_sizing.py`, param_grid: cmo_window∈{10,14,20}, base_exposure∈{0.6,0.8,1.0},
cmo_sensitivity∈{0.4,0.6,0.8}; symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT};
vol_regime_splits=3. 2017-01-01 to 2026-09-01.

- total_cells=324, passed=81, **pass_fraction=0.25**
- by_asset_class: equity 81/162 passed; **crypto 0/162 (decisive fail)**
- by_vol_regime: low 54/108, mid 27/108, **high 0/108**
- best_cell: QQQ, cmo_window=20, base_exposure=1.0, cmo_sensitivity=0.4, low-vol, Sharpe=2.46

## Single-config validation (Step 7) — best config cmo_window=20, base_exposure=1.0, cmo_sensitivity=0.4

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>1.0) | **PASS** 1.114 | **FAIL** 0.784 |
| Max Drawdown (<0.25) | PASS 0.211 | PASS 0.204 |
| Transaction cost survival (net Sharpe >0.5 @10bps) | **FAIL** 0.447 (562 trades) | **FAIL** 0.117 (525 trades) |
| Walk-forward (4-split, ≥0.75 pass) | PASS 1.0 | PASS 0.75 |
| Parameter sensitivity (rel. std <0.5) | PASS 0.028 | PASS 0.041 |

## Decision: REJECTED
QQQ passes raw Sharpe/MDD/walk-forward/parameter-sensitivity but **fails transaction cost
survival decisively** (net Sharpe 0.447 vs 0.5 threshold) — CMO fluctuates enough day-to-day
even inside a persistent SMA(200) uptrend that the continuous exposure dial rebalances ~562
times over the sample (much higher turnover than the %B/Aroon/Williams-%R sizing variants,
which passed TC). SPY fails both raw Sharpe and TC. Crypto grid decisively rejected (0/162).
This is the first sizing-overlay variant this cron trigger to fail specifically on transaction
costs rather than raw Sharpe — CMO's un-smoothed sum-of-gains/sum-of-losses construction (no
EMA/Wilder smoothing, unlike RSI) makes it noisier bar-to-bar than %B/Aroon/Williams %R,
translating to materially higher rebalancing frequency for a similar exposure range.

## Note for future iterations
If revisiting CMO-as-sizing, add smoothing (e.g. EMA the raw CMO before mapping to exposure,
or a no-trade deadband/hysteresis around exposure changes) to cut turnover before re-testing
transaction-cost survival — the underlying trend-following Sharpe (1.11 QQQ) is otherwise
competitive with the accepted %B/Aroon/Williams %R variants.
