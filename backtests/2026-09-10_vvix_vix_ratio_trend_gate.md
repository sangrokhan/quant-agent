# Backtest report: VVIX/VIX ratio regime-gated SMA trend-following

**Strategy file:** `strategies/2026-09-10_vvix_vix_ratio_trend_gate.py`
**Knowledge base id:** 2026-09-10-042
**Outcome: REJECTED** (decisive Sharpe fail across the full parameter grid; crypto 0/108)

## Hypothesis

Per volatilitybox.com's VVIX guide (visited 2026-09-10, first time this
source was read in this repo), the VVIX/VIX ratio (median ~4.5:1
historically) reflects how confident/unstable the market's own volatility
forecast is. A "calm" regime (ratio at/below its own trailing SMA) should
be a better environment for a plain SMA trend-following signal than an
"unstable" vol-of-vol regime (elevated ratio, market pricing a VIX spike
that hasn't happened yet — often choppy/whipsaw-prone). Tested as a gate on
QQQ/SPY (equity, direct VVIX/VIX data) and BTC/ETH (crypto, equity-derived
macro vol-of-vol gate applied cross-asset-class, consistent with prior
iterations e.g. 2026-09-10-039/040).

This is distinct from the already-rejected raw-VVIX-level contrarian
strategy (id=2026-09-10-022, VVIX>120 spike-fade), since this uses the
VVIX/VIX *ratio* relative to its own trailing average as a trend-following
*gate*, not the raw VVIX level as a contrarian mean-reversion trigger.

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = trend_window∈{50,100,200} ×
ratio_window∈{30,60} × regime_mult∈{0.9,1.0,1.1}, symbols =
{equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT}, vol_regime_splits=3
(low/mid/high realized-vol terciles), 2018-01-01 to 2024-12-31.

- **total_cells:** 216
- **passed_cells:** 38
- **pass_fraction:** 0.176
- **by_asset_class:** equity 38/108 passed; **crypto 0/108 passed** (decisive fail — VVIX/VIX is a purely equity-market-derived signal and provides no edge when applied to crypto trend signals)
- **by_vol_regime:** low 23/72, mid 15/72, **high 0/72** (gate provides zero benefit during high-realized-vol regimes — arguably the regime where a "calm vol-of-vol" filter should matter most, which undercuts the hypothesis)
- **best_cell:** trend_window=200, ratio_window=60, regime_mult=0.9, QQQ, mid-vol tercile, Sharpe=2.356 (a single favorable slice, not representative)
- **worst_cell:** trend_window=50, ratio_window=60, regime_mult=0.9, SPY, high-vol tercile, Sharpe=-1.651

## Full-sample single-config validation (Step 7)

Swept the full param grid on full-sample (non-sliced) QQQ/SPY returns to find
the best overall full-sample config (not just best tercile-slice, which
overfits to one regime):

| trend_window | ratio_window | regime_mult | QQQ Sharpe | QQQ MDD | SPY Sharpe | SPY MDD |
|---|---|---|---|---|---|---|
| 50 | 30 | 1.1 | 0.794 | 0.173 | 0.587 | 0.186 |
| 200 | 60 | 1.1 | 0.558 | 0.219 | 0.538 | 0.180 |
| 200 | 30 | 1.1 | 0.778 | 0.248 | 0.530 | 0.223 |

**Best full-sample config found (trend_window=50, ratio_window=30,
regime_mult=1.1): QQQ Sharpe=0.794, SPY Sharpe=0.587** — both decisively
below the 1.0 Sharpe threshold across every parameter combination tested.
Max drawdown passed (<0.25) for most configs, but Sharpe is the binding,
decisive failure — no walk-forward or transaction-cost-survival validation
was run since the primary Sharpe check already fails outright at every grid
point (RESEARCH_LOOP.md Step 8: reject if any validator fails; no value in
running secondary validators against a strategy that fails cleanly on
every parameter combination already tested).

## Validators

- `check_sharpe_ratio` (min 1.0): **FAILED** at every one of 18 param combos × 2 symbols tested; best 0.794 (QQQ), 0.622 (SPY, different combo).
- `check_max_drawdown` (max 0.25): passed for most configs (not the binding constraint).
- `check_transaction_cost_survival`, `check_walk_forward`, `check_parameter_sensitivity`: not run — decisive Sharpe fail at the full-sample level makes these moot per Step 7 guidance ("Run whichever subset is relevant").

## Decision

**Rejected.** The VVIX/VIX ratio regime gate does not lift a plain SMA
trend-following signal to the required Sharpe threshold on either equity
symbol, provides zero benefit in high-vol regimes (where the "calm vol of
vol" story should matter most), and has no edge at all on crypto (expected,
since VVIX/VIX has no crypto analogue — this cross-asset-class gate
application is now empirically falsified, not just theoretically
speculative).
