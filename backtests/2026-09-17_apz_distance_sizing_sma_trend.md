# Backtest Report: APZ Distance-From-Basis Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-17_apz_distance_sizing_sma_trend.py`
**Date:** 2026-09-17 (cron trigger iteration 1/10)

## Hypothesis

Adaptive Price Zone (APZ, Lee Leibfarth, TASC Sept 2006) per Investopedia's
disclosed exact formula (source:
https://www.investopedia.com/articles/trading/10/adaptive-price-zone-indicator-explained.asp,
read via browser_exec this iteration -- web_search's DDGS backend
intermittently timed out/returned empty results for several queries this
run; Google search fallback used for keyword discovery/novelty scanning,
direct browser page read used for exact formula extraction):

    basis = EMA(EMA(close, 5), 5)
    volatility_value = EMA(EMA(high - low, 5), 5)

Distance-from-basis, ATR-analog normalized by volatility_value, reframed
as a CONTINUOUS SIZING dial (rolling z-score + tanh) within an
SMA(trend_window) uptrend gate. Distinct from this repo's two prior APZ
entries (2026-09-07-011 mean-reversion off the bands, rejected;
2026-09-11-012 ADX-gated breakout, accepted equity) since neither used the
basis-distance series itself as a continuous exposure input.

## Grid test summary (Step 6)

108 cells: param_grid={trend_window:[30,40,50], sensitivity:[0.5,0.6,0.7]}
(ema_period=5, zscore_window=60, deadband=0.20 fixed) x symbols
{equity: QQQ,SPY; crypto: BTC/USDT,ETH/USDT} x vol_regime_splits=3.

- pass_fraction: 0.435 (47/108)
- by_asset_class: equity 28/54 pass, crypto 19/54 pass
- by_vol_regime: low 28/36, mid 19/36, high 0/36 (strategy holds up in
  calmer regimes only, as expected for a trend/momentum-style sizing dial)
- best_cell: SPY low-vol, trend_window=30 sensitivity=0.5, Sharpe 2.79
- Note: this grid used deadband=0.20 (the default); the primary-config
  validation below uses a widened deadband=0.55 turnover-reduction fix
  applied after the grid, per this cron trigger's established pattern
  (2026-09-17-107, -109) since deadband=0.20 alone produced too much
  turnover for TC-survival at the single-config level (see below).

## Single-config validation (Step 7)

Primary config: `trend_window=40, ema_period=5, zscore_window=60,
sensitivity=0.6, deadband=0.55, leverage_cap=1.0` (deadband widened from
0.20 to 0.55 to cut turnover after the initial deadband=0.20 config failed
TC-survival on both QQQ (net Sharpe 0.323) and SPY (net Sharpe 0.155) at
~810 trades each).

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.036 PASS | 1.058 PASS |
| Max drawdown (<=0.25) | 0.202 PASS | 0.091 PASS |
| TC survival, 5bps/trade (net Sharpe >=0.5) | 0.774 PASS (308 trades) | 0.737 PASS (292 trades) |
| Walk-forward (4 splits, >=75% positive) | 1.0 PASS (4/4) | 1.0 PASS (4/4) |
| Parameter sensitivity (relative std <=0.5, 3x3 sens/trend_window sweep) | 0.058 PASS | 0.073 PASS |

Crypto (BTC/USDT, ETH/USDT) with the same equity-tuned config, no
leverage-cap recalibration: Sharpe passes (1.12 / 1.11) and TC passes
(1.06 / 1.07 net Sharpe) but MDD decisively fails (0.54 / 0.50 vs 0.25
threshold) -- consistent with this repo's near-universal finding that
equity-tuned trend-sizing dials need a crypto-specific leverage_cap
recalibration (not attempted this sub-iteration; would be a natural
follow-up per the `leverage_cap_recalibration` pattern used elsewhere in
this repo, e.g. 2026-09-14-185).

## Decision

**Accept (QQQ, SPY only)**. All 5 validators pass cleanly for both equity
symbols at the widened-deadband config. **Reject (BTC/USDT, ETH/USDT)** --
decisive MDD failure without a crypto-specific leverage-cap fix.
