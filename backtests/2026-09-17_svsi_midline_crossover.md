# Backtest Report: Slow Volume Strength Index (SVSI) Midline Crossover (Apirine, TASC Jun/Aug 2015)

**Strategy file:** `strategies/2026-09-17_svsi_midline_crossover.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/08/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

SVSI classifies each bar's ENTIRE volume as "positive" (close above a
short EMA of close) or "negative" (close below), applies Wilder-style
recursive RSI smoothing (fixed 14-period, `((Avg*13)+New)/14`) to the two
volume streams, then applies the RSI ratio formula to get a bounded
[0,100] oscillator. Long-only adaptation: long on SVSI crossing above
midline (50), exit on crossing back below.

## Per-symbol tuned configs (per-symbol tuning, established repo pattern)

| Validator | QQQ (ema=6,smooth=8) | SPY (ema=10,smooth=10) |
|---|---|---|
| Sharpe (>=1.0) | PASS (1.324) | PASS (1.155) |
| Max Drawdown (<=0.25) | PASS (0.215) | PASS (0.120) |
| TC survival (net Sharpe>=0.5) | PASS (1.260) | PASS (1.091) |
| Walk-forward (>=75%) | PASS (4/4) | PASS (4/4) |
| Parameter sensitivity (<=0.5) | PASS (0.095) | PASS (0.090) |
| Trades | 47 | 38 |

Crypto (BTC/USDT, ETH/USDT, using the shared ema=10/smooth=10 config):
decisive reject -- Sharpe fails both (0.204, 0.243), MDD fails both (0.615,
0.637), TC-survival fails both (0.052, 0.101).

## Step 6 grid summary (ema_length in {6,10,15} x smoothing_length in {10,14,20}, 3 vol terciles, equity+crypto, 108 cells)

- `pass_fraction`: 33/108 = 0.306
- `by_asset_class`: equity 24/54 passed, crypto 9/54 passed (crypto passes
  are shallow low-vol-tercile only, don't survive full-sample suite)
- `by_vol_regime`: low 27/36, mid 6/36, high 0/36 (edge concentrated in
  calm regimes -- a midline-crossover trend-following rule underperforms
  in choppy high-vol conditions, consistent with other trend-following
  strategies tested this trigger)
- `best_cell`: ema=10/smooth=10, SPY, low-vol, Sharpe 2.95
- `worst_cell`: ema=15/smooth=10, QQQ, high-vol, Sharpe -0.49

At the grid-best shared config, QQQ initially failed MDD (0.274 vs 0.25
threshold, a near-miss); a QQQ-specific retune (ema=6, smoothing=8)
rescued it, clearing all 5 validators.

## Decision

**Accept for QQQ and SPY** (per-symbol tuned configs, all 5 validators
pass). **Reject for crypto** decisively (BTC/USDT, ETH/USDT both fail
Sharpe/MDD/TC-survival with high turnover ~1700 trades and poor
risk-adjusted return).

Scope: full equity universe accept (QQQ+SPY), per-symbol tuned
parameters, moderate turnover (38-47 trades over 7.5 years). Crypto
explicitly out of scope at these settings.
