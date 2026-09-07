# Lo-MacKinlay Variance Ratio Trend-Regime Gate + Donchian Breakout — QQQ/SPY/BTC/ETH

**Hypothesis:** Direct follow-up to 2026-09-08-103 (VR(k) gate + EMA
crossover, rejected). Keeps the same Lo-MacKinlay Variance Ratio VR(k)
trending-regime gate (per https://twowaymind.com/article-variance-ratio,
Lo & MacKinlay 1988) but swaps the entry mechanism for the
already-accepted-on-QQQ plain Donchian Channel breakout (2026-09-04-054),
isolating whether the VR(k) filter rescues the Donchian breakout, or
whether the prior rejection was a limitation of VR(k) itself rather than
the crossover mechanism.

Best config from grid search: `vr_threshold=1.0, entry_window=40,
exit_window=20` (vr_k=5, vr_window=60, max_hold_days=40 held fixed).

## Single-config validator results (best config)

| Validator | QQQ | SPY |
|---|---|---|
| sharpe_ratio | **FAIL** 0.615 (thr 1.0) | **FAIL** 0.196 (thr 1.0) |
| max_drawdown | pass 0.099 (thr 0.25) | pass 0.101 (thr 0.25) |
| transaction_cost_survival (10bps/trade, 15-17 trades) | pass 0.565 (thr 0.5) | **FAIL** 0.131 (thr 0.5) |

QQQ is a partial near-miss (2/3 pass, Sharpe still fails threshold); SPY
fails decisively.

## Step 6 grid summary (param_grid: vr_threshold∈{1.0,1.1},
entry_window∈{20,40}, exit_window∈{10,20}; symbols QQQ/SPY (equity),
BTC/USDT+ETH/USDT (crypto); vol_regime_splits=3)

- **pass_fraction: 0.177** (17/96 cells)
- by_asset_class: equity 17/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 16/32, mid 1/32, **high 0/32** -- same low-vol-only
  concentration pattern as the sibling EMA-crossover variant
- best_cell: QQQ, low-vol regime, Sharpe 2.05
- worst_cell: QQQ, high-vol regime, Sharpe -1.18

## Decision: REJECTED

Full-sample Sharpe still fails on both QQQ and SPY at the best grid
config even with the accepted Donchian entry mechanism substituted in,
confirming the prior iteration's suspicion should be revised: the VR(k)
regime filter itself -- not the EMA-crossover entry mechanism -- is the
limiting factor. Crypto again shows zero edge. Grid pass_fraction and the
low-vol-only concentration pattern are nearly identical to 2026-09-08-103.

**Notes for future loops:** Two consecutive VR(k)-gated variants (EMA
crossover and Donchian breakout) both plateau in the same low-vol-only,
sub-threshold-Sharpe pattern -- this is now good evidence that VR(k) as
constructed here (5-period, 60-day rolling window) does not add exploitable
signal over plain unconditional trend-following on this daily-bar
QQQ/SPY/BTC/ETH sample. Not recommended to try further VR(k) variants
without changing the underlying construction substantially (e.g. much
longer vr_window/higher vr_k, or heteroscedasticity-robust z*(k) instead
of the raw ratio).
