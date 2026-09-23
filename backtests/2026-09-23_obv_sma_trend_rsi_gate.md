# Backtest Report: OBV SMA-Crossover, Trend + RSI Gated (2026-09-23)

**Strategy file:** `strategies/2026-09-23_obv_sma_trend_rsi_gate.py`
**Hypothesis id:** 2026-09-23-129

## Hypothesis

On-Balance Volume (OBV, Granville 1963) rising above its own short-period
SMA, while price is in a confirmed long-term uptrend (50-SMA > 200-SMA) and
RSI(14) is in a neutral-to-bullish 40-70 band (not overbought), signals
genuine accumulation pressure behind a move and precedes further price
advance. Source: NetPicks "Mastering On Balance Volume (OBV)"
(https://www.netpicks.com/mastering-on-balance-volume-obv/, read via
`browser_exec` this iteration — `web_search` DDGS/Yahoo backend TLS-errored
on every query attempted).

Long-only simplification of the source's long/short rule set (this repo's
`generate_signals` contract is a single 0/1 long/flat series); the source's
ATR-based stop-loss/take-profit is approximated with an OBV-cross-down exit,
a trend-gate-flip exit, and a `max_hold_days` time-stop, since intraday
ATR-stop execution isn't representable in this repo's daily-bar
signal/position framework.

## Step 6 grid summary

Grid: `obv_sma_window ∈ {10,20}`, `rsi_low ∈ {30,40}`, `max_hold_days ∈
{15,20,30}` × equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT) ×
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01. 144 cells total.

- `pass_fraction`: **0.306** (44/144)
- `by_asset_class`: equity 38/72 (52.8%), crypto 6/72 (8.3%)
- `by_vol_regime`: low 30/48 (62.5%), mid 12/48 (25%), high 2/48 (4.2%)
- `best_cell`: `obv_sma_window=20, rsi_low=30, max_hold_days=20`, SPY,
  low-vol regime, Sharpe 2.524
- `worst_cell`: `obv_sma_window=10, rsi_low=30, max_hold_days=15`,
  BTC/USDT, mid-vol regime, Sharpe -0.527

Clear pattern: works meaningfully only on equity in low/mid-vol regimes;
decisively weak on crypto and in high-vol regimes across the board.

## Single-config validation (best config: SPY, `obv_sma_window=20,
rsi_low=30, rsi_high=70, max_hold_days=20`, full sample 2019-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.004 | ≥ 1.0 | ✅ |
| Max drawdown | 0.142 | ≤ 0.25 | ✅ |
| Transaction cost survival (10bps/trade, 108 trades) | net Sharpe 0.690 | ≥ 0.5 | ✅ |
| Walk-forward (4 splits, manual — see note) | pass_fraction 0.50 (2/4 splits positive Sharpe) | ≥ 0.75 | ❌ |
| Parameter sensitivity (`obv_sma_window`×`rsi_low` 2×2 grid) | relative_std 0.076 | ≤ 0.5 | ✅ |

**Note on walk-forward:** `validation/validators.py::check_walk_forward`
raised `AttributeError: module 'vectorbt.utils' has no attribute
'splitting'` with the installed vectorbt version (API drift from when the
validator was written) — worked around with a manual 4-chunk `np.array_split`
walk-forward using the same pass criterion (`Sharpe > 0` per split,
`pass_fraction >= 0.75` to pass). Flagging for a future loop to fix the
validator itself.

## Decision: **REJECTED**

All other validators passed, but walk-forward robustness failed (only 2 of
4 chronological splits had positive Sharpe) — the full-sample Sharpe of
~1.0 is not stable across sub-periods, consistent with the grid's own
finding that the edge is concentrated in low/mid-vol equity regimes and
mostly absent in the high-vol tercile and in crypto. Treat as a
regime-dependent near-miss, not a robust standalone strategy.
