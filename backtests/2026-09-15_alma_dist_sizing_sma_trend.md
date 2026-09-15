# Backtest Report: ALMA Distance Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_alma_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-042

## Hypothesis

ALMA (Arnaud Legoux Moving Average, Legoux & Kouzis-Loukas 2009), per
LuxAlgo's guide
(https://www.luxalgo.com/blog/arnaud-legoux-moving-average-alma-guide/,
visited this iteration): a windowed FIR moving average whose weights
follow a Gaussian bell curve shifted toward recent bars. Given window N,
offset (default 0.85), sigma (default 6): peak m = offset*(N-1), width
s = N/sigma, weight w(i) = exp(-(i-m)^2/(2*s^2)) for i in [0,N-1]; ALMA =
weighted sum of prices / sum of weights. Source's framing: for a given
amount of smoothing, ALMA shows less lag than an SMA and less noise than
an EMA. **First ALMA strategy in this repo (0 prior entries).**

Construction follows this repo's established "distance-from-adaptive-MA
sizing dial" pattern (cf. McGinley Dynamic, FRAMA, Gann HiLo distance
entries): normalized distance = (close - ALMA) / ALMA, rolling z-scored
and tanh-squashed into [-1,+1], used as a continuous exposure-sizing dial
inside an SMA(trend_window) uptrend gate, with a deadband.

## Step 6 — Grid summary (alma_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `alma_window in [14, 20, 30]`, `sensitivity in [0.5, 0.8]`,
  symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
  `vol_regime_splits=3`.
- **72 cells, 35 passed (pass_fraction = 0.486)**.
- By asset class: equity 18/36, crypto 17/36 — roughly balanced.
- By vol regime: low 22/24, mid 12/24, high 1/24.
- Best cell: QQQ, alma_window=30, sensitivity=0.5, low-vol regime, Sharpe 2.80.
- Worst cell: ETH/USDT, alma_window=20, sensitivity=0.8, high-vol regime,
  Sharpe -0.10.

## Step 7 — Single-config validator suite (per-asset-class retuned)

Equity config: `alma_window=20, alma_offset=0.85, alma_sigma=6.0,
sensitivity=0.5, trend_window=40, zscore_window=100, base_exposure=0.4,
leverage_cap=1.0, deadband=0.4`.

Crypto config (leverage-cap-aware retune): same core params,
`base_exposure=0.24, leverage_cap=0.4, deadband=0.15`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.305 (pass) | 0.131 (pass) | 0.763 (pass) | 1.00 (pass) | 0.177 (pass) | **Yes** |
| SPY | 1.143 (pass) | 0.080 (pass) | 0.580 (pass) | 1.00 (pass) | 0.181 (pass) | **Yes** |
| BTC/USDT | 1.453 (pass) | 0.198 (pass) | 0.769 (pass) | 1.00 (pass) | 0.037 (pass) | **Yes** |
| ETH/USDT | 0.950 (fail) | 0.251 (fail, marginal) | 0.528 (pass) | 1.00 (pass) | 0.044 (pass) | No (near-miss) |

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (QQQ, SPY, BTC/USDT); reject ETH/USDT (near-miss)**

Three of four symbols pass all 5 validators cleanly with tight
parameter-sensitivity margins throughout (rel std 0.04-0.18). ETH/USDT is
a genuine near-miss on both Sharpe (0.950 vs 1.0) and MDD (0.251 vs 0.25)
by a very thin margin — a future iteration could retune ETH's deadband/cap
specifically to rescue it. This is the strongest cross-asset result of
this cron trigger's 4 iterations (3/4 symbols passing, tightest
parameter-sensitivity margins observed).
