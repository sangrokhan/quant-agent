# Heikin-Ashi Smoothed Body Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_ha_smoothed_body_sizing_sma_trend.py`
**Hypothesis:** Heikin-Ashi Smoothed (EMA-smooth raw OHLC first, then
compute standard HA candles) — normalized candle-body strength
(HA_close-HA_open)/ATR reframed as a continuous sizing dial (rolling
z-score + tanh) within an SMA(trend_window) uptrend gate. Repo has 2 prior
binary Dual-HA-Smoothed fast/slow crossover entries (2026-09-09-062, -063,
both rejected). First single-series HA-Smoothed-body continuous-sizing
variant in this repo.

**Source:** Barchart Technical Indicators glossary + MQL5/ForexFactory
corroboration of the smoothing-before-HA construction (read via
browser_exec this iteration; web_search's DuckDuckGo backend intermittently
failing with TLS errors this run).

## Step 6 grid summary (432 cells: trend_window x{30,40,50}, smooth_period
x{6,10,20}, sensitivity x{0.5,0.7}, deadband x{0.15,0.20}, 2 equity + 2
crypto symbols, vol_regime_splits=3)

- Overall pass_fraction: **0.4097** (177/432)
- By asset class: equity 106/216 (0.491); crypto 71/216 (0.329)
- By vol regime: low 123/144 (0.854); mid 54/144 (0.375); high **0/144
  (0.0)** — fourth consecutive entry this cron trigger with this
  categorical high-vol-regime failure pattern (alongside VPT 2026-09-17-104,
  LWMA 2026-09-17-105, Pivot Point SuperTrend 2026-09-17-106).
- Best cell: SPY, trend_window=50/smooth_period=6/sensitivity=0.7/
  deadband=0.15, low-vol regime, Sharpe 2.64.
- Worst cell: QQQ, same params, high-vol regime, Sharpe -0.08.

Best-per-symbol config (by pass_fraction then avg Sharpe):
- QQQ: trend_window=50/smooth_period=20/sensitivity=0.5/deadband=0.20 → pass_frac 0.667, avg Sharpe 1.439
- SPY: trend_window=30/smooth_period=6/sensitivity=0.7/deadband=0.20 → pass_frac 0.333, avg Sharpe 1.428
- BTC/USDT: trend_window=40/smooth_period=20/sensitivity=0.5/deadband=0.20 → pass_frac 0.667, avg Sharpe 1.471 (at default leverage_cap=1.0)
- ETH/USDT: trend_window=50/smooth_period=6/sensitivity=0.5/deadband=0.20 → pass_frac 0.667, avg Sharpe 1.303 (at default leverage_cap=1.0)

## Step 7 single-config validators (best-per-symbol config; crypto retuned
to leverage_cap=0.3, base_exposure=0.15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.301 (pass) | 0.115 (pass) | 0.689 (pass) | 1.0 (pass) | 0.069 rel-std (pass) | **YES** |
| SPY | 1.228 (pass) | 0.087 (pass) | 0.187 (fail) | 1.0 (pass) | 0.044 rel-std (pass) | NO — TC-survival fail |
| BTC/USDT | 0.178 (fail) | 0.143 (pass) | -0.061 (fail) | 1.0 (pass) | 0.036 rel-std (pass) | NO — decisive |
| ETH/USDT | 0.145 (fail) | 0.155 (pass) | -0.065 (fail) | 1.0 (pass) | 0.103 rel-std (pass) | NO — decisive |

Note: crypto's grid-averaged pass_frac (0.667 at default leverage_cap=1.0)
looked strong, but the single-config validator applies the standard
leverage-cap-aware retune (0.3) which sharply cuts gross Sharpe without
proportionally reducing turnover (4325/5812 trades) -- same pattern already
observed for Pivot Point SuperTrend (2026-09-17-106) this cron trigger:
this construction's turnover is dominated by the dial's own z-score/tanh
dynamics rather than the leverage cap, so leverage-cap retuning alone
doesn't rescue crypto here.

## Decision

**Accepted: QQQ only.** All 5 validators pass.

**Rejected: SPY** (TC-survival fail, net Sharpe 0.187<0.5, driven by
elevated turnover at 401 trades — a near-miss worth a targeted deadband-
widening fix in a future iteration, following the same successful pattern
used for the Pivot Point SuperTrend SPY fix this cron trigger,
2026-09-17-107).

**Rejected: BTC/USDT and ETH/USDT** (decisive Sharpe and TC-survival
failure even after leverage-cap retune; very high turnover, 4325-5812
trades over the sample).
