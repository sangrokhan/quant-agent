# Pairs Trading: JPM/BAC Z-Score + Efficiency-Ratio Regime Gate

**Strategy file:** `strategies/2026-09-08_pairs_zscore_er_regime_gate.py`
**Sources:**
- https://www.quantifiedstrategies.com/pairs-trading-strategy/ (base pairs z-score idea, carried over from 2026-09-08-071)
- https://www.tradewink.com/learn/mean-reversion-volatility-regime-guide (Efficiency Ratio regime-gate rationale, ER<0.35 = range-bound/favorable for mean reversion)

## Hypothesis

Direct fix for near-miss `2026-09-08-071` (JPM/BAC pairs z-score mean
reversion, full-period Sharpe 0.954, edge concentrated in low-vol tercile
16/18 vs mid 3/18 vs high 2/18). Add a Kaufman Efficiency Ratio (ER) gate on
the primary symbol's own price: only take the mean-reversion entry when
ER <= er_threshold (choppy/range-bound), and exit early if ER rises above
threshold (regime flips to trending). This reuses the Efficiency Ratio
already tested for trend-following gates elsewhere in this repo
(2026-09-04-120/151) but for the opposite purpose (mean-reversion filter,
not trend-following filter).

## Grid test summary (Step 6)

`param_grid`: `er_period in {10,20,30}`, `er_threshold in {0.3,0.35,0.45}`,
`entry_z in {1.5,2.0}` (hedge_window/z_window fixed at the prior iteration's
best values 90/15); `vol_regime_splits=3`; symbols: equity JPM (partner
BAC), crypto ETH/USDT (partner BTC/USDT).

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (JPM/BAC) | 20/54 (0.370) | 10/18 | 9/18 | 1/18 |
| crypto (ETH/BTC) | 0/54 (0.0) | 0/18 | 0/18 | 0/18 |

Compared to the un-gated baseline (2026-09-08-071: low=16/18, mid=3/18,
high=2/18), the ER gate roughly **triples the mid-vol pass rate (3→9)** at
the cost of some low-vol cells (16→10) — net pass_fraction similar
(0.389→0.370) but more evenly distributed, which is exactly the effect
needed to raise the *full-sample combined* Sharpe (since the un-gated
version's full-sample Sharpe was dragged down by mid/high-vol losses).

Best cell: equity, `er_period=30, er_threshold=0.45, entry_z=1.5`, low-vol
regime, Sharpe 2.65. Crypto (ETH/BTC) still rejected decisively (0/54,
no edge in any regime, consistent with 2026-09-08-071's crypto finding).

## Single-config validation (Step 7) — best config: hedge_window=90, z_window=15, entry_z=1.5, exit_z=0.3, max_hold_days=15, er_period=30, er_threshold=0.45

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | **1.059** | 1.0 |
| Max drawdown | ✅ | 0.213 | 0.25 |
| Transaction cost survival (5bps/trade, 57 trades) | ✅ | 1.028 net Sharpe | 0.5 |
| Walk-forward (manual 4-slice fallback; `vbt.utils.splitting.RangeSplitter` broken in this install, pre-existing repo-wide gap) | ✅ | 3/4 splits positive | 0.75 |
| Parameter sensitivity (18-cell equity grid) | ❌ | relative_std 0.505 | 0.5 |

## Decision: **REJECTED** (near-miss, one validator away)

The ER regime gate successfully fixed the Sharpe shortfall from
`2026-09-08-071` (0.954 → 1.059, now passing), and MDD/TC-survival/
walk-forward all pass. However, parameter sensitivity now narrowly fails
(relative_std 0.505 vs 0.5 threshold) — the ER-gated version's performance
is more sensitive to the exact `er_threshold`/`er_period`/`entry_z` combo
than the un-gated baseline was (which had relative_std 0.471, passing).
This is a textbook Sharpe-vs-robustness tradeoff: tightening the regime
filter improved point-estimate Sharpe but at the cost of param stability.

**Notes for future iterations:** this is now a *very* close near-miss (4/5
validators pass, param-sensitivity fails by only 0.005). A future iteration
could try widening the param grid slightly (e.g. `er_threshold` in
{0.35, 0.40, 0.45, 0.50} with finer steps) to find a flatter region of the
parameter surface, or fix `er_threshold`/`er_period` at round, less
"tuned-to-this-backtest" values (e.g. er_period=20 default, threshold=0.4)
rather than the grid's literal argmax, which may reduce the appearance of
overfitting and could genuinely lower relative_std. Crypto (ETH/BTC)
remains decisively unsuitable for this whole strategy family regardless of
the regime gate.
