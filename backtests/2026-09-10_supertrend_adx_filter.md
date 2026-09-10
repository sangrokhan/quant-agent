# SuperTrend + ADX Trend-Strength Filter

**Hypothesis / source:** Google AI-overview synthesis (Quantzee/FXNX
sourced) via browser_exec Google SERP fallback of "SuperTrend + ADX
filter" strategy guides: SuperTrend (ATR period 10, multiplier 3.0
standard) paired with an ADX(14) trend-strength gate — only take
SuperTrend's bullish long signal when ADX > 25 (source: values above 25
confirm a valid trend; below 25 indicates a ranging/choppy market). This
repo has 7 prior SuperTrend variants (plain flip, RSI dual-confirmation,
choppiness-gated, vol-regime-gated, chandelier dual-confirm) but none
combined it with ADX specifically before this iteration.

**Grid summary (scripts/run_grid_supertrend_adx.py, 108 cells: 3
multiplier x 3 adx_threshold x 2 asset classes x 2 symbols x 3 vol
regimes):**
- pass_fraction: 0.1667 (18/108)
- by_asset_class: equity 18/54; **crypto 0/54 (decisive)**
- by_vol_regime: low 9/36, mid 9/36, **high 0/36** (high-vol tercile is a
  categorical fail — consistent with ADX/trend filters generally failing
  to protect against sharp-vol drawdowns)
- best_cell: SPY, multiplier=3.5/adx_threshold=20, low-vol, Sharpe 2.08
- worst_cell: QQQ, multiplier=3.5/adx_threshold=30, high-vol, Sharpe -1.86

**Single-config validators (multiplier=3.5, adx_threshold=20.0,
2017-01-01 to 2026-09-01):**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL 0.740 | FAIL 0.294 |
| Max drawdown (<=0.25) | PASS 0.178 | **FAIL 0.256** |
| TC survival (10bps, N trades) | PASS 0.679 (44 trades) | FAIL 0.217 (41 trades) |
| Walk-forward (4 manual splits, >=0.75) | PASS 0.75 | PASS 0.75 |
| Parameter sensitivity (9-cell sweep, <=0.5) | FAIL 0.647 | FAIL 3.906 |

**Verdict: REJECTED.** Neither QQQ nor SPY clears the Sharpe threshold on
the grid's best config (0.740/0.294 vs 1.0), and both fail parameter
sensitivity — SPY catastrophically (rel_std 3.91, near-zero mean Sharpe
0.081 across the 9-cell sweep, meaning performance is essentially noise
that happens to spike at one specific multiplier/threshold pair). SPY also
breaches max drawdown (25.6% vs 25% threshold) and fails TC-survival. The
grid's high-vol tercile is a clean 0/36 across all cells — ADX alone does
not protect this ATR-band flip strategy from high-volatility whipsaw/
drawdown any better than the RSI or realized-vol-regime gates already
tried in prior SuperTrend variants. Crypto remains categorically
unsuitable for every SuperTrend variant tested in this repo to date
(0/54 here).
