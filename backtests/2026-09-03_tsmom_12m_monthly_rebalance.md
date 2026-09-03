# Backtest Report: 12-Month Time-Series Momentum, Monthly Rebalance + 200d Trend Filter

**Strategy file:** `strategies/2026-09-03_tsmom_12m_monthly_rebalance.py`
**Date:** 2026-09-03

## Hypothesis

Moskowitz/Ooi/Pedersen's "Time Series Momentum" (2012) academic result uses
a full trailing 12-month (252 trading day) return with **no skip-month**
adjustment, and rebalances **monthly** — both details differ from every
prior momentum attempt in this repo's knowledge base (2026-09-03-002 used a
90-day lookback rebalanced daily; -003 used 45d + daily inverse-vol sizing;
-004 swept 30–90d lookbacks ANDed with a 200d trend filter, still rebalanced
daily and its best cell narrowly missed both Sharpe (SPY 0.94) and MDD (BTC
37.0% vs 35%)). -004's failure was explicitly regime-dependent (83% pass
low-vol vs 4% high-vol), consistent with daily-rebalanced whipsaw. This
iteration tests whether the longer 12-month lookback + monthly rebalance
(position held fixed for a full month, cutting turnover/whipsaw) clears the
bar that shorter, daily-rebalanced variants narrowly missed.

**Source:** https://www.globalequitymomentum.com/articles/lookback-delay —
states Moskowitz/Ooi/Pedersen's TSMOM uses the full trailing 12-month return
with no skip, and that GEM's live signal is checked monthly, not daily; also
argues the "12-1 skip-month" convention is a stock-level-only artifact that
doesn't transfer to broad index/asset-class instruments (relevant since this
repo trades index ETFs and crypto majors, not individual stocks) — read via
`browser_exec` fallback (page rendered fine in-browser; `web_extract` failed
first with a backend error: "DuckDuckGo (ddgs) is a search-only backend and
cannot extract URL content").

## Grid Test (`validation/grid_test.py::run_strategy_grid`)

Grid: `lookback_days` ∈ {126, 189, 252} × `trend_window` ∈ {0, 200} ×
{QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol terciles = 72 cells, 2019-01-01 to
2026-09-01.

- **pass_fraction: 0.208** (15/72)
- by_asset_class: equity 15/36 (41.7%), **crypto 0/36 (0%)**
- by_vol_regime: low 12/24 (50%), mid 3/24 (12.5%), **high 0/24 (0%)**
- best_cell: SPY, lookback_days=189, trend_window=0, low-vol regime, Sharpe 2.85
- worst_cell: ETH/USDT, lookback_days=252, trend_window=200, mid-vol, Sharpe -0.06

Same pattern as nearly every prior momentum/trend strategy in this log:
equity-only, low-vol-only edge; crypto and high-vol regimes fail entirely.

## Single-Config Validators (primary hypothesis config: lookback_days=252, trend_window=200)

| Symbol | Sharpe (≥1.0) | MDD (≤0.25) | Net-of-cost Sharpe (≥0.5) | Param sensitivity (≤0.5 rel.std) | Walk-forward |
|---|---|---|---|---|---|
| QQQ | **0.89 — FAIL** | **0.286 — FAIL** | 0.88 — pass | 0.044 — pass | broken (vectorbt.utils.splitting missing, known repo bug) |
| SPY | **0.87 — FAIL** | 0.176 — pass | 0.85 — pass | 0.055 — pass | broken (same) |

Parameter sensitivity computed over `lookback_days` ∈ {126, 189, 252} at
fixed `trend_window=200`, per symbol (grid_size=3). Both symbols show very
low sensitivity (rel.std 0.04–0.05) — the *lack* of edge is itself stable
across lookback choices, not a fluke of one parameter value.

Trade counts are low (QQQ: 9 trades, SPY: 13 trades over ~7.5 years) as
expected from monthly rebalancing on a strict AND-gated position — this
also means the walk-forward validator (still broken, unfixed since
2026-09-03-002) would have very few trades per split even if it worked.

## Verdict: REJECT

Both QQQ and SPY fail the primary Sharpe gate (0.89 and 0.87 vs 1.0
threshold) — reducing rebalance frequency to monthly and lengthening the
lookback to the full academic 12-month window did **not** clear the bar
that shorter daily-rebalanced variants (-002/-003/-004) also narrowly
missed. QQQ additionally fails MDD (28.6% vs 25% threshold — worse than
several prior accepted momentum-adjacent strategies). The grid confirms the
now-familiar pattern across this repo's ~12 tested momentum/trend variants:
consistent edge only in equity + low-vol regimes, near-total failure in
crypto and high/mid-vol regimes, and full-sample Sharpe on the "headline"
hypothesis config landing just under 1.0 rather than clearing it. Monthly
rebalance reduced turnover/costs (net-of-cost Sharpe ≈ gross Sharpe, as
expected with so few trades) but did not increase the raw return/risk
tradeoff enough to matter for the primary Sharpe gate.

Strategy file and this report kept as a record of a rejected attempt.
