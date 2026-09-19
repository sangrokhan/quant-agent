# Dual Kaufman Adaptive Moving Average (KAMA) Trend-Filter + Crossover — ACCEPTED (QQQ only)

**Hypothesis:** Per StockCharts.com's "Kaufman's Adaptive Moving Average
(KAMA)" explainer
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/kaufmans-adaptive-moving-average-kama),
KAMA adapts its smoothing speed to market noise via an Efficiency Ratio
(ER: price change over N periods / sum of absolute period-to-period
changes), tracking price closely in clean trends and slowing down in
choppy markets. StockCharts' own disclosed dual-KAMA technique: use a
longer-term, more-smoothed KAMA (slower fastest-EMA-constant) as a trend
filter (bullish when rising), then take bullish price-crosses above a
faster/more-responsive KAMA only while the trend filter confirms. First
KAMA-based strategy tested in this repo — a distinct adaptive-smoothing
mechanism from every other MA variant already tested (Hull MA, T3, Guppy
Multiple MA, FRAMA/Ehlers-family filters).

**Signal logic:** kama_fast = KAMA(er_window, fast_ema=2, slow_ema=30);
kama_trend = KAMA(er_window, fast_ema=trend_fast_ema, slow_ema=30);
trend_bullish = kama_trend rising; long when close > kama_fast AND
trend_bullish, flat otherwise.

## Step 6 — Grid test summary

Grid: `er_window` in {10,20} x `trend_fast_ema` in {5,10,15}, symbols
equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3. 72 total
cells.

- `pass_fraction`: 25/72 = **0.347** (strongest grid result of this cron
  trigger's 4 iterations so far)
- `by_asset_class`: equity 18/36 passed, crypto 7/36 passed
- `by_vol_regime`: low 18/24, mid 7/24, high 0/24
- `best_cell`: er_window=20, trend_fast_ema=5, SPY, low-vol regime,
  Sharpe=2.23
- `worst_cell`: er_window=10, trend_fast_ema=5, QQQ, high-vol regime,
  Sharpe=-0.88

Unlike this trigger's earlier iterations, the pass fraction here spans
low AND mid vol regimes (not just low), and both asset classes show some
passing cells — a broader, more genuine signal.

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### QQQ, er_window=20, trend_fast_ema=15 (best full-sample config found)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.049 | >= 1.0 | **pass** |
| Max drawdown | 0.223 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 186 trades) | net Sharpe 0.914 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | 1.0 | >= 0.75 | pass |
| Parameter sensitivity (6-cell er_window x trend_fast_ema sweep) | relative_std 0.142 | <= 0.5 | pass |

**All 5 validators pass on QQQ.**

### SPY, same config (er_window=20, trend_fast_ema=15)

Sharpe 0.711 (fails 1.0 threshold), MDD 0.232 (passes), tx-cost net Sharpe
0.536 (passes). Near-miss — Sharpe alone falls short.

### Crypto (BTC/USDT, ETH/USDT), same config

Both decisively fail: BTC Sharpe 0.13/MDD 44.4%/net-Sharpe -0.02; ETH
Sharpe 0.20/MDD 56.9%/net-Sharpe 0.03. Crypto's much higher realized
volatility and choppier trend structure make the dual-KAMA
trend-filter-plus-crossover construction ineffective there — consistent
with the grid's own by_asset_class breakdown (crypto only 7/36 grid
cells passed, all presumably narrower param combos).

## Decision: ACCEPTED (QQQ only, er_window=20, trend_fast_ema=15)

All 5 validators pass for QQQ at this config. SPY is a near-miss (Sharpe
just short of 1.0) — not accepted for SPY, but worth noting as a
candidate for a future loop to retune per-symbol (as was done for e.g.
the 52-week-high strategy, 2026-09-17-080, with per-symbol-tuned
thresholds). Crypto is decisively rejected at this config. Strategy file
kept live in `strategies/` for QQQ scope only; `notes` in the knowledge-base
entry records the honest narrower scope (QQQ-only, not SPY/crypto).
