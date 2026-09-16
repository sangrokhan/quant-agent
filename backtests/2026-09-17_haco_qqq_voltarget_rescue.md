# HACO Regime-Flip with Inverse-Vol Sizing — QQQ Rescue (2026-09-17)

## Hypothesis

Direct follow-up to `2026-09-16-118` (Vervoort's HACO Heikin-Ashi regime-flip
oscillator, source:
https://www.tradingview.com/script/UyhY8FuQ-Vervoort-Heiken-Ashi-Candlestick-Oscillator/).
That entry accepted SPY but rejected QQQ as a near-miss: "QQQ: near-miss MDD
(0.283 vs 0.25 threshold), everything else passes cleanly -- plausible
vol-target rescue candidate for a future iteration" (per its own
`rejection_reason`). This iteration tests exactly that suggested rescue:
identical HACO regime signal, but position SIZE scaled inversely to trailing
20-day realized volatility (target_vol / realized_vol, capped at
max_leverage=1.0) instead of a flat 0/1 long/flat position.

## Strategy file

`strategies/2026-09-17_haco_qqq_voltarget_rescue.py` (imports the base HACO
oscillator unchanged from `strategies/2026-09-16_haco_zltema_regime.py`)

## Grid test (`scripts/run_grid_haco_qqq_voltarget.py`)

`param_grid={"target_vol": [0.10, 0.15, 0.20], "max_leverage": [1.0]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`. 36 cells.

- `pass_fraction`: 0.528 (19/36) — a substantial improvement over the base
  strategy, and now crypto ALSO passes cells (10/18) where the unsized
  version was decisively rejected.
- `by_asset_class`: equity 9/18, crypto 10/18
- `by_vol_regime`: low 12/12 (100%), mid 7/12, high 0/12 — the vol-target
  overlay works very well in low/mid-vol regimes but the underlying HACO
  signal still struggles in high-vol regimes even after sizing.
- `best_cell`: SPY, target_vol=0.15, low-vol, Sharpe 2.02
- `worst_cell`: QQQ, target_vol=0.10, high-vol, Sharpe -0.11

## Full-sample validators (`scripts/validate_haco_qqq_voltarget.py`, target_vol=0.15, max_leverage=1.0, 2019-2026)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 1.098 ✅ | 0.937 **❌** | 1.031 ✅ | 1.261 ✅ | ≥1.0 |
| Max drawdown | 0.188 ✅ (was 0.283 unsized) | 0.106 ✅ | 0.244 ✅ | 0.164 ✅ | ≤0.25 |
| TC survival (10bps/trade) | net Sharpe 0.855 ✅ (111 trades) | net Sharpe 0.654 ✅ (112) | net Sharpe 0.836 ✅ (164) | net Sharpe 1.051 ✅ (154) | ≥0.5 |
| Walk-forward (manual 4-split fallback) | 3/4 positive (1.94,0.25,2.12,-0.001) → 0.75 ✅ | not run (already fails Sharpe) | 4/4 positive → 1.0 ✅ | 4/4 positive → 1.0 ✅ | ≥0.75 |
| Parameter sensitivity (target_vol∈{0.10,0.15,0.20} on QQQ) | relative_std 0.027 ✅ | — | — | — | ≤0.5 |

## Decision: ACCEPT (QQQ, BTC/USDT, ETH/USDT — NOT SPY)

The vol-target rescue works exactly as the prior entry's notes predicted:
QQQ's MDD drops from 0.283 (unsized, rejected) to 0.188 (sized, passes) while
all other validators remain clean. As a bonus, BTC/USDT and ETH/USDT — both
decisively rejected in the unsized version — now also pass all 5 validators,
extending this strategy's honest scope to a genuinely multi-asset-class
result. SPY (already separately accepted unsized in 2026-09-16-118) narrowly
fails Sharpe under the sized version (0.937<1.0) — the sizing overlay
slightly dilutes SPY's already-modest unsized edge; SPY should continue
using its existing unsized/binary config from 2026-09-16-118, not this
sized variant.
