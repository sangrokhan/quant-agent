# Backtest Report: Ergodic Oscillator Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-14_ergodic_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

William Blau's Ergodic Oscillator (double-smoothed momentum ratio: one-bar
price change passed through a long-length then short-length EMA, divided by
the identical pipeline applied to the absolute change, scaled to +/-100 by
construction) had only ever been tested in this repo as a BINARY
signal-line-crossover entry (2026-09-06-102, REJECTED). This iteration
reframes it as a CONTINUOUS SIZING dial within an SMA(trend_window) uptrend
gate, following this cron trigger's now-repeatedly-validated pattern
(Coppock/AO/BW-MFI/TSI/SMI/DSS all flipped from binary reject to accepted
QQQ(+SPY)-only continuous-sizing dials).

Source: https://www.luxalgo.com/library/indicator/ergodic-oscillator/
(same source as the prior binary 2026-09-06-102 entry; only the *use* of
the indicator changed, not the formula).

## Grid Test Summary (Step 6)

`param_grid={"long_len": [20, 32], "base_exposure": [0.4, 0.6, 0.8],
"sensitivity": [0.5, 0.7, 0.9]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`.

- total_cells: 216, passed_cells: 97, **pass_fraction: 0.449**
- by_asset_class: equity 61/108 (0.565), crypto 36/108 (0.333)
- by_vol_regime: low 59/72 (0.819), mid 38/72 (0.528), high 0/72 (0.0)
- best_cell: long_len=32, base_exposure=0.8, sensitivity=0.5, ETH/USDT mid-vol, sharpe=2.40
- worst_cell: long_len=32, base_exposure=0.4, sensitivity=0.9, QQQ high-vol, sharpe=-0.37

The grid confirms the pattern seen across this cron trigger's other
sizing-dial variants: it works broadly in low/mid vol, breaks down
completely in high-vol regimes (0/72), and equity outperforms crypto.

## Primary Config Validation (Step 7)

Best full-sample single config: `long_len=20, base_exposure=0.8, sensitivity=0.9`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.083 (pass) | 0.190 (pass) | 0.772 (pass) | 1.00 (pass) | 0.048 rel-std (pass) |
| SPY | 1.063 (pass) | 0.114 (pass) | 0.695 (pass) | 1.00 (pass) | 0.047 rel-std (pass) |
| BTC/USDT | 1.303 (pass) | 0.637 (**fail**, cap 0.25) | 1.212 (pass) | 1.00 (pass) | 0.021 rel-std (pass) |
| ETH/USDT | 1.164 (pass) | 0.526 (**fail**, cap 0.25) | 1.103 (pass) | 1.00 (pass) | 0.025 rel-std (pass) |

All 5 validators pass for both QQQ and SPY. Crypto (BTC/ETH) decisively
fails only on max-drawdown (leverage-cap-aware sizing still allows
unbounded crypto vol to blow through the 25% MDD threshold) despite
passing every other validator — consistent with essentially every other
sizing-dial strategy tested this trigger.

## Decision

**ACCEPT for equity (QQQ + SPY). REJECT for crypto (BTC/ETH, MDD decisive fail).**
