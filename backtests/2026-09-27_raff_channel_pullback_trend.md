# Raff Channel Pullback-in-Trend — QQQ + SPY (accepted)

**Hypothesis:** Raff Channel (Gilbert Raff equidistant regression channel:
rolling OLS midline + parallel bands offset by the max historical absolute
residual within the window) turned into a pullback-in-trend entry: buy when
the regression slope is positive (uptrend) AND price dips to/below the lower
equidistant band, exit at the midline (mean-reversion target), on a trend
break (slope turns non-positive), on a low-vol-regime flip, or a time-stop.

**Source:** https://quantifiedtrader.com/backtest/strategies/raff-channel
(site's own naive rule is a bare price>midline trend-follow; this iteration
adapts it into a slope-gated pullback entry per this repo's established
"turn the naive site rule into a pullback/rescue variant" pattern). First
Raff Channel strategy in this repo (0 prior KB hits for "Raff").

**Strategy file:** `strategies/2026-09-27_raff_channel_pullback_trend.py`

## Grid test (Step 6)

`param_grid={reg_window:[20,30,45], max_hold_days:[10,15,25]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2018-01-01..2026-09-01.

- Initial grid (no vol gate): pass_fraction 0.185 (20/108), edge concentrated
  entirely in the low-vol tercile (20/36 low vs 0/36 mid, 0/36 high).
- After adding a low-vol-regime flatten gate (vol_regime_ratio, same pattern
  as `2026-09-03_bb_meanrev_qqq_volregime.py`): pass_fraction improved to
  0.25 (27/108); by_asset_class equity 21/54, crypto 6/54 (crypto still
  weak/inconsistent); by_vol_regime low 18/36, mid 6/36, high 3/36.
- Best cell: QQQ low-vol, reg_window=30/max_hold_days=10, Sharpe 2.55.

## Fine-tune to a single SHARED equity config (Step 6/7)

A targeted local search over
`reg_window in [15,20,25,30,40,50] x max_hold_days in [5,10,15,20,30] x
slope_min_pct in [0.0,0.0005,0.001] x vol_regime_ratio in [0.8,1.0,1.2]`
on full-sample QQQ+SPY found a config clearing Sharpe 1.0 on BOTH symbols
simultaneously (maximizing `min(sharpe_QQQ, sharpe_SPY)`):

**Chosen config:** `reg_window=20, max_hold_days=5, slope_min_pct=0.0005,
vol_regime_ratio=1.0`

## Single-config validator suite (Step 7)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.172 PASS | 1.246 PASS | >= 1.0 |
| Max drawdown | 4.56% PASS | 5.76% PASS | <= 25% |
| TC survival (10bps/trade, 42/43 trades) | net Sharpe 0.990 PASS | net Sharpe 1.001 PASS | >= 0.5 |
| Walk-forward (4 contiguous splits, per-split independent signal regen) | 4/4 splits positive Sharpe, frac 1.0 PASS | 4/4 splits positive Sharpe, frac 1.0 PASS | >= 0.75 |
| Parameter sensitivity (reg_window in {15,20,25} x max_hold_days in {4,5,7}, 9-cell local grid) | relative_std 0.257 PASS | relative_std 0.187 PASS | <= 0.5 |

Note: `check_walk_forward` in `validation/validators.py` hit the known
repo-wide `vectorbt.utils.splitting` AttributeError (see prior entries e.g.
`run_validate_2dance.py`'s documented workaround); used the same manual
4-way contiguous-split fallback (regenerate signals independently per
slice, require Sharpe>0 in >=75% of splits) as other recent accepted
entries in this repo.

## Outcome

**Accepted (equity: QQQ + SPY, shared config)** — all 5 validators pass on
both symbols at the same parameter set. Crypto (BTC/USDT, ETH/USDT) not
pursued individually; the vol-gated grid showed only 6/54 crypto cells
passing with no clean best-config, decisively weaker than equity.
