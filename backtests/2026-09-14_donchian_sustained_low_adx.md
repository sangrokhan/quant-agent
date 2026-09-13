# Backtest Report: Donchian Breakout Gated by SUSTAINED Low-ADX Consolidation

**Strategy file:** `strategies/2026-09-14_donchian_sustained_low_adx.py`
**Knowledge base id:** 2026-09-14-118

## Hypothesis

Follow-up to this cron trigger's 2026-09-14-116 (single-bar low-ADX gate:
QQQ accepted, SPY near-miss, crypto decisively rejected via turnover
explosion, 1535 trades) and 2026-09-14-117 (own regime analysis: BTC/USDT
spends ~49.5% of time below ADX 25, similar to QQQ's 58.7% -- crypto is
not "never quiet", so the single-bar gate's failure was hypothesized to be
about DURATION of quiet periods, not their frequency). This iteration
requires ADX to stay at/below `adx_max` for at least
`min_consolidation_bars` CONSECUTIVE bars before the breakout (not just the
single bar right before it), testing whether filtering for genuinely
sustained coils (vs brief noisy dips) suppresses crypto's excess turnover.

## Config tested (per-symbol full-sample best config)

- QQQ: donchian_window=25, min_consolidation_bars=3, atr_multiplier=3.0
- SPY: donchian_window=25, min_consolidation_bars=3, atr_multiplier=3.0
- BTC/USDT: donchian_window=15, min_consolidation_bars=3, atr_multiplier=2.5

## Single-config validator results

| Validator | QQQ | SPY | BTC/USDT |
|---|---|---|---|
| Sharpe (>=1.0) | 1.070 PASS | 0.458 FAIL | 0.230 FAIL |
| Max Drawdown (<=0.25) | 0.158 PASS | 0.176 PASS | 0.477 FAIL |
| TC survival (10bps/trade, net Sharpe >=0.5) | 0.993 PASS (45 trades) | 0.342 FAIL (63 trades) | 0.054 FAIL (**1701 trades**) |
| Walk-forward (4 manual contiguous folds, >=0.75) | 1.0 PASS (4/4) | 0.75 PASS (3/4) | 1.0 PASS (4/4) |
| Param sensitivity (min_consolidation_bars x donchian_window sweep, rel-std <=0.5) | 0.045 PASS | 0.065 PASS | 0.119 PASS (base already failing) |
| **All pass?** | **YES** | **NO (Sharpe/TC fail)** | **NO (Sharpe/MDD/TC all fail)** |

## Grid summary (Step 6)

`param_grid={donchian_window:[15,25], min_consolidation_bars:[3,5,10],
atr_multiplier:[2.5,3.0]}`, `symbols={equity:[QQQ,SPY],
crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells=144, passed_cells=33, **pass_fraction=0.229**
- by_asset_class: equity 33/72 passed, **crypto 0/72 passed**
- by_vol_regime: low 24/48, mid 9/48, **high 0/48**
- best_cell: SPY, donchian_window=25, min_consolidation_bars=3,
  atr_multiplier=3.0, low-vol regime, Sharpe=2.131

## Decision: ACCEPT (QQQ only, same conclusion as 2026-09-14-116) / REJECT (SPY, crypto)

QQQ passes all 5 validators (Sharpe 1.070, MDD 15.8%, TC-survival 0.993 on
45 trades -- fewer trades than the single-bar-gate version's 53, confirming
the persistence requirement does reduce equity turnover somewhat). SPY
remains a near-miss on Sharpe/TC-survival, essentially unchanged from
2026-09-14-116.

**Crypto's rejection is NOT fixed, and in fact got MARGINALLY WORSE: trade
count rose from 1535 (single-bar gate) to 1701 (3-bar persistence gate),
and low-vol-tercile Sharpe stayed at ~0.23-0.34 (still far below 1.0) even
though low-vol-tercile MDD did improve into the passing range (17-23% vs
25% threshold) at some configs.** This falsifies the specific mechanism
hypothesized in 2026-09-14-117: requiring ADX to be persistently low for
several consecutive bars does NOT meaningfully filter out crypto's
choppiness, likely because BTC/ETH's ADX oscillates in and out of the
sub-25 band on a timescale comparable to or shorter than the
`min_consolidation_bars` windows tested (3/5/10 days) -- the "quiet"
periods aren't actually contiguous enough at any tested window length to
distinguish genuine coils from noise. A larger `min_consolidation_bars`
(e.g. 20-30 days) might work but was not in this iteration's grid; more
importantly, this refines the repo's running meta-finding further: crypto's
ADX signal itself may carry too little autocorrelation/regime-persistence
at the daily timeframe for ANY ADX-threshold-based consolidation filter
(single-bar or multi-bar) to work as a crypto turnover-reduction mechanism,
independent of window length.
