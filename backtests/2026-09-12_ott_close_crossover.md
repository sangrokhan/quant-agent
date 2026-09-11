# Optimized Trend Tracker (OTT) Close-Crossover Trend Following

**Hypothesis:** OTT (Anil Ozeksi/KivancOzbilgic, 2020) is an adaptive
trailing-stop trend line built from a Chande-Momentum-Oscillator-weighted
Variable Index Dynamic Average (VIDYA/VAR) with a percentage-band trailing
stop. Per https://www.tradingview.com/script/zVhoDQME/ (creator's own
page): "We are under the effect of the uptrend in cases where the prices
are above OTT... BUY when Prices are above OTT, SELL when Prices are below
OTT." Formula details (CMO-weighted VMA alpha, `fark = VMA*percent*0.01`
band) per https://pineify.app/pine-script/indicators/optimized-trend-tracker.
Operationalized as a close-crosses-OTT-line long/flat trend-following
strategy with a max_hold_days time-stop.

Sources: https://www.tradingview.com/script/zVhoDQME/ (rule),
https://pineify.app/pine-script/indicators/optimized-trend-tracker (formula
detail) -- both visited via browser_exec (google.com/web_search fallback
chain).

## Step 6 Grid Test Summary (108 cells: 3 length x 3 percent x 1
max_hold_days x 4 symbols x 3 vol regimes)

- pass_fraction: 0.269 (29/108)
- by_asset_class: equity 29/54 passed, crypto 0/54 (decisively rejected)
- by_vol_regime: low 18/36, mid 9/36, high 2/36 (edge concentrated in
  low/mid-vol, weak in high-vol)
- best_cell: length=10, percent=2.5, max_hold_days=60, SPY, low-vol
  regime, Sharpe=2.65
- worst_cell: length=5, percent=1.4, max_hold_days=60, QQQ, high-vol
  regime, Sharpe=-0.26

## Step 7 Single-Config Validation (best config: length=10, percent=2.5,
max_hold_days=60, full sample 2019-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|--------|--------|-----|-------------|---------------|---------------------|
| QQQ | 1.027 (PASS) | 0.2501 (FAIL by 0.0001, thr 0.25) | 0.917 (PASS) | 0.75 (PASS) | 0.118 rel std (PASS) |
| SPY | 1.023 (PASS) | 0.2165 (PASS) | 0.893 (PASS) | 1.00 (PASS) | 0.138 rel std (PASS) |

## Decision: ACCEPTED (SPY only); QQQ near-miss (MDD fails by 0.0001, all
other 4 validators pass)

SPY passes all 5 validators at the primary grid-best config cleanly.
QQQ passes 4/5 validators, missing MDD by a razor-thin margin (25.014% vs
25.00% threshold) -- essentially a tie, but per this repo's strict
accept-only-if-all-pass convention, QQQ is not accepted standalone.
Strategy file and this report are kept as a live SPY strategy; crypto is
decisively rejected (0/54 grid cells) so this strategy's scope is SPY
(equity) only. QQQ could be revisited in a future iteration with a
slightly tighter percent (e.g. 2.0) or an added MDD-reducing exit rule
(e.g. ATR stop) to close the 0.0001 gap.
