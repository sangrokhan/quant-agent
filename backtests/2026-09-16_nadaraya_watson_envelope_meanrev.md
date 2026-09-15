# Backtest Report: Nadaraya-Watson Envelope (LuxAlgo) mean-reversion

**Strategy file:** `strategies/2026-09-16_nadaraya_watson_envelope_meanrev.py`
**Date:** 2026-09-16

## Hypothesis

LuxAlgo's Nadaraya-Watson Envelope (2021): Gaussian-kernel-weighted
regression center line with a mean-absolute-deviation envelope, using the
non-repainting "endpoint" estimator mode (backward-looking only, safe for
backtesting — the default repainting mode recomputes the full-window fit
retroactively and would leak future information). Exact formula per
https://www.tradingview.com/script/Iko0E2kL-Nadaraya-Watson-Envelope-LuxAlgo/:

```
gauss(x,h) = exp(-x^2/(2h^2))
out_t = sum_i(price[t-i]*gauss(i,h)) / sum_i(gauss(i,h))
mae_t = SMA(|price-out|, W)*mult
upper_t = out_t+mae_t, lower_t = out_t-mae_t
```

Long entry: close crosses below the lower envelope (stretched decline);
exit: close crosses back above the center line `out`, or a time-stop.
LuxAlgo's own caveat, quoted verbatim: "nothing suggests this envelope
outperforms traditional band tools." First Nadaraya-Watson-family strategy
in this repo.

## Grid test (Step 6)

Grid: `bandwidth`∈{5,8,12} × `mult`∈{2.0,3.0} × `max_hold_days`∈{10,20},
symbols {QQQ, SPY} × {BTC/USDT, ETH/USDT}, vol_regime_splits=3. 144 cells.

- **pass_fraction: 0.069** (10/144) — one of the weakest grid results this
  cron trigger.
- by_asset_class: equity 9/72 (0.125), crypto 1/72 (0.014)
- by_vol_regime: low 4/48, mid 4/48, high 2/48 — no vol regime shows a
  usable edge.

Per-symbol best average-Sharpe configs all landed well below the 1.0
threshold: QQQ 0.817, SPY 0.876, BTC/USDT 0.336, ETH/USDT 0.547.

## Decision (Step 8)

**Reject: all 4 symbols, without proceeding to full-sample Step 7
validators** — no symbol's best-average-Sharpe grid config clears even the
raw Sharpe threshold on average across vol regimes, and the overall grid
pass_fraction (0.069) is decisively weak. This directly confirms LuxAlgo's
own honest disclaimer that this indicator does not demonstrably outperform
traditional band tools (Bollinger/Keltner/STARC, all already tested with
mixed but generally stronger results in this repo). Not pursued further.
