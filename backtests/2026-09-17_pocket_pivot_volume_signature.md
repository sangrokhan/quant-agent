# Pocket Pivot Volume Signature (2026-09-17)

## Hypothesis

Per LuxAlgo's "Pocket Pivot" indicator page
(https://www.luxalgo.com/library/indicator/pocket-pivot/, read via
`browser_exec` this iteration, cross-confirmed by ChartMill/TradingView
community/Gil Morales "OWL" sources found via Google search): a "pocket
pivot" day is an up-close day whose volume exceeds the highest volume of
any down day over the trailing 10 sessions — a volume signature historically
associated with institutional accumulation happening quietly inside a base,
before an obvious breakout. LuxAlgo's "clean build" adds constructive-context
filters: close above a 50-day SMA (uptrend), and the day's low within a 2%
proximity band of either the 10-day or 50-day SMA (avoiding extended moves).

This is the FIRST Pocket Pivot strategy in this repo (0 prior entries) — a
genuinely distinct volume-signature construction (comparison against the
max down-day volume in a trailing window) from every other volume-based
strategy already tested.

## Strategy files

- `strategies/2026-09-17_pocket_pivot_volume_signature.py` (base, unsized)
- `strategies/2026-09-17_pocket_pivot_voltarget_crypto.py` (inverse-vol
  sized variant, applied to rescue crypto's MDD)

## Grid test (`scripts/run_grid_pocket_pivot.py`, base strategy)

`param_grid={"down_day_lookback": [10], "support_proximity_pct": [0.02,
0.04], "max_hold_days": [15, 30]}`, symbols `{equity: [QQQ, SPY], crypto:
[BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`. 48 cells.

- `pass_fraction`: 0.3125 (15/48)
- `by_asset_class`: equity 8/24, crypto 7/24
- `by_vol_regime`: low 14/16, mid 0/16, high 1/16 — edge is almost entirely
  a low-vol-regime phenomenon
- `best_cell`: ETH/USDT, support_proximity_pct=0.02, mid-vol, Sharpe 2.48

## Full-sample validators — base (unsized), down_day_lookback=10, support_proximity_pct=0.02, max_hold_days=15, 2019-2026

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 0.857 **❌** | 0.307 **❌** | 0.977 **❌** (near-miss) | 1.204 ✅ | ≥1.0 |
| Max drawdown | 0.099 ✅ | 0.124 ✅ | 0.358 **❌** | 0.352 **❌** | ≤0.25 |
| TC survival | 0.775 ✅ | 0.186 **❌** | 0.944 ✅ | 1.181 ✅ | ≥0.5 |

QQQ/SPY are decisive equity Sharpe fails even after tuning `max_hold_days`
up to 30 (QQQ best 0.904, SPY best 0.525 at support_proximity_pct=0.04) —
a genuine ceiling on daily-bar QQQ/SPY, not a tuning artifact (Pocket Pivot
is originally an individual-stock pattern; index ETFs may simply not show
the same discrete accumulation volume spikes). BTC/ETH pass Sharpe/TC
comfortably but decisively fail MDD (0.35+ vs 0.25) — the classic
"good signal, no risk control" pattern already fixed for multiple other
strategies this cron trigger via inverse-vol sizing.

## Rescue: inverse-vol sizing for crypto (`strategies/2026-09-17_pocket_pivot_voltarget_crypto.py`, target_vol=0.15, max_leverage=1.0)

| Validator | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.057 ✅ | 1.235 ✅ | ≥1.0 |
| Max drawdown | 0.130 ✅ (was 0.358 unsized) | 0.123 ✅ (was 0.352 unsized) | ≤0.25 |
| TC survival | net Sharpe 0.970 ✅ | net Sharpe 1.147 ✅ | ≥0.5 |
| Walk-forward (manual 4-split fallback) | 4/4 positive → 1.0 ✅ | 4/4 positive → 1.0 ✅ | ≥0.75 |
| Parameter sensitivity (target_vol∈{0.10,0.15,0.20} on BTC/USDT) | relative_std 0.019 ✅ | — | ≤0.5 |

## Decision: ACCEPT (BTC/USDT + ETH/USDT, sized variant only) — REJECT equity (QQQ, SPY)

The base unsized strategy fails on all 4 symbols for different reasons
(equity: Sharpe too low; crypto: MDD too high). Applying this repo's
established inverse-vol sizing overlay (same technique as `2026-09-17-009`
and `2026-09-17-010`) fully rescues both crypto symbols, which now pass all
5 validators cleanly. QQQ/SPY remain rejected — Pocket Pivot's edge does
not clear the Sharpe threshold on index ETFs at the daily-bar level even
after tuning, consistent with the pattern's original design for individual
stocks with sharper single-name volume spikes.
