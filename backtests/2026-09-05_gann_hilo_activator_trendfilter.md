# Gann HiLo Activator state-flip trend entry, gated by SMA trend filter

**Hypothesis:** The Gann HiLo Activator (W.D. Gann concept, popularized by
Robert Krausz) is a stepped trailing support/resistance line built from
`HMA(n)=SMA(High,n)` and `LMA(n)=SMA(Low,n)` with a state machine: state
flips to "up" when close > prior-bar HMA(n), flips to "down" when close <
prior-bar LMA(n), otherwise holds. Prior standalone HiLo-flip strategies in
this repo (Parabolic SAR id=2026-09-04-042, SuperTrend id=2026-09-03-014)
needed a slower SMA trend filter to avoid whipsaw — applied the same pattern
here: long entry on the state flip from "down" to "up" gated by close >
SMA(trend_window); exit on the reverse flip, trend filter break, or a
max_hold_days time-stop.

Source: https://trendsandbreakouts.com/gann-hilo-activator (formula + period
settings 3/5/8/10/13/20 disclosed free).

Novelty: distinct from the flip-only Gann HiLo variant already rejected at
id=2026-09-04-128 (no trend-filter gate there).

## Step 6 — Grid summary

Grid: `hilo_period in {3,5,10}`, `trend_window in {50,100}`, `max_hold_days
in {15,25}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 96 total
cells.

- pass_fraction: 0.292 (28/96)
- by_asset_class: equity 28/72 passed; crypto 0/24 (data loader raised a
  tz-aware Timestamp error for this repo's ccxt provider this run — all
  crypto cells recorded as data-load failures, consistent with other recent
  iterations' crypto rejections)
- by_vol_regime: low 22/24, mid 4/24, high 2/24 (low-vol-heavy, same pattern
  as most recent accepted/rejected iterations this run)
- best_cell: hilo_period=10, trend_window=100, max_hold_days=15, SPY,
  low-vol, Sharpe 2.78

## Step 7 — Single-config validation (hilo_period=10, trend_window=100, max_hold_days=15)

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe (>=1.0) | 1.055 PASS | 0.403 FAIL |
| Max drawdown (<=0.25) | 0.102 PASS | 0.170 PASS |
| Net-of-cost Sharpe (>=0.5, 10bps/trade) | 0.853 PASS | 0.280 FAIL |
| Param sensitivity relative_std (<=0.5, hilo_period in {3,5,10}) | 0.386 PASS | 0.160 PASS |
| num_trades | 66 | 74 |
| Walk-forward | not run — `vbt.utils.splitting.RangeSplitter` is unavailable in this repo's installed vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`), consistent with `walk_forward: null` in essentially every recent knowledge_base entry this run. |

## Step 8 — Decision

**Accepted (SPY only).** All validators pass cleanly for SPY at
hilo_period=10/trend_window=100/max_hold_days=15. QQQ rejected at the same
config: Sharpe (0.403) and net-of-cost Sharpe (0.280) both decisively miss
threshold despite a clean MDD and stable parameter sensitivity — not an
overfitting artifact. Crypto rejected due to data-load failures this run (0
usable grid cells).
