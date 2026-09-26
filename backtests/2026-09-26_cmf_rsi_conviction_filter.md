# Backtest Report: CMF/RSI Conviction-Disagreement Filter

**Strategy file:** `strategies/2026-09-26_cmf_rsi_conviction_filter.py`
**KB id:** 2026-09-26-069
**Outcome:** REJECTED (decisive)

## Hypothesis

Source: https://enlightenedstocktrading.com/chaikin-money-flow/ ("Filtering
Overbought and Oversold Conditions" rule family) — "If the trading platform
shows oversold levels but CMF remains strong, it suggests the downward
trend may lack conviction, providing a potential buying opportunity."

Operationalized: long entry when RSI(14) crosses below an oversold
threshold (25/30/35) AND CMF(20) > a strength floor (-0.05/0/0.05) at the
SAME bar (price-only "oversold" reading disagrees with volume-weighted
CMF, so the price dip is faded), gated by close > SMA(200). Exit on RSI
recovering to 50, CMF turning negative, or a 15-day time-stop.

Distinct from this repo's existing CMF entries: 2026-09-07-016 (CMF
zero-cross confirmed by a price breakout above a swing high) and
2026-09-05-047 (CMF/price swing-low divergence) — neither uses a same-bar
indicator-disagreement construction with no swing-point detection.

## Grid summary (Step 6)

`param_grid={rsi_oversold:[25,30,35], cmf_strength_floor:[-0.05,0,0.05]}`,
symbols equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
108 total cells, 2016-01-01 to 2026-09-01.

| Metric | Value |
|---|---|
| pass_fraction | **0.0 (0/108)** |
| by_asset_class | equity 0/54, crypto 0/54 |
| by_vol_regime | low 0/36, mid 0/36, high 0/36 |
| best_cell | BTC/USDT, rsi_oversold=35, cmf_strength_floor=0.05, mid-vol tercile, Sharpe 0.807 (still below threshold) |
| worst_cell | BTC/USDT, rsi_oversold=35, cmf_strength_floor=-0.05, high-vol tercile, Sharpe -0.814 |

Zero passing cells anywhere in the grid — the single decisive worst result
of this cron trigger so far.

## Single-config validation (Step 7) — best-adjacent config, full sample, QQQ

(Ran the best available grid params on QQQ full-sample as the primary
config since the grid's actual best cell used a narrow crypto mid-vol
slice; full-sample QQQ is representative of the broader failure.)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | -0.143 | ≥ 1.0 |
| Max drawdown | PASS | 0.048 | ≤ 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe -0.164 (2 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken, established repo workaround) | **FAIL** | 0/4 splits positive (0.0) | ≥ 0.75 |

Extremely sparse signal (only 2 trades over the full ~10.7yr QQQ sample at
the grid's best params) — the RSI-oversold-cross AND CMF>floor AND
uptrend-gate conjunction is a very rare joint event, and when it does fire
it does not produce a reliable edge (negative Sharpe on the sparse sample).

## Decision

**Reject (decisive).** The indicator-disagreement framing does not survive
even loosely — 0/108 grid cells passed, confirming the hypothesis: a
price-only "oversold" reading paired with volume-weighted "no real
selling pressure" is not a useful contrarian signal on this repo's
existing SMA(200)-trend-gated conjunction structure. Strategy file
retained in `strategies/` as a rejected-attempt record (not live).
