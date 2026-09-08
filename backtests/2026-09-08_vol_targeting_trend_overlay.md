# Backtest Report: Inverse-Volatility Targeting Overlay on SMA200 Trend (QQQ/SPY)

**Strategy file:** `strategies/2026-09-08_vol_targeting_trend_overlay.py`
**Date:** 2026-09-08
**Knowledge base id:** 2026-09-08-165

## Hypothesis

Per https://realbacktesting.com/academy/volatility-targeting-explained.html
(summarizing Moreira & Muir "Volatility-Managed Portfolios" and Harvey et
al.'s volatility-targeting study), scaling notional exposure inversely to
trailing realized volatility (`raw_exposure = target_vol / estimated_vol`,
capped by a leverage ceiling) smooths realized risk through time and tends
to raise risk-adjusted returns most for equity/credit-like risk assets (the
source explicitly flags weaker/inconsistent benefit for
bonds/currencies/commodities — a caveat we test by including crypto in the
grid). This is an OVERLAY on a plain SMA(200) trend gate (close>SMA200 ->
want long), isolating whether the SIZING mechanism itself — not entry
timing — improves risk-adjusted performance vs. the same trend signal traded
at fixed full size. First position-sizing-as-hypothesis strategy in this
repo (every prior strategy uses fixed 0/1 sizing).

## Grid summary (Step 6)

`target_vol` in [0.10, 0.15, 0.20] x `leverage_cap` in [1.0, 1.5] x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.

- **pass_fraction: 0.25** (18/72)
- **by_asset_class:** equity 18/36 (0.50), crypto 0/36 (0.0) — crypto
  decisively rejected, consistent with the source's own caveat that
  volatility targeting doesn't reliably help non-equity assets.
- **by_vol_regime:** low 12/24 (0.50), mid 6/24 (0.25), high 0/24 (0.0) —
  edge concentrated in low/mid-vol regimes; strategy degrades in high-vol
  regimes (expected: inverse-vol sizing lags fast vol spikes, a failure mode
  explicitly flagged by the source article).
- **best_cell:** SPY, target_vol=0.20, leverage_cap=1.5, low-vol, Sharpe 2.85
- **worst_cell:** ETH/USDT, target_vol=0.10, leverage_cap=1.5, mid-vol, Sharpe -0.017

## Single-config validation (Step 7): QQQ, target_vol=0.20, leverage_cap=1.0

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.327 | >= 1.0 |
| Max drawdown | PASS | 0.177 | <= 0.25 |
| Transaction cost survival (10bps/trade, 12 trades) | PASS | net Sharpe 1.312 | >= 0.5 |
| Walk-forward (manual 4-slice fallback*) | PASS | 0.75 (3/4 positive) | >= 0.75 |
| Parameter sensitivity (6 QQQ grid configs) | PASS | rel_std 0.040 | <= 0.5 |

\* `vbt.utils.splitting.RangeSplitter` is broken in this install (documented
since 2026-09-03-002); used the repo's established manual 4-equal-slice
fallback instead.

### SPY, same config (spot-check, not full validator suite)

- Sharpe: 1.016 (borderline pass, >= 1.0)
- Max drawdown: 0.202 (pass, <= 0.25)

## Decision: ACCEPT (QQQ primary, SPY borderline secondary; crypto rejected)

All validators pass decisively for QQQ. SPY passes but narrowly (Sharpe just
above 1.0) — record as secondary/weaker confirmation, not equally trusted.
Crypto (BTC/USDT, ETH/USDT) fails decisively across the entire grid (0/36) —
do not apply this strategy to crypto. High-vol regime cells fail across the
board — this strategy's edge is real but narrow: low/mid realized-vol
regimes on equity indices only.
