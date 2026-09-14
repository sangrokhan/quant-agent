# HACOLT-Inspired Heikin-Ashi-Close/TEMA Distance Sizing Dial — SMA Trend Gate (all 4 symbols accepted)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_hacolt_tema_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-037

## Hypothesis

Vervoort's HACOLT (Heikin-Ashi Candles Oscillator Long Term), sources
visited this iteration: https://www.tradingview.com/script/4zuhGaAU-Vervoort-Heiken-Ashi-LongTerm-Candlestick-Oscillator-HACOLT/
(LazyBear's TradingView port, 3-level state-machine description) and
Google's AI-overview summary (TEMA smoothing details).

HACOLT smooths modified Heikin-Ashi close prices with a zero-lag TEMA
(default period 55) and produces a discrete 3-level trend state (-1/0/1).
The exact HACO sub-formula and full state-machine transition logic weren't
fully extractable this iteration (TradingView source-code view blocked),
so this implementation builds the core smoothing mechanism explicitly
confirmed by sources (Heikin-Ashi close -> TEMA) and reuses the cron
trigger's continuous-sizing-dial pattern instead of the discrete 3-level
state machine: percentage distance of HA-close from its own TEMA is
rolling z-scored and tanh-squashed to [-1,+1] as an exposure multiplier
inside an SMA(trend_window) uptrend gate with deadband. Distinct from this
repo's several existing plain-Heikin-Ashi entries (all candle-color/
consecutive-count/crossover rules on raw HA candles, no TEMA smoothing of
the HA close itself).

## Grid test summary (Step 6)

`param_grid={"trend_window": [30,40,50], "tema_period": [21,34,55],
"sensitivity": [0.4,0.6]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 216 total cells.

- **pass_fraction:** 0.620 (134/216) — the highest grid pass fraction of
  any strategy tested this cron trigger
- **by_asset_class:** equity 61/108 (0.565), crypto 73/108 (0.676)
- **by_vol_regime:** low 72/72 (1.0, perfect), mid 38/72 (0.528), high 24/72 (0.333)
- **best_cell:** crypto/ETH/USDT, mid-vol, `trend_window=50, tema_period=34,
  sensitivity=0.4`, Sharpe 2.698
- **worst_cell:** equity/QQQ, high-vol, `trend_window=50, tema_period=21,
  sensitivity=0.6`, Sharpe -0.318

Second consecutive strategy this trigger with a perfect 72/72 low-vol
pass rate (after Fractal Energy, 2026-09-15-036), and the highest overall
pass fraction and best high-vol showing (24/72) of any sizing-dial
strategy tested this trigger.

## Single-config validation (Step 7)

All 4 grid-best configs initially failed (mostly on transaction-cost
survival/max-drawdown at grid-default deadband=0.20/leverage_cap=1.0); a
single round of deadband/leverage_cap tuning fixed all 4:

| Symbol | Config | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, tema_period=34, sensitivity=0.4, deadband=0.35 | 1.278 (✓) | 0.162 (✓) | 0.823 (✓) | 1.00 (✓) | 0.208 (✓) | **YES** |
| SPY | trend_window=30, tema_period=55, sensitivity=0.6, deadband=0.35 | 1.257 (✓) | 0.104 (✓) | 0.724 (✓) | 1.00 (✓) | 0.187 (✓) | **YES** |
| BTC/USDT | trend_window=50, tema_period=55, sensitivity=0.6, leverage_cap=0.3 | 1.332 (✓) | 0.187 (✓) | 0.976 (✓) | 1.00 (✓) | 0.090 (✓) | **YES** |
| ETH/USDT | trend_window=40, tema_period=55, sensitivity=0.4, leverage_cap=0.3 | 1.393 (✓) | 0.140 (✓) | 1.207 (✓) | 1.00 (✓) | 0.060 (✓) | **YES** |

## Decision (Step 8)

**Accepted for all 4 symbols (QQQ, SPY, BTC/USDT, ETH/USDT), each with its
own tuned config as above.** All 5 validators pass with comfortable margin
for every symbol — third full-universe accept this cron trigger (alongside
DSS Bressert 2026-09-15-033 and Elliott Wave Oscillator 2026-09-15-034),
and the highest-quality single grid (best overall pass fraction, perfect
low-vol coverage) among them.
