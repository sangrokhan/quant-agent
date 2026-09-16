# 2026-09-17 Ichimoku Kumo-Distance Continuous Sizing Dial + SMA Trend Gate

## Hypothesis

This repo has 6 prior Ichimoku entries (TK-cross+cloud-confirmation binary
2026-09-04-034 near-miss rejected; Kumo breakout binary 2026-09-05-049;
3-condition confluence 2026-09-05-085; Chikou-Span-distance continuous
sizing dial 2026-09-14-163 accepted QQQ only), but none use the price-to-
Kumo DISTANCE itself (as opposed to a binary above/below state or the
Chikou lagging line) as a continuous signal. Per common Ichimoku trading
literature, the vertical gap between price and the nearer Kumo boundary
carries trend-conviction information beyond its sign. This iteration
reframes price-to-Kumo distance as a CONTINUOUS SIZING dial (rolling
z-score + tanh) within an SMA(trend_window) uptrend gate, following this
repo's binary-to-continuous-sizing-dial rescue pattern.

Source: quantifiedstrategies.com / agentictraders.io / j2t.com Ichimoku
Cloud explainers (standard Tenkan/Kijun/Senkou Span A/B construction,
already partially cited in this repo's prior Ichimoku entries).

## Strategy file

`strategies/2026-09-17_kumo_distance_sizing_sma_trend.py`

## Grid test summary (216 cells: sensitivity x zscore_window x deadband x 4 symbols x 3 vol regimes)

- pass_fraction: 0.315 (68/216)
- by_asset_class: equity 46/108 passed; crypto 22/108 passed
- by_vol_regime: low 57/72; mid 10/72; high 1/72
- best_cell: QQQ, sensitivity=0.6/zscore_window=90/deadband=0.2, low-vol regime, Sharpe 2.82

## Single-config validation (full sample, 2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | deadband=0.2, sensitivity=0.8, zscore_window=90 | 1.182 (pass) | 0.195 (pass) | 0.984 (pass) | 0.75 (pass) | 0.039 (pass) | **ACCEPT** |
| SPY | deadband=0.2, sensitivity=0.4, zscore_window=60 | 1.014 (pass) | 0.109 (pass) | 0.679 (pass) | 0.75 (pass) | 0.035 (pass) | **ACCEPT** |
| BTC/USDT | deadband=0.2, sensitivity=0.8, zscore_window=60, leverage_cap=0.3 | 0.169 (fail) | 0.209 (pass) | -0.051 (fail) | 1.0 (pass) | 0.012 (pass) | **REJECT** |

## Outcome

**Accepted for equity (QQQ, SPY)** -- all 5 validators pass for both.
**Rejected for crypto** -- BTC/USDT fails decisively on Sharpe and
transaction-cost survival even at low leverage_cap, consistent with this
repo's recurring pattern that trend-conviction-magnitude continuous dials
generalize well within equity but rarely to crypto.
