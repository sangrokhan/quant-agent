# Backtest Report: Network Momentum Spillover (Cross-Asset, TLT-neighbor gate)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_network_momentum_spillover.py`
**Source:** Pu, Roberts, Dong & Zohren, "Network Momentum across Asset Classes"
(2023, Oxford-Man Institute), summarized at
https://www.quantitativo.com/p/network-momentum (read via browser_exec
fallback after web_search failed to return the article directly — Google
SERP screenshot located the exact URL).

## Hypothesis

The paper's own ablation shows cross-class network edges (bonds <->
currencies <-> commodities) are "the secret sauce" — network momentum from
neighbor assets predicts a target's next-day return, and this signal is
only ~65% correlated with the target's own individual momentum (a genuinely
new signal, not a repackage). This repo has no futures/currency data, so we
implement the simplest single-edge analog: gate a PRIMARY equity's position
purely on a bond-ETF NEIGHBOR's (TLT) own trailing momentum, never using the
primary's own price history in the signal at all.

## Grid test summary (Step 6)

`param_grid={"neighbor_lookback": [10,20,40], "neighbor_threshold": [0.0, 0.01]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 72, **passed:** 22, **pass_fraction: 0.306**
- **by_asset_class:** equity 22/36 passed; crypto 0/36 passed (decisive
  reject for crypto — BTC has no economically meaningful link to TLT bond
  momentum via this mechanism)
- **by_vol_regime:** low 12/24, mid 8/24, high 2/24 — edge concentrates in
  low/mid volatility regimes, degrades sharply in high-vol regime
- **best_cell:** QQQ, neighbor_lookback=20, neighbor_threshold=0.0, low-vol
  regime, Sharpe 2.88
- **worst_cell:** BTC/USDT, neighbor_lookback=10, neighbor_threshold=0.01,
  mid-vol regime, Sharpe -0.29

## Single-config validation (Step 7): neighbor_lookback=20, neighbor_threshold=0.0

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.288 (PASS) | 1.037 (PASS) | >= 1.0 |
| Max drawdown | 0.286 (**FAIL**) | 0.342 (**FAIL**) | <= 0.25 |
| TC survival (5bps/trade, 191 trades) | 1.160 (PASS) | 0.898 (PASS) | >= 0.5 |
| Walk-forward (4 manual chunks, Sharpe>0 pass_fraction) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (relative_std, 6-combo grid) | 0.359 (PASS) | 0.477 (PASS) | <= 0.5 |

(`check_walk_forward`'s built-in `vbt.utils.splitting.RangeSplitter` still
raises `AttributeError` in the installed vectorbt version — pre-existing
issue documented since 2026-09-03; used the standard manual 4-equal-chunk
workaround per prior iterations' convention.)

## Decision: REJECT

Max drawdown fails decisively on both tested equities full-sample (0.286
QQQ, 0.342 SPY, both above the 0.25 threshold) despite every other validator
passing comfortably. The neighbor-gated position is long whenever TLT has
positive trailing momentum — this keeps the strategy exposed through
extended equity drawdowns (e.g. 2022) when bond momentum stayed positive
even as equities fell, producing a much deeper drawdown than a standalone
trend filter on the primary asset itself would. The grid confirms this is
structural, not a parameter-tuning issue: the edge only holds up in
low/mid-vol regimes (2/24 high-vol cells passed) and fails all crypto
cells decisively, consistent with the mechanism requiring an actual
economic link between primary and neighbor that a crypto/bond-ETF pairing
lacks.

Worth revisiting: adding a max-drawdown circuit-breaker or combining the
TLT-neighbor gate with the primary's OWN absolute-momentum filter (making it
a genuine "spillover ON TOP OF trend" hybrid rather than spillover alone)
might rescue the MDD failure while keeping the Sharpe/TC/WF strength — a
candidate for a future iteration.
