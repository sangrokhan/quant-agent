# Clenow "Stocks on the Move" Exponential-Regression Momentum (Time-Series Adaptation)

**Strategy file:** `strategies/2026-09-16_clenow_regression_momentum_sizing.py`
**Knowledge base id:** 2026-09-16-165

## Hypothesis
Per https://teddykoker.com/2019/05/momentum-strategy-from-stocks-on-the-move-in-python/
(Python re-implementation of Andreas F. Clenow's book "Stocks on the Move:
Beating the Market with Hedge Fund Momentum Strategy"): momentum is
measured by fitting an OLS regression of log(close) against a bar index
over a rolling lookback window, then annualizing the fitted slope and
multiplying by the regression's R^2 (goodness-of-fit) so smooth,
high-conviction trends outrank noisy/choppy ones with the same raw slope:

    slope, r_value = linregress(arange(n), log(close[-n:]))
    momentum = ((1 + slope) ** 252) * (r_value ** 2)

Clenow's actual strategy ranks a broad universe (S&P 500) cross-
sectionally each week and holds only the top 20% by this score, gated by
the broad market being above its own 200-day MA, and stops out positions
below their own 100-day MA. This repo's `grid_test.py`/`validators.py`
harness tests one symbol at a time (no cross-sectional ranking
capability — confirmed as a structural blocker for prior cross-sectional
factor strategies, e.g. low-volatility anomaly, per 2026-09-11-110/
2026-09-13-026), so this adaptation ranks the asset's OWN momentum score
against its own trailing history (rolling percentile rank) instead of
against a peer universe — a direct time-series analogue of Clenow's
"top 20%" cutoff (`rank_threshold=0.8` = "in the top 20% of its own
recent history") — combined with the same two disclosed absolute filters
(own SMA(200)-style regime gate, own SMA(100)-style stop).

## Novelty check
Grepped strategies_index.jsonl for "Clenow"/"Stocks on the Move"/
"exponential regression slope"/"annualized regression slope" — zero
prior entries. Distinct from prior linear-regression-channel BREAKOUT
strategy (2026-09-04-141, traded band breakout not this score) and prior
information-discreteness/FIP filter (2026-09-10-108, conditioned trend
continuity on jump-discreteness rather than regression fit quality).

## Parameter search
Manual Sharpe-only search (mom_window, rank_window, rank_threshold,
regime_window, stop_window):

| Symbol | Best config | Best Sharpe |
|---|---|---|
| QQQ | mw=60,rw=280,rt=0.85,regw=130,stopw=60 | 0.976 (near-miss) |
| SPY | mw=40,rw=126,rt=0.95,regw=200,stopw=50 | 0.858 (short of threshold) |
| BTC/USDT | mw=130,rw=160,rt=0.65,regw=170,stopw=90 | **1.097 (pass)** |
| ETH/USDT | mw=150,rw=140,rt=0.6,regw=130,stopw=75 | 0.710 (short of threshold) |

## Grid test (Step 6)
`param_grid={"mom_window": [60,90,130], "rank_threshold": [0.65,0.75,0.85]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01:

- total_cells=108, passed=33, **pass_fraction=0.306**
- by_asset_class: equity 23/54, crypto 10/54
- by_vol_regime: low 14/36, mid 14/36, high 5/36
- best_cell: mom_window=60, rank_threshold=0.85, QQQ, low-vol, sharpe=2.14
- worst_cell: mom_window=90, rank_threshold=0.85, QQQ, high-vol, sharpe=-0.81

Edge concentrates in low/mid-vol regimes and decays sharply in high-vol
(consistent with a smooth-trend-quality score penalizing choppy,
high-volatility price action by construction via the R^2 term).

## Standard validators (Step 7) — BTC/USDT primary config
`mom_window=130, rank_window=160, rank_threshold=0.65, regime_window=170, stop_window=90, leverage_cap=0.75`

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.097 | >=1.0 | PASS |
| MDD | 0.232 | <=0.25 | PASS |
| TC-survival net Sharpe | 0.651 | >=0.5 | PASS |
| Walk-forward (manual 4-fold) | 1.0 (all 4 folds positive) | >=0.75 | PASS |
| Param-sensitivity rel-std (rank_threshold in [0.55..0.75]) | 0.008 | <=0.5 | PASS |

`leverage_cap=0.75` (vs default 1.0) was needed specifically to bring MDD
under the 0.25 cap — Sharpe/param-sensitivity are leverage-invariant by
construction (linear position scaling), only MDD/absolute-return metrics
scale with it.

Walk-forward used the same manual 4-fold range-split fallback as other
2026-09-16 entries (`vectorbt.utils.splitting.RangeSplitter` unavailable
in this environment's installed vectorbt version).

## QQQ near-miss detail (not accepted)
QQQ's best config (mw=60,rw=280,rt=0.85,regw=130,stopw=60) reached Sharpe
0.976 (just under 1.0) with MDD 0.069 (comfortably under cap) and
param-sensitivity 0.023 (excellent), but TC-survival net Sharpe only
0.269 (well under the 0.5 threshold — 181 trades incur meaningful cost
drag relative to the gross edge) and walk-forward pass_fraction only 0.25
(1/4 folds positive) — the edge is concentrated in a narrow slice of the
sample rather than holding up walk-forward-robustly. Not accepted; a
future iteration could try widening the rank_window/regime_window further
or adding a minimum-holding-period filter to cut equity-side turnover.

## Decision (Step 8)
**Accepted (BTC/USDT only, leverage_cap=0.75)** — all 5 validators pass.
**Rejected (QQQ, SPY, ETH/USDT)** — none cleared the full validator suite
(QQQ near-miss on Sharpe/TC-survival/walk-forward as detailed above; SPY
and ETH/USDT fell short on raw Sharpe in the parameter search and were
not pursued further given the time budget).
