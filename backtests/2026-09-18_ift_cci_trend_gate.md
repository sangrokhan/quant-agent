# Inverse Fisher Transform on CCI (IFT-CCI) + SMA Trend Gate — Rejected (near-miss)

**Date:** 2026-09-18
**Strategy file:** `strategies/2026-09-18_ift_cci_trend_gate.py`
**Sources:**
- [KivancOzbilgic TradingView "Inverse Fisher Transform on CCI"](https://www.tradingview.com/script/HieaInXw/)
  (crediting John Ehlers) — exact formula: `v1=0.1*CCI(close,5)`,
  `v2=WMA(v1,9)`, `IFT=(exp(2*v2)-1)/(exp(2*v2)+1)`, reference lines
  +0.5 (sell) / -0.5 (buy).
- [FMZ "WMA + IFT-CCI Momentum Filtering Multi-Strategy System"](https://www.fmz.com/lang/en/strategy/500242)
  — corroborates same threshold convention, uses IFT-CCI as a
  momentum-confirmation filter (`IFT-CCI > 0.5` for longs) atop a
  WMA(50)/WMA(200) trend cross.

## Hypothesis

Long entry when IFT-CCI crosses above buy_level (-0.5, the "buy zone"
boundary), gated by close>SMA(trend_window) uptrend filter (this repo's
established rescue pattern for raw oscillator crossovers); exit on
IFT-CCI crossing below sell_level (0.5), trend filter break, or
max_hold_days time-stop.

## Grid test (cci_length∈{5,14} × trend_window∈{150,200} × max_hold_days∈{15,20,30}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- 144 cells, 33 passed (**22.9%**)
- by_asset_class: equity 28/72 (38.9%), crypto 5/72 (6.9%)
- by_vol_regime: low 22/48 (45.8%), mid 10/48 (20.8%), high 1/48 (2.1%)
- Best average-Sharpe config across QQQ+SPY: `cci_length=14,
  trend_window=150, max_hold_days=30` (avg Sharpe 0.975)

## Single-config validators (full sample 2019-01-01–2026-09-01, cci_length=14/trend_window=150/max_hold_days=30)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.854 **FAIL** | 24.2% PASS | 0.711 PASS | 0.75 PASS | 0.166 PASS | 70 |
| SPY | 0.977 **FAIL** (near-miss) | 11.7% PASS | 0.769 PASS | 1.0 PASS | 0.164 PASS | 68 |

## Decision: REJECT (both symbols, near-miss on Sharpe)

Both QQQ and SPY fail only on the Sharpe threshold (0.854 and 0.977 vs 1.0),
with every other validator passing comfortably — this is a genuine
near-miss, not a decisive failure. Parameter sensitivity is very stable
(relative std ~16%), so the near-miss isn't an overfitting artifact.
Crypto (BTC/USDT, ETH/USDT) rejected decisively — grid pass fraction only
6.9%. A future iteration could revisit with a finer local parameter search
around cci_length=14/trend_window=150 (e.g. varying wma_length, buy/sell
levels) specifically to try to clear the Sharpe threshold, following this
repo's established near-miss-rescue pattern (cf. Vervoort RSI-IFT
2026-09-11-007→008).
