# Backtest Report: Ehlers Continuation Index (UltimateSmoother vs Laguerre)

**Strategy file:** `strategies/2026-09-12_ehlers_continuation_index.py`
**Knowledge base id:** 2026-09-12-173
**Date:** 2026-09-12

## Hypothesis

Per John F. Ehlers' "Continuation Index" (TASC September 2025 Traders'
Tips), implemented at
https://www.tradingview.com/script/5ZrOut79-TASC-2025-09-The-Continuation-Index/:
Ehlers observed that "when price is in trend, it tends to stay to one side
of" a Laguerre filter. This strategy normalizes the difference between the
UltimateSmoother (low-lag Ehlers filter, half the length of the Laguerre
filter to minimize lag) and a fixed-gamma classic Laguerre filter into a
two-state trend oscillator. Source's own disclosed usage: "+1 suggests the
trader should position on the long side. -1 suggests the user should
position on the short side." Long-only adaptation here (per SAFETY.md):
long when UltimateSmoother is above the Laguerre filter (smoothed
difference > 0), flat otherwise.

## Single-config validator results (gamma=0.3, length=30)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Param-sensitivity relative_std |
|--------|--------|-----|-------------------------|----------------------------------|
| QQQ    | 1.424 (PASS, thr 1.0) | 0.208 (PASS, thr 0.25) | 1.352 (PASS, thr 0.5, 114 trades, 5bps) | 0.288 (PASS, thr 0.5) |
| SPY    | 1.641 (PASS, thr 1.0) | 0.119 (PASS, thr 0.25) | 1.534 (PASS, thr 0.5, 116 trades, 5bps) | 0.368 (PASS, thr 0.5) |

All 4 run validators pass for both QQQ and SPY, with comfortable margins
(Sharpe well above 1.0, MDD well below 0.25). Walk-forward not run
(vectorbt.utils.splitting API broken in installed vectorbt version,
repo-wide known issue, not specific to this strategy).

## Grid test summary (run_strategy_grid)

`param_grid={"gamma": [0.3, 0.5, 0.7], "length": [15, 20, 30]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 108 total cells.

- **pass_fraction: 0.278** (30/108)
- by_asset_class: equity 30/54 passed; crypto 0/54 decisively rejected.
- by_vol_regime: low 18/36, mid 9/36, high 3/36 -- consistent with most
  trend-following strategies in this repo, edge is strongest in
  low/mid-vol regimes and weaker (but not zero) in high-vol.
- Best cell: QQQ low-vol, gamma=0.7/length=30, Sharpe 3.04.
- Worst cell: QQQ high-vol, gamma=0.3/length=15, Sharpe -0.63.
- Every full-sample config tested (5 spot-checked combos per symbol) had
  Sharpe > 1.0 on BOTH QQQ and SPY -- this is an unusually robust
  parameter surface for this repo, not just a single lucky cell.

## Decision: ACCEPT (QQQ and SPY, gamma=0.3, length=30)

Both symbols pass Sharpe, MDD, transaction-cost-survival, and
parameter-sensitivity comfortably at the chosen config. Crypto is out of
scope (decisively rejected across the full grid, consistent with most
Ehlers-family filters already tested in this repo).

## Notes / caveats for future iterations

- This is one of the strongest full-sample results found this cron
  trigger's iterations -- both Sharpe (1.42/1.64) and MDD (0.21/0.12) have
  comfortable margins versus threshold, and multiple nearby parameter
  combos also pass, suggesting a genuinely robust surface rather than a
  cherry-picked cell.
- The UltimateSmoother and fixed-gamma Laguerre filter building blocks are
  both reused from/consistent with this repo's existing Ehlers-family
  helpers (2026-09-05_ultimate_smoother_trend.py's `_ultimate_smoother`);
  the fixed-gamma Laguerre implementation here is a fresh classic-form
  helper distinct from this repo's existing *adaptive*-gamma Laguerre
  filter (2026-09-05_adaptive_laguerre_filter_trend.py).
