# Pairs Trading: JPM/BAC Cointegration Z-Score Mean Reversion

**Strategy file:** `strategies/2026-09-08_pairs_zscore_cointegration.py`
**Source:** https://www.quantifiedstrategies.com/pairs-trading-strategy/

## Hypothesis

Two economically-related instruments (same-sector equities, or two large-cap
crypto majors) share a long-run price relationship; when their price ratio
(spread, via a rolling OLS hedge ratio) diverges far from its recent mean
(z-score), it tends to revert. Source article demonstrates this with
JPM/BAC using OLS-regression residuals and z-score thresholds (article's own
example uses +/-1.2 to +/-2.3). Adapted here to the repo's single-symbol
`generate_signals`/`generate_returns` contract: the strategy fetches the
partner leg internally via `data/loaders.py`, computes a rolling-hedge-ratio
spread z-score, and expresses only the "long the spread" (long primary
symbol) direction as a 0/1 position series — a directional simplification
of true market-neutral pairs trading.

## Grid test summary (Step 6)

`param_grid`: `hedge_window in {40,60,90}`, `z_window in {15,20,30}`,
`entry_z in {1.5,2.0}`; `vol_regime_splits=3`; symbols: equity JPM (partner
BAC), crypto ETH/USDT (partner BTC/USDT).

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (JPM/BAC) | 21/54 (0.389) | 16/18 | 3/18 | 2/18 |
| crypto (ETH/BTC) | 0/54 (0.0) | 0/18 | 0/18 | 0/18 |

Best cell: equity, `hedge_window=90, z_window=15, entry_z=1.5`, low-vol
regime, Sharpe 2.56. Worst cell: equity mid-vol, Sharpe -0.49.

**Finding:** the edge is real but almost entirely confined to the low-vol
tercile for JPM/BAC; crypto (ETH/BTC) shows no edge at all across any
regime/param combo — rejected decisively for crypto.

## Single-config validation (Step 7) — best config: hedge_window=90, z_window=15, entry_z=1.5, exit_z=0.3, max_hold_days=15

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.954 | 1.0 |
| Max drawdown | ✅ | 0.213 | 0.25 |
| Transaction cost survival (5bps/trade, 52 trades) | ✅ | 0.927 net Sharpe | 0.5 |
| Walk-forward (manual 4-slice fallback; `vbt.utils.splitting.RangeSplitter` broken in this install, same pre-existing repo-wide gap noted in prior reports) | ✅ | 3/4 splits positive | 0.75 |
| Parameter sensitivity (18-cell equity grid) | ✅ (borderline) | relative_std 0.471 | 0.5 |

## Decision: **REJECTED** (near-miss)

Full-period (all vol regimes combined) Sharpe of 0.954 falls just short of
the 1.0 threshold — consistent with the grid finding that the edge is
concentrated in low-vol regimes and gets diluted by mid/high-vol periods
where the mean-reversion assumption breaks down. All other validators
(MDD, TC-survival, walk-forward, param-sensitivity) passed, including the
borderline param-sensitivity result.

**Notes for future iterations:** this is a near-miss worth revisiting with
an explicit low-vol-regime gate (similar to `2026-09-03_bb_meanrev_qqq_volregime.py`'s
pattern) — restricting trading to when JPM/BAC's own realized vol is below
its trailing median might push full-sample Sharpe above 1.0 given the grid
already shows 16/18 low-vol cells passing. Also worth testing other
same-sector equity pairs (e.g. XOM/CVX, KO/PEP) since JPM/BAC's
relationship may itself be idiosyncratic (both mega-cap money-center banks
with very similar beta/rate sensitivity — the pair may be "too correlated"
for JPM/BAC-specific news divergence to matter as much as sector-wide moves).
