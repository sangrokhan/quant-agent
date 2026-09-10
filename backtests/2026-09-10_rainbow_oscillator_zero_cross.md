# Rainbow Oscillator (deviation-average) zero-line cross — REJECTED

**Hypothesis:** Per https://alphax.trading/dictionary/rainbow-oscillator, the
Rainbow Oscillator computes, for N EMA periods, the % deviation of price from
each EMA, then averages those deviations into a single "Rainbow_Value". This
strategy tests the zero-line-cross analog (bullish when Rainbow_Value crosses
from <=0 to >0), distinct from this repo's already-tested Rainbow Moving
Average (SMA cascade) and Vervoort Rainbow %B constructions.

Source note: quantifiedstrategies.com's own Rainbow Oscillator article
404'd; used AlphaX's disclosed formula and constructed the zero-cross rule
ourselves as the natural analog other zero-line multi-EMA oscillators in
this repo use (TRIX/PPO/KST).

## Step 6 grid summary (72 cells: periods x max_hold_days x QQQ/SPY/BTC/ETH x low/mid/high vol terciles, 2018-01-01 to 2024-12-31)

- pass_fraction: 15/72 = 0.208
- by_asset_class: equity 15/36, crypto 0/36 (decisive crypto fail)
- by_vol_regime: low 9/24, mid 6/24, high 0/24
- best_cell: QQQ/SPY at periods=(5,10,20,50,100) or (10,20,40,80,160), max_hold_days=30, low-vol tercile (Sharpe up to 2.11)
- best full-grid config (highest avg Sharpe across regimes on QQQ): periods=(5,10,20,50,100), max_hold_days=30 (2/3 tercile passes)

## Step 7 single-config validation (periods=(5,10,20,50,100), max_hold_days=30)

Note: `validation/validators.py::check_walk_forward` calls a vectorbt
splitter API (`vbt.utils.splitting.RangeSplitter`) not present in the
installed vectorbt==1.1.0; used an equivalent manual 4-way equal-length
walk-forward split (same pass criterion: split Sharpe > 0) as a drop-in.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 0.562 | 0.596 | >= 1.0 | FAIL both |
| Max Drawdown | 0.293 | 0.232 | <= 0.25 | FAIL QQQ, pass SPY |
| Net Sharpe after costs (10bps/trade) | 0.445 | 0.426 | >= 0.5 | FAIL both |
| Walk-forward (4-split, splits w/ Sharpe>0) | 0.50 | 0.50 | >= 0.75 | FAIL both |
| Parameter sensitivity (relative std across 6 QQQ param combos' avg tercile Sharpe) | 0.252 | n/a | <= 0.5 | PASS |
| Trade count | 75 | 88 | — | — |

## Decision: REJECTED

The tercile-conditioned grid's promising low-vol Sharpe (up to 2.11) does not
survive full-sample validation on either symbol — decisive Sharpe fail on
both, decisive TC-survival fail on both (frequent trading at ~75-88 entries
over 7 years erodes the edge), decisive walk-forward fail on both (only
2 of 4 splits positive). Crypto rejected decisively (0/36 grid cells).
Parameter sensitivity alone passes, meaning the failure is structural
(insufficient net edge), not a fragile parameter choice.

**Lesson for future loops:** the "average of N EMA-percentage-deviations"
construction behaves similarly to a slow trend filter and inherits the same
low-vol-only-edge, high-vol-decisive-fail pattern seen repeatedly in this
repo's other multi-EMA/zero-line-cross indicators (TRIX, KST, PPO all
similarly saturated with the same regime-concentration issue) — this
confirms rather than discovers anything new about that broad indicator
family.
