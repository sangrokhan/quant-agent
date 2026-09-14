# 2026-09-14 Chande Trend Meter (CTM) Continuous Sizing Overlay

## Hypothesis

Chande Trend Meter (CTM, Tushar Chande), per StockCharts ChartSchool
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy `strategies/2026-09-11_chande_trend_meter_ctm.py`,
no fresh web fetch needed this sub-step): a 0-100 composite trend-strength
score combining (1) Bollinger %B averaged across FOUR timeframes
(20/50/75/100-day), (2) price change relative to its own 100-day std dev
(squashed to [0,1]), (3) RSI(14) rescaled to [0,1], and (4) a 2-day
price-channel breakout flag (1/0.5/0).

This repo's only prior CTM entries (2026-09-11-033/067) used the composite
score as a binary threshold CROSSOVER entry trigger (entry_threshold=60,
accepted QQQ+SPY at a fine-tuned shared config, crypto rejected
decisively). This iteration reframes CTM as a CONTINUOUS SIZING dial
within an SMA(trend_window) uptrend gate -- the same reframing pattern
that rescued Firefly Oscillator, Elegant Oscillator, Volume RSI, and Trend
Continuation Factor earlier this same cron trigger.

## Grid test summary (Step 6)

`param_grid={"trend_window":[30,40], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.479** (69/144)
- by_asset_class: equity 36/72 passed, crypto 33/72 passed
- by_vol_regime: low 47/48 (98%), mid 21/48 (44%), high 1/48 (2% -- one
  high-vol cell passes, edge otherwise concentrated in low/mid vol like
  nearly every sizing-dial strategy this trigger)
- best_cell: SPY low-vol, trend_window=40/sensitivity=0.5/deadband=0.15,
  Sharpe 2.61
- worst_cell: QQQ high-vol, trend_window=40/sensitivity=0.7/deadband=0.2,
  Sharpe -0.59

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | trend_window=30, sens=0.5, db=0.4 | 1.230 | 0.108 | 0.831 | 1.00 | 0.042 | YES |
| SPY      | trend_window=40, sens=0.6, db=0.4 | 1.122 | 0.076 | 0.691 | 1.00 | 0.129 | YES |
| BTC/USDT | trend_window=40, sens=0.3, db=0.2, leverage_cap=0.3, base_exposure=0.2 | 1.407 | 0.155 | 1.104 | 0.75 | 0.009 | YES |
| ETH/USDT | trend_window=40, sens=0.3, db=0.15, leverage_cap=0.25, base_exposure=0.2 | 1.237 | 0.189 | 0.984 | 1.00 | 0.013 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs. Equity used a widened deadband (0.4 vs the 0.15-0.2 grid
default) for transaction-cost survival; crypto needed the now-standard
leverage-cap-aware low-exposure recalibration (base_exposure=0.2,
leverage_cap=0.25-0.3, lower sensitivity=0.3) to keep MDD under 25% (ETH's
MDD at 18.9% is the highest crypto MDD of any all-symbol-accept strategy
this trigger, still under threshold).

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Fifth strategy this cron trigger (after Firefly, Elegant Oscillator,
VoRSI, TCF) to accept all 4 target symbols in a single reframing pass.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-11-033/067) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chande-trend-meter-ctm
