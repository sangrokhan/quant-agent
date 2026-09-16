# VPT Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_vpt_sizing_sma_trend.py`
**Hypothesis:** Volume Price Trend (VPT) rate-of-change, rolling z-scored and
tanh-squashed, used as a continuous exposure-sizing dial within an
SMA(trend_window) uptrend gate + deadband. First VPT-as-continuous-sizing
variant in this repo — rescues/generalizes the repo's one prior binary VPT
signal-line-crossover entry (2026-09-05-076, accepted QQQ only, rejected
SPY/crypto).

**Source:** https://www.investopedia.com/terms/v/vptindicator.asp (VPT
formula and momentum-strength interpretation; read via browser_exec this
iteration — web_search's DuckDuckGo backend intermittently erroring/empty
this run).

## Step 6 grid summary (432 cells: trend_window x {30,40,50}, vpt_roc_window
x {10,20,30}, sensitivity x {0.5,0.7}, deadband x {0.15,0.20}, 2 equity + 2
crypto symbols, vol_regime_splits=3)

- Overall pass_fraction: **0.4745** (205/432)
- By asset class: equity 131/216 (0.606); crypto 74/216 (0.343)
- By vol regime: low 116/144 (0.806); mid 89/144 (0.618); high **0/144 (0.0)**
  — strategy categorically fails in high-realized-vol regimes across the
  entire grid (deadband/trend-gate mechanics whipsaw badly when vol spikes).
- Best cell: SPY, trend_window=50/vpt_roc_window=30/sensitivity=0.7/deadband=0.15,
  low-vol regime, Sharpe 2.60.
- Worst cell: SPY, trend_window=50/vpt_roc_window=30/sensitivity=0.5/deadband=0.2,
  high-vol regime, Sharpe 0.06.

Best-average-Sharpe config per symbol (averaged across the 3 vol-regime
cells for that param combo):
- QQQ: trend_window=50/vpt_roc_window=20/sensitivity=0.5/deadband=0.15 → avg Sharpe 1.585, pass_frac 0.667
- SPY: trend_window=40/vpt_roc_window=20/sensitivity=0.5/deadband=0.20 → avg Sharpe 1.506, pass_frac 0.667
- BTC/USDT: trend_window=50/vpt_roc_window=10/sensitivity=0.5/deadband=0.15 → avg Sharpe 1.425, pass_frac 0.333 (crypto default leverage_cap=1.0 before retune)
- ETH/USDT: pass_frac 0.0 at any grid combo tested (full-sample-relevant param avg Sharpe 1.365, but all individual vol-regime cells fail on MDD/Sharpe threshold combo)

## Step 7 single-config validators (best-per-symbol config; crypto retuned to
leverage_cap=0.3, base_exposure=0.15 per this repo's standard leverage-cap-
aware crypto retune)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.318 (pass) | 0.115 (pass) | 0.622 (pass) | 0.75 (pass, 3/4 splits) | 0.044 rel-std (pass) | **YES** |
| SPY | 1.215 (pass) | 0.090 (pass) | 0.533 (pass) | 0.75 (pass, 3/4 splits) | 0.032 rel-std (pass) | **YES** |
| BTC/USDT | 0.185 (fail) | 0.151 (pass) | -0.063 (fail) | 1.0 (pass) | 0.083 rel-std (pass) | NO — decisive Sharpe+TC fail even after leverage-cap retune |
| ETH/USDT | 0.205 (fail) | 0.149 (pass) | -0.059 (fail) | 1.0 (pass) | 0.034 rel-std (pass) | NO — decisive Sharpe+TC fail even after leverage-cap retune |

## Decision

**Accepted: QQQ and SPY (equity).** All 5 validators pass at the grid-optimal
per-symbol config.

**Rejected: BTC/USDT and ETH/USDT (crypto).** Decisive Sharpe and
transaction-cost-survival failure at both the grid-optimal config and a
leverage-cap-retuned config (leverage_cap=0.3, base_exposure=0.15) — VPT's
volume-weighted pct-change construction appears to generate too much noisy
turnover on crypto's 24/7, higher-vol calendar to clear net-of-cost Sharpe,
consistent with several other continuous-sizing-dial strategies in this repo
that pass equity but fail crypto even after the standard leverage retune.

**Notable finding for future loops:** the grid's `by_vol_regime` breakdown
shows this strategy (VPT-ROC continuous dial) categorically fails in
high-realized-vol regimes (0/144 cells) regardless of asset class or
parameter combo — the accepted equity configs are being carried almost
entirely by low/mid-vol-regime performance. A future iteration could try
gating exposure to zero (or reducing sensitivity) specifically during
high-vol terciles as a targeted fix, rather than a blanket parameter retune.
