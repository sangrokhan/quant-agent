# Backtest Report: Coral Trend Indicator (LazyBear) trend-color-flip

**Strategy file:** `strategies/2026-09-16_coral_trend_color_flip.py`
**Date:** 2026-09-16

## Hypothesis

Coral Trend Indicator (LazyBear): cascade of six one-pole EMA smoothing
stages (i1..i6, each fed from the prior stage), recombined via cubic-
polynomial coefficients derived from a lag-compensation constant D
(default 0.4), yielding a single low-lag trend line ("Cto"). Exact formula
per https://www.tradingview.com/script/AzQo1gRi-Coral-Trend-Indicator-LazyBear/:

```
di=(sm-1)/2+1; c1=2/(di+1); c2=1-c1
c3=3*(D^2+D^3); c4=-3*(2D^2+D+D^3); c5=3D+1+D^3+3D^2
i1=c1*src+c2*i1[1] ... i6=c1*i5+c2*i6[1] (cascaded)
Cto = -D^3*i6 + c3*i5 + c4*i4 + c5*i3
```

Per the source's own disclosed rule: buy on the trend-color flip from
falling to rising (shift_up); exit on the mirror flip. First Coral Trend
strategy in this repo — distinct from T3/TEMA/Rainbow MA/GMMA (other
cascaded-smoothing trend lines already tested) via its unique cubic-
polynomial recombination of 6 EMA stages.

## Grid test (Step 6)

Grid: `sm`∈{14,21,34} × `cd`∈{0.3,0.4,0.5} × `max_hold_days`∈{40,80},
symbols {QQQ, SPY} × {BTC/USDT, ETH/USDT}, vol_regime_splits=3. 216 cells.

- **pass_fraction: 0.375** (81/216)
- by_asset_class: equity 62/108 (0.574), crypto 19/108 (0.176)
- by_vol_regime: low 54/72 (0.75), mid 17/72 (0.236), high 10/72 (0.139)
- best_cell: QQQ, sm=34/cd=0.4/max_hold=80, low-vol, Sharpe 3.19

Per-symbol best average-Sharpe configs: QQQ sm=34/cd=0.5/hold=80 (avg
1.62); SPY sm=34/cd=0.4/hold=80 (avg 1.57); BTC/USDT sm=14/cd=0.3/hold=80
(avg 1.34); ETH/USDT sm=34/cd=0.5/hold=40 (avg 1.37).

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.494 (pass) | 0.185 (pass) | 1.456 (pass) | 0.75 (pass) | 0.108 (pass) | **Yes** |
| SPY | 1.451 (pass) | 0.150 (pass) | 1.409 (pass) | 1.00 (pass) | 0.117 (pass) | **Yes** |
| BTC/USDT | 1.187 (pass) | 0.583 (**FAIL**, decisive) | 1.158 (pass) | 1.00 (pass) | 0.134 (pass) | **No** |
| ETH/USDT | 1.374 (pass) | 0.485 (**FAIL**, decisive) | 1.362 (pass) | 1.00 (pass) | 0.041 (pass) | **No** |

## Decision (Step 8)

**Accept: QQQ and SPY** (both all 5 validators pass with strong margins,
first-try grid configs, no fine-tune needed).
**Reject: BTC/USDT and ETH/USDT** (Sharpe passes comfortably on both, MDD
decisively fails on both — 0.583 and 0.485, roughly 2x the threshold). The
same repo-wide pattern as HalfTrend/CTI/TPR this cron trigger: a strong
directional trend-following signal that needs an explicit vol-targeting
overlay to control crypto drawdown. Plausible rescue candidate for a
future iteration.
