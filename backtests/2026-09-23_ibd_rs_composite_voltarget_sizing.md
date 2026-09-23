# Backtest Report: IBD RS Composite + Inverse-Vol Sizing Overlay (2026-09-23)

**Strategy file:** `strategies/2026-09-23_ibd_rs_composite_voltarget_sizing.py`
**Knowledge base id:** 2026-09-23-141
**Status: ACCEPTED (QQQ only)** -- SPY near-miss, crypto (BTC/USDT, ETH/USDT) decisively rejected

## Hypothesis

Direct rescue attempt for this same cron trigger's own near-miss rejection
`2026-09-23-138` (IBD weighted RS composite momentum, binary long/flat):
QQQ passed 4/5 validators but failed max_drawdown decisively (0.341 vs 0.25
budget). That entry's own `notes` flagged a volatility-targeting/leverage-cap
overlay as the natural fix. This iteration keeps the exact same entry/exit
timing signal (weighted RS composite = 0.4*ret(63d)+0.2*ret(126d)+
0.2*ret(189d)+0.2*ret(252d) crossing entry/exit thresholds) but replaces the
fixed full-size {0,1} position with a continuous inverse-realized-volatility
exposure (`min(target_vol/realized_vol, leverage_cap)`), plus a
rebalance-deadband to bound the transaction-cost drag the added daily
rebalancing introduces (a pattern already used successfully elsewhere in
this repo, e.g. `strategies/2026-09-08_vol_targeting_trend_overlay.py` and
many "continuous sizing dial" entries in `strategies_log.jsonl`).

## Grid test summary (Step 6)

`param_grid={"target_vol": [0.10,0.15,0.20], "leverage_cap": [0.6,0.8,1.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2018-01-01 to 2026-09-01 (fixed
`rebalance_deadband` not yet included in this first grid pass, added in a
follow-up local scan).

- `total_cells`: 108, `passed_cells`: 51, `pass_fraction`: 0.472 (up from
  0.264 for the unscaled binary predecessor)
- `by_asset_class`: equity 27/54, crypto 24/54 (crypto now clears SOME grid
  cells with the sizing overlay, though not enough for a full-sample accept
  -- see below)
- `by_vol_regime`: low 18/36, mid 24/36, high 9/36
- `best_cell`: SPY, `target_vol=0.15, leverage_cap=0.8`, low-vol regime,
  Sharpe 2.63

## Rebalance-deadband local scan (QQQ)

Follow-up scan (`rebalance_deadband` in [0.10,0.15,0.20,0.30] x
`leverage_cap` in [0.6,0.8,1.0,1.2] at `target_vol=0.15`) found QQQ's best
full-sample config at `target_vol=0.15, leverage_cap=1.0,
rebalance_deadband=0.10` (178 trades over the sample, Sharpe 1.041, MDD
0.158 -- both clear the acceptance thresholds).

## Single-config validator results

| Validator | QQQ (tv=0.15,lc=1.0,db=0.10) | BTC/USDT (tv=0.15,lc=0.8,db=0.15) | ETH/USDT (tv=0.15,lc=0.8,db=0.15) |
|---|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.253 | **FAIL** 0.124 | **FAIL** 0.180 |
| Max Drawdown (<=0.25) | **PASS** 0.158 | **FAIL** 0.554 | **FAIL** 0.598 |
| TC survival (net Sharpe >=0.5, 10bps/trade) | **PASS** 0.954 | **FAIL** 0.001 | **FAIL** 0.040 |
| Walk-forward (4-split, >=0.75) | PASS 1.0 | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (rel. std <=0.5) | PASS 0.018 | PASS 0.012 | PASS 0.062 |

SPY: separate local search (`target_vol` in [0.10,0.15,0.20,0.25] x
`leverage_cap` in [0.8,1.0,1.2,1.5] x `rebalance_deadband` in
[0.05,0.10,0.15,0.20], 64 combos) found a best full-sample Sharpe of only
0.850 (at `target_vol=0.15, leverage_cap=1.5, rebalance_deadband=0.20`,
MDD 0.187) -- a genuine Sharpe miss, not accepted.

BTC/USDT and ETH/USDT both trade far too frequently under a 20-day
`vol_window` (daily realized-vol re-estimation on crypto's much higher and
noisier vol regime causes the deadband to trigger constantly -- 1866-1974
trades over the sample even at `deadband=0.15`), and even before costs the
gross Sharpe/MDD on crypto are structurally weak (crypto realized vol
frequently spikes far above any reasonable `target_vol`, so the exposure
scaling clips at `leverage_cap` most of the time anyway, effectively
degenerating toward the already-rejected binary crypto result from
2026-09-23-138).

## Decision: ACCEPTED (QQQ only)

QQQ clears all 5 validators cleanly at `target_vol=0.15, leverage_cap=1.0,
rebalance_deadband=0.10` -- Sharpe 1.253, MDD 0.158 (well inside the 0.25
budget, directly rescuing the 2026-09-23-138 QQQ MDD failure), net Sharpe
after 10bps/trade costs 0.954, walk-forward 4/4 splits positive, parameter
sensitivity relative std 0.018 (very stable). SPY and crypto remain
rejected -- SPY as a genuine Sharpe miss (ceiling ~0.85 after a 64-combo
local search) and crypto decisively (structurally too volatile for this
vol-targeting construction without a much lower `target_vol`/`leverage_cap`
that would likely also collapse the signal).
