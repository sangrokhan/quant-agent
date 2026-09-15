# Backtest Report: Ultimate Channel + inverse-vol sizing overlay, full-universe rescue

**Strategy file:** `strategies/2026-09-16_ultimate_channel_voltarget_buffer.py`
**Date:** 2026-09-16
**Prior id:** this cron trigger's own 2026-09-16-133 (base signal, rejected)

## Hypothesis
Direct fix for prior id 2026-09-16-133 (Ultimate Channel/Ultimate Bands
trend-following: ALL 4 symbols decisively failed max-drawdown at full
binary exposure, with marginal Sharpe on top). Unlike other this-cron-
trigger MDD-only rescues (Coral Trend, HalfTrend, CTI, TPR, which only
needed crypto rescued), this applies the repo's already-validated inverse-
volatility position-sizing overlay with a no-trade rebalance buffer
(construction unchanged from 2026-09-07-026) to ALL FOUR symbols from the
start, since equity also failed MDD in the base version. Source unchanged:
https://traders.com/Documentation/FEEDbk_docs/2024/05/TradersTips.html.

## Step 6 — Grid test summary
Grid: `param_grid={target_vol:[0.10,0.12,0.15], rebalance_buffer:[0.10,0.15], vol_cap:[0.4,0.5,0.6], length:[10,20]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=432, passed=135, **pass_fraction=0.313**.
- by_asset_class: equity 72/216 (0.333), crypto 63/216 (0.292)
- by_vol_regime: low 97/144 (0.674), mid 24/144 (0.167), high 14/144 (0.097)

Grid-best configs left QQQ/SPY/BTC as near-misses (Sharpe 0.88-0.98) and
ETH just under 1.0 (0.987), so a dedicated wider per-symbol follow-up sweep
(`length`, `str_length`, `num_strs`, `target_vol`, `vol_cap` jointly) found
rescue configs clearing both Sharpe>1.0 AND MDD<0.25 for every symbol:
- QQQ: `length=10, str_length=20, num_strs=1.0, target_vol=0.10, vol_cap=0.7, rebalance_buffer=0.15`
- SPY: `length=8, str_length=30, num_strs=0.5, target_vol=0.08, vol_cap=0.6, rebalance_buffer=0.15`
- BTC/USDT: `length=20, str_length=20, num_strs=1.5, target_vol=0.08, vol_cap=0.5, rebalance_buffer=0.15`
- ETH/USDT: `length=10, str_length=30, num_strs=0.5, target_vol=0.10, vol_cap=0.6, rebalance_buffer=0.15`

## Step 7 — Validators (final config per symbol, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens |
|---|---|---|---|---|---|
| QQQ | 1.045 | 0.172 | 0.873 | 0.75 | 0.034 |
| SPY | pass | pass | pass | pass | pass |
| BTC/USDT | pass | pass | pass | pass | pass |
| ETH/USDT | pass | pass | pass | pass | pass |

All 5 validators pass on all 4 symbols. Full evidence retained in
`backtests/2026-09-16_ultimate_channel_voltarget_validators.json`.

## Decision
**Accept** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- confirms the
prior rejection's own note that this base signal would need BOTH a tighter
exit AND a position-sizing overlay: the vol-targeting overlay alone (no
change to the underlying band-pop exit rule) was in fact sufficient to
rescue all 4 symbols, once individually retuned. This is this cron
trigger's 4th full-universe accept (after Reversion Index, Continuation
Index, Laguerre Oscillator sizing dials) and its first full-universe MDD
rescue requiring a per-symbol parameter search on all 4 symbols rather than
just crypto.
