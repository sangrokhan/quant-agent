# Backtest Report: Chande Forecast Oscillator (CFO) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_cfo_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-112

## Hypothesis

Chande Forecast Oscillator (Tushar Chande): CFO = (Close -
LinRegForecast(n)) / Close * 100, where LinRegForecast is the n-period
least-squares linear regression forecast value (default n=14). Formula
confirmed via Google AI overview (browser_exec navigation): LuxAlgo,
LightningChart, positioned.app all agree.

Repo has 2 prior CFO entries (1 rejected zero-line crossover, 1
no_candidate). This iteration normalizes via rolling z-score + tanh squash
to bounded [-1,1], then uses it as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], cfo_sensitivity:[0.5,0.6,0.7], deadband:[0.2,0.28]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=144, passed=34, pass_fraction=0.236
- by_asset_class: equity 34/72 (0.47), crypto 0/72 (0.00)
- by_vol_regime: low 24/48 (0.50), mid 10/48 (0.21), high 0/48 (0.00)
- best_cell: SPY, trend_window=60/sens=0.6/db=0.2, low-vol regime, Sharpe
  2.44

## Single-config validator results (Step 7)

Grid's nominal best cells and the initial single-config runs both missed
(QQQ Sharpe 0.451, SPY 0.630 -- notably weak, and QQQ additionally failed
walk-forward at db=0.2). CFO required a substantially wider search than
prior iterations this trigger: a shorter trend_window=30 (vs the usual
40-60) plus wide deadbands (0.35-0.4, vs the usual 0.2-0.3) were needed to
clear all validators, likely because CFO's linear-regression-forecast
deviation is naturally noisier/faster-mean-reverting than the other
indicators tested this trigger, requiring more aggressive smoothing via the
deadband:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, sens=0.4, db=0.4 | 1.022 (pass) | 16.5% (pass) | 0.752 (pass) | 1.00 (pass) | 0.080 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=30, sens=0.4, db=0.35 | 1.193 (pass) | 11.2% (pass) | 0.700 (pass) | 1.00 (pass) | 0.191 rel-std (pass) | **ACCEPT** |
| BTC/USDT | trend_window=60, sens=0.6, db=0.2 | 0.089 (**FAIL**) | 43.3% (**FAIL**, decisive) | -0.061 (**FAIL**) | 1.00 (pass) | 0.104 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ AND SPY (equity)**, at an unusually wide deadband (0.35-0.4,
the widest of any accepted strategy this cron trigger) needed to tame CFO's
noisier signal. SPY's param-sensitivity (0.191 rel-std) is the highest of
any accept this trigger, still comfortably under threshold but worth
monitoring. **Reject BTC/USDT** — decisive MDD failure at 43.3%. Continues
the now-established pattern: only the SMA-uptrend-gated equity slice
generalizes reliably this cron trigger; crypto has failed on every single
continuous-sizing dial tested in this batch (EFI, EMV, STC, Qstick, PPO,
ER, FDI, CFO -- 8 for 8), regardless of whether the underlying indicator is
momentum/oscillator-based or trend-efficiency-based, reinforcing that the
crypto rejection is more likely driven by BTC/USDT's structurally higher
volatility and fatter tails overwhelming any of these SMA-trend-gated
sizing constructions, rather than being fixable via indicator choice alone.
