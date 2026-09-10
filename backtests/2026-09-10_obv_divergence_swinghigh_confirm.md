# OBV Bullish Divergence + Swing-High Breakout Confirmation

**Hypothesis / source:** Google AI-overview synthesis (TradersPost/Phemex/
equiti.com sourced) via browser_exec Google SERP fallback of OBV bullish
divergence rules: price records a lower low while OBV records a higher low
(hidden accumulation); entry confirmed when close breaks above the
intermediate swing high between the two lows; optional 50-SMA trend filter
and RSI>30 recovery filter to avoid falling knives. Distinct from this
repo's existing 2026-09-04-088 OBV-divergence entry (EMA cross-back
confirmation, no trend/RSI filter) via the swing-high breakout mechanic and
added trend+RSI gating.

**Grid summary (scripts/run_grid_obv_divergence.py, 216 cells: 3 lookback
x 2 trend_window x 3 max_hold_days x 2 asset classes x 2 symbols x 3 vol
regimes):**
- pass_fraction: 0.1065 (23/216)
- by_asset_class: equity 23/108; **crypto 0/108 (decisive)**
- by_vol_regime: low 11/72, mid 1/72, high 11/72
- best_cell: SPY, lookback=30/trend_window=100/max_hold_days=20, low-vol,
  Sharpe 2.06
- worst_cell: QQQ, same params but max_hold_days=15, low-vol, Sharpe -0.99
  (high param sensitivity even within low-vol tercile)

**Single-config validators (lookback=30, trend_window=100,
max_hold_days=20, 2017-01-01 to 2026-09-01):**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL 0.433 | FAIL 0.372 |
| Max drawdown (<=0.25) | PASS 0.107 | PASS 0.128 |
| TC survival (10bps, N trades) | FAIL 0.402 (11 trades) | FAIL 0.335 (9 trades) |
| Walk-forward (4 manual splits, >=0.75) | PASS 0.75 | PASS 1.0 |
| Parameter sensitivity (18-cell sweep, <=0.5) | PASS 0.412 | **FAIL 1.332** |

**Verdict: REJECTED.** Both QQQ and SPY fail Sharpe and transaction-cost
survival decisively (full-sample Sharpe ~0.35-0.43 vs 1.0 threshold); SPY
additionally fails parameter sensitivity catastrophically (relative std
1.33, driven by a near-zero mean Sharpe of 0.119 across the 18-cell sweep
-- the strategy's performance swings wildly, even sign-flipping, across
adjacent parameter choices). Trade counts are also very low (9-11 trades
over ~9.7 years), consistent with the divergence+breakout+trend+RSI
4-condition AND-gate being too restrictive to generate a statistically
meaningful edge. Crypto is a categorical 0/108 across the entire grid,
matching the pattern of most oversold/divergence mean-reversion strategies
in this repo failing on crypto's noisier price action.
