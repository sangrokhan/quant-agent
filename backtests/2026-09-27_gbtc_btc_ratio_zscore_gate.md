# Backtest Report: GBTC/BTC Ratio Z-Score Regime Gate on SMA Trend

**Strategy file:** `strategies/2026-09-27_gbtc_btc_ratio_zscore_gate.py`
**Hypothesis ID:** 2026-09-27-095 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

GBTC (Grayscale Bitcoin Trust) historically traded at a market price that
could deviate substantially from its underlying BTC NAV (premium during
institutional demand/bull euphoria, deep discount during capitulation/
liquidity stress — e.g. the 2022 FTX-collapse discount exceeded -40%). A
prior iteration this repo (2026-09-27-074) rejected a direct GBTC-premium
strategy at the feasibility-screening stage because a dedicated GBTC-NAV
feed isn't available via `data/loaders.py`. This iteration sidesteps that
blocker: GBTC (yfinance) and BTC/USDT (ccxt) are BOTH already loadable via
existing `data/loaders.py` wrappers, so a rolling z-score of the raw
GBTC-market-price / BTC-spot-price RATIO (which normalizes away the fixed
BTC-per-share conversion factor, leaving only relative deviation from its
own trailing mean/std — a genuine premium/discount signal proxy) can be
computed with zero new data-source work. Used as a risk-off regime gate
(flatten when the ratio z-score is unusually low, i.e. deep "discount"
episode) on a primary asset's SMA(trend_window) trend-following signal,
plus a `min_hold_days` hysteresis to control whipsaw trade frequency.

## Single-config validation (2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Param sens. | Result |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, zscore_window=120, low_z=-1.0, min_hold_days=15 | 1.188 ✅ | 0.221 ✅ | 0.970 ✅ | 1.00 ✅ | 0.100 ✅ | **PASS** |
| SPY | trend_window=30, zscore_window=90, low_z=-2.0, min_hold_days=12 | 1.168 ✅ | 0.150 ✅ | 0.909 ✅ | 0.75 ✅ | 0.077 ✅ | **PASS** |

All 5 validators pass for BOTH QQQ and SPY. Note: an earlier config
without `min_hold_days` (raw daily re-evaluation) passed Sharpe/MDD/
walk-forward/param-sensitivity but FAILED transaction-cost-survival on
both symbols (279 and 185 trades respectively drove net Sharpe below the
0.5 threshold) — adding a `min_hold_days` hysteresis (reducing turnover
to 83/82 trades) rescued both to a clean pass.

## Grid-test summary (Step 6)

Grid (pre-min_hold_days rescue): `trend_window ∈ {30,50,80}`,
`zscore_window ∈ {60,90,120}`, `low_z_threshold ∈ {-1.0,-1.5,-2.0}` ×
symbols `{QQQ,SPY}` (equity), `{BTC/USDT,ETH/USDT}` (crypto) ×
vol_regime_splits=3, using `validation/grid_test.py::run_strategy_grid`.

- **Overall pass_fraction: 0.315** (102/324 cells) — the highest grid
  pass_fraction of this cron trigger's iterations.
- **By asset class:** equity 77/162 (0.475); crypto 25/162 (0.154) — the
  best crypto grid result of this trigger's iterations, though crypto's
  full-sample sweep showed high Sharpe (>1.5 for BTC/USDT) alongside
  consistently high MDD (0.37-0.57), never clearing the 0.25 MDD
  threshold — crypto's own extreme volatility means the same trend +
  regime-gate mechanism captures strong risk-adjusted (Sharpe) returns
  but with drawdowns well outside this repo's MDD bar. Crypto NOT
  pursued for acceptance this iteration.
- **By vol regime:** low 77/108 (0.713); mid 25/108 (0.231); high 0/108
  (0.00) — same universal high-vol-regime failure pattern as other
  constructions this trigger, though the low-vol-regime pass rate here is
  the strongest seen this trigger.

## Decision

**Accept: QQQ and SPY** (both symbols, per-symbol tuned configs above).
**Reject crypto (BTC/USDT, ETH/USDT)** — decisive MDD failure at every
tested config despite attractive Sharpe, consistent with crypto's known
higher tail-risk profile; scope this strategy to equity only per the
honest-narrow-scope principle in RESEARCH_LOOP.md Step 6.
