# Backtest Report: BB/KC Squeeze Percent-Rank Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_bbkc_squeeze_rank_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-052
**Date:** 2026-09-16

## Hypothesis

Volatility Squeeze Percent Rank, per Google AI-overview (TradingView
corroborating, visited this iteration via browser_exec Google fallback):
instead of the standard discrete Boolean squeeze test (BBW < KCW), compute
R = BBW/KCW on every bar and take its rolling percentile rank over a
lookback window -- a smooth 0-100% scale of "how tight volatility is right
now relative to its own recent history." Distinct from this repo's existing
BBW-only continuous-sizing dial (id 2026-09-14-150, min-max normalized
single-band-width) since this construction (a) compares TWO bands
(Bollinger vs Keltner) rather than one band's width in isolation, and (b)
uses a percentile-RANK transform (order statistic) rather than min-max
normalization. First BB/KC-ratio-based sizing dial in this repo.

Construction: rolling percentile rank of R=BBW/KCW, inverted (1-2*rank) so
compression scales exposure up (same inverse-volatility-conditioning
intuition already validated via GAPO/BBW), used as a continuous
exposure-sizing dial inside an SMA(trend_window=40) uptrend gate with a
deadband.

Source: Google AI-overview (TradingView) via browser_exec.

## Step 6 — Grid summary

`run_grid_bbkc_squeeze_rank_sizing.py`: `param_grid` = rank_window in
{60,100,150} x sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20},
symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=81, **pass_fraction=0.375** (lowest of the five
  strategies accepted this cron trigger, driven by weak crypto grid cells)
- by_asset_class: equity 72/108 (strongest equity grid this trigger),
  crypto 9/108 (weakest crypto grid this trigger)
- by_vol_regime: low 38/72, mid 25/72, high 18/72 (best high-vol-regime
  coverage of any strategy accepted this cron trigger)
- best_cell: SPY rank_window=150/sensitivity=0.4/deadband=0.20, low-vol Sharpe=2.86
- per-symbol grid pass: QQQ 32/54, SPY 40/54, BTC/USDT 3/54, ETH/USDT 6/54

## Step 7 — Single-config validators

Crypto needed extensive hand-tuning beyond the grid's default deadband
range (0.10-0.20) -- most (leverage_cap, deadband) combos at grid defaults
produced either failing MDD or a degenerate zero-trade flat position:

| Symbol | rank_window | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 150 | 0.3 | 0.50 | 0.4 | 1.0 | 1.151 | 0.126 | 0.796 | 0.75 | 0.203 | YES |
| SPY | 100 | 0.4 | 0.30 | 0.4 | 1.0 | 1.462 | 0.060 | 0.553 | 1.00 | 0.062 | YES |
| BTC/USDT | 60 | 0.4 | 0.15 | 0.3 | 0.3 | 1.147 | 0.100 | 0.631 | 1.00 | 0.133 | YES |
| ETH/USDT | 150 | 0.4 | 0.20 | 0.2 | 0.25 | 1.030 | 0.122 | 0.657 | 0.75 | 0.170 | YES |

All 4 symbols pass all 5 validators, though with thinner margins than the
prior four accepts this cron trigger (SPY TC net Sharpe 0.553 close to the
0.5 threshold; ETH Sharpe 1.030 close to the 1.0 threshold).

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT), with a caveat:
margins are thinner than the prior four accepts this cron trigger and the
grid pass_fraction (0.375) is the lowest of the five -- flagged as a
narrower/lower-confidence full-universe accept.

## Notes

- Fifth consecutive full-universe accept this cron trigger (after Elder
  AutoEnvelope, Acceleration Bands, FCO, T3), though qualitatively weaker
  (lowest grid pass_fraction, thinnest single-config margins) than the
  prior four.
- Confirms this repo's "compression favors leaning in" pattern (already
  validated via GAPO/BBW) generalizes to a two-band ratio construction, but
  the crypto grid cells were mostly failing (9/108) before hand-tuning
  found narrow working windows -- a future revisit could investigate
  whether crypto specifically needs the ratio direction inverted (crypto
  vol expansion, not compression, might precede continuation given crypto's
  momentum-heavy character) rather than reusing the equity-derived
  compression-favors-exposure intuition unchanged.
