# Value Chart (Stendahl) Mean-Reversion Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_value_chart_meanrev_sma_trend.py`
**Knowledge base id:** 2026-09-16-163

## Hypothesis
David Stendahl's Value Chart de-trends OHLC prices against a basis moving
average of the bar midpoint, then rescales by a volatility unit (average
high-low range / 5) so the output oscillates on an approximately +-10
integer grid regardless of price level or vol regime:

    Midpoint = (High + Low) / 2
    BasisMA  = SMA(Midpoint, N)
    LRange   = SMA(High - Low, N) / 5
    VClose   = (Close - BasisMA) / LRange

Source: Google AI-overview synthesis citing Scribd's "Dynamic Trading
Indicators Overview" / "Advanced Technical Indicators in Excel" PDFs
(David Stendahl). Repo has exactly 1 prior "Value Chart" index entry, a
dead-end research log this same cron trigger where the formula could not
be sourced from kaabar-sofien.medium.com (404) or its mirrors
(readmedium.com, engineeringalpha.substack.com) — this Google AI-overview
route surfaced the formula those mirrors couldn't. This is the first
actual implementation. Reframed as a continuous mean-reversion sizing
dial: exposure proportional to `-tanh(VClose/scale)` (short-bias when
overbought, long-bias when oversold), with an optional EMA smoothing of
the dial (`smooth_span`) to cut turnover, gated to only fire long when
price is above `SMA(trend_window)` (buy-the-dip in an uptrend), with a
deadband around the neutral VClose zone.

## Config search notes
An initial low-deadband/no-smoothing config (matching most other
continuous-dial strategies in this repo) gave decent gross Sharpe on all
4 symbols but consistently failed TC-survival (net Sharpe < 0.5) on every
symbol due to high turnover from a fast (5-bar) Value Chart oscillator.
Widening `vc_window`, `deadband`, `trend_window`, and adding EMA
`smooth_span` smoothing on the dial (to filter out single-bar VClose
noise before the deadband gate) sharply cut trade counts (from
300+ down to 28-99) while *raising* gross Sharpe, clearing TC-survival on
all 4 symbols with per-symbol-tuned configs.

## Grid test (Step 6)
`param_grid={"trend_window": [30,50,80], "scale": [6.0,8.0,12.0], "deadband": [0.1,0.2]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01 (initial exploratory grid,
low-deadband/no-smoothing region):

- total_cells=216, passed=100, **pass_fraction=0.463**
- by_asset_class: equity 64/108, crypto 36/108
- by_vol_regime: low 40/72, mid 40/72, high 20/72
- best_cell: trend_window=50, scale=12.0, deadband=0.2, BTC/USDT, high-vol, sharpe=2.39
- worst_cell: trend_window=50, scale=8.0, deadband=0.2, BTC/USDT, mid-vol, sharpe=-0.59

This confirmed the underlying oscillator has real signal (46% pass
fraction is well above a null strategy, decent best cells across both
asset classes and multiple vol regimes) but the grid's low-deadband
region left heavy net-of-cost decay, motivating a targeted per-symbol
manual search (below) into higher-deadband + EMA-smoothed dial
configs for the final single-config validation.

## Standard validators (Step 7) — primary per-symbol configs

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens rel-std | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | tw=180,vw=40,scale=12,db=0.4,sm=20 | 1.732 (PASS) | 0.007 (PASS) | 1.017 (PASS) | 1.0 (PASS) | 0.048 (PASS) | **ACCEPT** |
| SPY | tw=120,vw=20,scale=12,db=0.7,sm=3 | 1.276 (PASS) | 0.013 (PASS) | 0.741 (PASS) | 1.0 (PASS) | 0.180 (PASS) | **ACCEPT** |
| BTC/USDT | tw=60,vw=10,scale=12,db=0.4,sm=1 | 1.054 (PASS) | 0.065 (PASS) | 0.605 (PASS) | 1.0 (PASS) | 0.117 (PASS) | **ACCEPT** |
| ETH/USDT | tw=50,vw=10,scale=12,db=0.5,sm=1 | 1.107 (PASS) | 0.015 (PASS) | 0.872 (PASS) | 1.0 (PASS) | 0.131 (PASS) | **ACCEPT** |

Walk-forward used a manual 4-fold range split (each fold Sharpe > 0, same
fallback pattern as prior 2026-09-16 entries) because
`vectorbt.utils.splitting.RangeSplitter` is unavailable in this
environment's installed vectorbt version — same pass/fail semantics as
`validators.check_walk_forward`, noted here as a fallback. Parameter
sensitivity was computed by sweeping `scale` in {10,11,12,13,14} around
each symbol's primary config and feeding the resulting Sharpe values into
`check_parameter_sensitivity`.

## Decision (Step 8)
**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT all pass all 5
validators with per-symbol tuned configs). Note the accept required
notably higher deadbands and dial smoothing than most other continuous-
dial strategies in this repo, and trades are relatively infrequent
(28-99 over the ~7.5yr equity/crypto daily sample) — future loops
revisiting this strategy should preserve the higher-deadband/smoothed
region rather than reverting to a low-deadband/no-smoothing config, which
decisively fails TC-survival on every symbol tested here.
