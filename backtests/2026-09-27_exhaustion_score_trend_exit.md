# Backtest Report: Multi-Dimensional Exhaustion Score Trend Exit

**Strategy file:** `strategies/2026-09-27_exhaustion_score_trend_exit.py`
**Hypothesis ID:** 2026-09-27-093 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Per Draconic's "Exhaustion Detection Framework"
(https://draconic.ai/tradecraft/exhaustion-detection-framework, read via
`browser_exec` — `web_extract`'s ddgs backend is search-only), trend
exhaustion is detectable across THREE independent dimensions before price
confirms a reversal: (1) velocity deceleration across successive swings,
(2) swing duration expansion beyond the trailing average, (3) combined
statistical extremes (>=2 of {velocity, range, swing-magnitude} percentile
at/above the 90th percentile simultaneously). Source's own disclosed
decision rule: 0/3 dimensions active = healthy trend; 1/3 = early warning;
**2/3 = exit trend-following positions**; 3/3 = strong exhaustion exit.
Adapted from the source's intraday-session framing to daily OHLCV via a
percentage-deviation ZigZag swing construction, with a trailing rolling
percentile substituting for the source's intraday-session percentile. Used
as an EXIT overlay on a baseline SMA(trend_window) trend-following long
entry — exit on exhaustion score >= exit_min_score OR a trend break,
whichever comes first. First multi-dimensional swing-based exhaustion
scoring construction in this repo (distinct from every prior single-metric
divergence/exhaustion strategy already tested).

## Single-config validation (QQQ, 2015-01-01 to 2026-09-01)

Config: `trend_window=150, deviation_pct=0.05, exit_min_score=3`

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.085 | ≥ 1.0 | ✅ |
| Max drawdown | 0.244 | ≤ 0.25 | ✅ |
| Transaction cost survival (15bps/trade, 69 trades) | net Sharpe 0.992 | ≥ 0.5 | ✅ |
| Walk-forward (4-split manual) | 0.75 pass fraction (3/4 splits positive) | ≥ 0.75 | ✅ |
| Parameter sensitivity (deviation_pct∈{0.03,0.05,0.08} × exit_min_score∈{2,3}) | rel. std 0.334 | ≤ 0.5 | ✅ |

All 5 validators pass for QQQ at this config (walk-forward exactly at the
0.75 threshold — 1 of 4 splits was negative, the earliest chronological
quarter). **Accepted (QQQ only).**

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {50,100,150}`, `deviation_pct ∈ {0.03,0.05,0.08}`,
`exit_min_score ∈ {2,3}` × symbols `{QQQ,SPY}` (equity), `{BTC/USDT,
ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid` (pass criteria: Sharpe≥1.0 AND
MDD≤0.25 per cell).

- **Overall pass_fraction: 0.097** (21/216 cells)
- **By asset class:** equity 21/108 (0.194) pass; crypto 0/108 (0.00) —
  decisive crypto reject at all tested configs.
- **By vol regime:** low 16/72 (0.222); mid 5/72 (0.069); high 0/72
  (0.00) — same high-vol-regime universal-failure pattern seen across this
  cron trigger's other constructions; the exhaustion-score exit (which
  requires >=2 converging dimensions) apparently reacts too slowly during
  the sharpest regime shifts to avoid drawdown.
- **Best cell:** crypto ETH/USDT, mid-vol, `trend_window=50,
  deviation_pct=0.03, exit_min_score=3`, Sharpe 2.305 — an isolated
  high-Sharpe cell within crypto's overall 0/108 pass rate, not pursued
  as a crypto config.
- **Worst cell:** equity SPY high-vol, Sharpe -0.728.

The accepted QQQ full-sample config (`trend_window=150`) is at the wide
end of the grid's tested range — a follow-up full-sample sweep across
symbols confirmed SPY tops out at Sharpe 0.602 (best config
`trend_window=100, deviation_pct=0.03, exit_min_score=3`), a decisive
Sharpe fail despite acceptable MDD (0.194) at that config.

## Decision

**Accept: QQQ only**, `trend_window=150, deviation_pct=0.05,
exit_min_score=3`. Reject SPY (decisive Sharpe fail at every tested
config) and both crypto pairs (0/108 grid cells) — scope the strategy
narrowly to QQQ per the honest-narrow-scope principle in RESEARCH_LOOP.md
Step 6. High-vol regimes broadly and crypto are out of scope for this
construction.
