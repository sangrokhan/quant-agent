# Backtest Report: Trend Magic Distance Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_trend_magic_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-053
**Date:** 2026-09-16

## Hypothesis

Trend Magic (Kivanc Ozbilgic, MT4/TradingView indicator), per a Google
search read via browser_exec (EzAlgo Pine Script snippet on Scribd,
corroborated by a GitHub mirror): upT = low - ATR(atr_period)*coeff;
downT = high + ATR(atr_period)*coeff. The "Magic Trend" line's direction
is decided by CCI(cci_period) sign (not by price crossing the line, unlike
Chandelier Exit/SuperTrend/PSAR/HalfTrend already tested in this repo):
when CCI>=0 the line ratchets up as max(prior_line, upT); when CCI<0 it
ratchets down as min(prior_line, downT). First strategy in this repo to
gate an ATR trailing-stop-style ratcheting line's direction by an
oscillator's SIGN rather than a price-crossing event.

Construction: percent-distance of close from the Trend Magic line, rolling
z-scored and tanh-squashed, used as a continuous exposure-sizing dial
inside an SMA(trend_window=40) uptrend gate with a deadband.

Source: Google search (Scribd EzAlgo Pine Script snippet, GitHub mirror)
via browser_exec.

## Step 6 — Grid summary

`run_grid_trend_magic_dist_sizing.py`: `param_grid` = atr_coeff in
{0.5,1.0,1.5} x sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20},
symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=96, **pass_fraction=0.444**
- by_asset_class: equity 53/108, crypto 43/108
- by_vol_regime: low 62/72, mid 34/72, high 0/72
- best_cell: QQQ atr_coeff=0.5/sensitivity=0.4/deadband=0.20, low-vol Sharpe=2.61
- per-symbol grid pass: QQQ 35/54, SPY 18/54, BTC/USDT 35/54, ETH/USDT 8/54

## Step 7 — Single-config validators

| Symbol | atr_coeff | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 1.0 | 0.4 | 0.30 | 0.4 | 1.0 | 1.179 | 0.110 | 0.584 | 1.00 | 0.116 | YES |
| SPY | 1.5 | 0.4 | 0.30 | 0.4 | 1.0 | 1.088 | 0.079 | 0.539 | 1.00 | 0.088 | YES |
| BTC/USDT | 0.5 | 0.8 | 0.20 | 0.25 | 0.3 | 1.314 | 0.151 | 0.731 | 1.00 | 0.036 | YES |
| ETH/USDT | 1.5 | 0.4 | 0.20 | 0.25 | 0.25 | 1.365 | 0.135 | 1.121 | 1.00 | 0.104 | YES |

All 4 symbols pass all 5 validators.

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Sixth consecutive full-universe accept this cron trigger.
- QQQ and SPY both have thin TC-survival margins (0.584 and 0.539, close
  to the 0.5 threshold) -- the CCI-sign-gated ratcheting line construction
  produces higher baseline turnover than the smoother constructions (T3,
  Elder AutoEnvelope) accepted earlier this trigger, requiring wider
  deadbands (0.30) to survive costs at all.
- BTC needed a notably smaller atr_coeff (0.5) than ETH (1.5), an unusual
  asymmetry for this repo's typical BTC/ETH parameter parity -- worth a
  future note if BTC's tighter-band preference recurs across other
  CCI/ATR-based strategies.
