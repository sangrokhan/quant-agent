# Pivot Point SuperTrend Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_pp_supertrend_sizing_sma_trend.py`
**Hypothesis:** Pivot Point SuperTrend (LonesomeTheBlue) — instead of
anchoring ATR trailing bands to raw price/hl2 like classic SuperTrend, this
construction anchors them to a weighted-average pivot-point center line
(`center := (center*2 + lastpivot)/3` on each confirmed swing pivot),
giving the trailing-stop a smoother, less noise-reactive base. Reframed as a
continuous sizing dial: (close - trailing_line)/ATR, rolling z-scored +
tanh, within an SMA(trend_window) uptrend gate + deadband. First Pivot
Point SuperTrend strategy in this repo.

**Source:** https://github.com/fmzquant/strategies/blob/master/Pivot-Point-Supertrend.md
(original LonesomeTheBlue Pine Script, read via browser_exec this iteration
— web_search's DuckDuckGo backend intermittently failing with TLS errors on
this query, Google SERP fallback used).

## Step 6 grid summary (576 cells: trend_window x{30,40,50}, pivot_period
x{3,5}, atr_factor x{2.0,3.0}, sensitivity x{0.5,0.7}, deadband x{0.15,0.20},
2 equity + 2 crypto symbols, vol_regime_splits=3)

- Overall pass_fraction: **0.4149** (239/576)
- By asset class: equity 167/288 (0.580); crypto 72/288 (0.250)
- By vol regime: low 144/192 (0.750); mid 95/192 (0.495); high **0/192
  (0.0)** — same categorical high-vol-regime failure pattern observed in
  other continuous-sizing-dial strategies logged this cron trigger (VPT
  2026-09-17-104, LWMA 2026-09-17-105).
- Best cell: QQQ, trend_window=50/pivot_period=3/atr_factor=3.0/
  sensitivity=0.5/deadband=0.2, low-vol regime, Sharpe 2.77.
- Worst cell: SPY, trend_window=50/pivot_period=5/atr_factor=3.0/
  sensitivity=0.7/deadband=0.2, high-vol regime, Sharpe -0.35.

Best-average-Sharpe config per symbol:
- QQQ: trend_window=50/pivot_period=3/atr_factor=3.0/sensitivity=0.5/deadband=0.20 → avg Sharpe 1.538, pass_frac 0.667
- SPY: trend_window=30/pivot_period=5/atr_factor=2.0/sensitivity=0.7/deadband=0.15 → avg Sharpe 1.433, pass_frac 0.667
- BTC/USDT: trend_window=40/pivot_period=5/atr_factor=2.0/sensitivity=0.5/deadband=0.20 → avg Sharpe 1.581, pass_frac 0.667 (best crypto pass_frac observed this cron trigger, but see single-config result below)
- ETH/USDT: trend_window=50/pivot_period=5/atr_factor=2.0/sensitivity=0.7/deadband=0.20 → avg Sharpe 1.293, pass_frac 0.333 (best config specifically for ETH)

## Step 7 single-config validators (best-per-symbol config; crypto retuned
to leverage_cap=0.3, base_exposure=0.15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.429 (pass) | 0.142 (pass) | 1.000 (pass) | 0.75 (pass) | 0.061 rel-std (pass) | **YES** |
| SPY | 1.161 (pass) | 0.086 (pass) | 0.308 (fail) | 1.0 (pass) | 0.060 rel-std (pass) | NO — TC-survival near-miss |
| BTC/USDT | 0.189 (fail) | 0.162 (pass) | -0.060 (fail) | 1.0 (pass) | 0.030 rel-std (pass) | NO — decisive |
| ETH/USDT | 0.263 (fail) | 0.206 (pass) | -0.047 (fail) | 1.0 (pass) | 0.030 rel-std (pass) | NO — decisive |

Note: the grid's per-cell averaged Sharpe for BTC/USDT (0.789, pass_frac
0.667 at leverage_cap=1.0 default) looked promising, but that grid used the
DEFAULT leverage_cap=1.0, whereas the single-config validator applies this
repo's standard leverage-cap-aware crypto retune (leverage_cap=0.3), which
sharply cuts both gross Sharpe and turnover-adjusted net Sharpe here —
unlike several other strategies in this repo where the retune rescues
crypto, this one still fails decisively even after retuning, likely because
turnover stays very high (4233 trades over the sample) regardless of
leverage scaling since num_trades depends on the deadband/dial dynamics,
not the leverage cap itself.

## Decision

**Accepted: QQQ only.** All 5 validators pass.

**Rejected: SPY** (transaction-cost survival near-miss, net Sharpe
0.308<0.5 threshold, despite Sharpe/MDD/WF/param-sensitivity all passing) —
flagged as a near-miss worth a targeted turnover-reduction fix (wider
deadband) in a future iteration.

**Rejected: BTC/USDT and ETH/USDT** (decisive Sharpe and TC-survival
failure even after the standard leverage-cap-aware retune; very high
turnover, 3900-4200 trades over the sample, driven by the pivot-based
center line reacting to every new confirmed swing pivot on crypto's higher-
frequency volatility).

**Notable finding for future loops:** this strategy reconfirms the
categorical high-vol-regime failure pattern (0/192 cells) already flagged
twice this cron trigger (VPT 2026-09-17-104, LWMA 2026-09-17-105) — now
observed across three structurally distinct indicator families (volume-
weighted momentum, dual-window moving average, ATR trailing-stop/pivot
line), suggesting this may be a shared limitation of the z-score-tanh-dial +
SMA-trend-gate + deadband mechanic itself under this repo's fixed
transaction-cost model during high-realized-vol periods, rather than an
indicator-specific weakness. Worth a standalone investigation (e.g. does
widening the deadband or reducing sensitivity specifically during high-vol
terciles rescue any of these three near-misses) in a future iteration.
