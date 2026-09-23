# Backtest Report: 52-Week-High Nearness Momentum, OBV-Confirmed (2026-09-23)

**Strategy file:** `strategies/2026-09-23_52wk_high_obv_confirmed.py`
**Hypothesis id:** 2026-09-23-133

## Hypothesis

Combines two building blocks already validated separately in this repo: the
52-week-high nearness anchoring effect (George & Hwang 2004; accepted for
QQQ in `strategies/2026-09-23_52wk_high_nearness_momentum.py`, near-miss on
SPY) and On-Balance Volume trend confirmation (Granville 1963; tested
standalone this cron trigger in `strategies/2026-09-23_obv_sma_trend_rsi_gate.py`,
rejected on walk-forward but edge concentrated in low/mid-vol equity).
Requiring OBV to be rising (above its own SMA) at the moment of a
52-week-high nearness breakout should filter "hollow" breakouts lacking
volume conviction. Sources this iteration (SERP-corroborated "52-week high +
volume confirmation" summaries; primary PDF 404'd, so parameters reuse this
repo's own already-validated building blocks rather than fabricated new
numbers — web_search DDGS/Yahoo backend TLS-errored on all queries, browser_exec
Google SERP fallback used throughout).

## Step 6 grid summary

Grid: `entry_threshold ∈ {0.92,0.95}`, `exit_threshold ∈ {0.80,0.85}`,
`obv_sma_window ∈ {10,20}` × equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT)
× `vol_regime_splits=3`, 2019-01-01 to 2026-09-01. 96 cells total.

- `pass_fraction`: **0.4375** (42/96)
- `by_asset_class`: equity 20/48 (41.7%), crypto 22/48 (45.8%)
- `by_vol_regime`: low 22/32 (68.8%), mid 18/32 (56.3%), high 2/32 (6.3%)
- `best_cell`: `entry_threshold=0.95, exit_threshold=0.80, obv_sma_window=10`,
  QQQ, low-vol regime, Sharpe 1.832
- `worst_cell`: same params, SPY, low-vol regime, Sharpe -0.436 — QQQ/SPY
  diverge sharply even in the same grid cell, consistent with the parent
  nearness strategy's QQQ-only edge.

## Single-config validation (QQQ, `entry_threshold=0.92, exit_threshold=0.80,
obv_sma_window=10, hold_days=126, lookback_days=252`, full sample 2019-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.116 | ≥ 1.0 | ✅ |
| Max drawdown | 0.060 | ≤ 0.25 | ✅ |
| Transaction cost survival (10bps/trade, 10 trades) | net Sharpe 1.078 | ≥ 0.5 | ✅ |
| Walk-forward (4 splits, manual workaround) | pass_fraction 0.75 (3/4 splits positive) | ≥ 0.75 | ✅ |
| Parameter sensitivity (`entry_threshold`×`obv_sma_window` 3×2 grid) | relative_std 0.425 | ≤ 0.5 | ✅ (close to threshold) |

**SPY (same config, full-sample):** Sharpe 0.102 — decisively fails, same
divergence pattern as the parent nearness strategy.

Note on walk-forward: same manual 4-chunk workaround as this cron trigger's
earlier OBV iteration (`validation/validators.py::check_walk_forward`
currently broken on the installed vectorbt version).

## Decision: **ACCEPTED (QQQ only)**

All 5 validators pass on QQQ with only 10 trades over 7.7 years (low
turnover, consistent with a long 6-month holding period). Parameter
sensitivity is close to the 0.5 threshold (0.425) — flagging as a caveat:
`entry_threshold=0.90` performs much worse (Sharpe 0.221) than 0.92/0.95,
suggesting some cliff-edge sensitivity below 0.92 that a future loop should
watch for if retuning. **Rejected for SPY** (Sharpe 0.102, decisive) and for
crypto (not tested at the single-config level given the grid's already weak
0.4375 crypto sub-pass-rate and the equity-specific anchoring-bias thesis).
Scope: QQQ only, same as the parent strategy.
