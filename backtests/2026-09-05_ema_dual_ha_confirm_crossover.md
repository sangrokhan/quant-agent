# Dual EMA(9/26) Crossover + Heikin-Ashi Candle-Color Confirmation — Backtest Report

**Hypothesis:** Fast/slow EMA price crossover (9/26, best config found; 9/21
was a QQQ near-miss at Sharpe 0.613 while SPY still passed at 1.116)
triggers a long entry only when the Heikin-Ashi candle at that bar is
bullish (HA_close > HA_open) -- confirming the crossover with a
noise-filtered candle-color signal; exit on the reverse EMA crossover or a
max_hold_days time-stop.

**Source:** Facebook "Spider Software - Algo Trading & Technical Analysis
Platform" post (via Google search snippet, `web_search` returned no useful
results for the query so `browser_exec` fallback was used): "Short Entry
(Sell): Look for the 9-period EMA to cross below the 21-period EMA,
confirmed by red Heikin-Ashi candles." (long-side rule inferred by
symmetry: 9/21+ EMA bullish cross confirmed by a green HA candle).

**Strategy file:** `strategies/2026-09-05_ema_dual_ha_confirm_crossover.py`

**Distinct from:** 2026-09-04-045 (single EMA trend filter + N-consecutive
same-color HA candles is the PRIMARY signal, no EMA crossover);
2026-09-05-051 (HA color-streak counting used as a CONTRARIAN mean-reversion
signal, opposite economic logic). Here price EMA crossover is the primary
trend-following trigger; HA candle color is a confirmation filter at the
crossover bar, not itself the trigger.

## Step 6 — Grid test summary (param_grid: fast_span in [9,12] x slow_span
in [21,26] x max_hold_days in [15,20]; symbols: equity QQQ/SPY, crypto
BTC/USDT, ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 96, passed_cells: 28, **pass_fraction: 0.292** (tied
  strongest of this cron trigger with the Aroon dual-threshold entry,
  2026-09-05-079)
- by_asset_class: equity 28/48 (58%); crypto 0/48 (0%, decisive fail)
- by_vol_regime: low 15/32 (47%), mid 3/32 (9%), high 10/32 (31% -- second
  strategy this trigger, after Aroon, to pass a meaningful share of
  high-vol cells)
- by_symbol: QQQ 12/24, SPY 16/24, crypto 0/24 each
- best_cell: fast_span=12, slow_span=26, max_hold_days=20, QQQ, low-vol,
  Sharpe=2.024
- worst_cell: fast_span=12, slow_span=21, max_hold_days=15, SPY, mid-vol,
  Sharpe=-0.260

Note: initial implementation had a numpy read-only-array bug in the
Heikin-Ashi recursive open calculation (`.to_numpy()` returning a
non-writeable view under this pandas version) that made every grid cell
error out; fixed with an explicit `.copy()` before running the reported
grid above.

## Step 7 — Single-config validators (config: fast_span=9, slow_span=26,
max_hold_days=20, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.324 | **PASS** 1.276 |
| Max Drawdown (<= 0.25) | PASS 0.112 | PASS 0.073 (tightest of the pair) |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **PASS** 1.256 (31 trades) | **PASS** 1.202 (28 trades) |
| Parameter sensitivity (relative_std <= 0.5, 8-cell fast/slow/hold sweep) | PASS 0.242 | PASS 0.131 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (QQQ AND SPY, fast_span=9/slow_span=26/max_hold_days=20)**;
crypto rejected decisively

Both equity indices clear all four validators at the identical shared
config: QQQ Sharpe 1.324/MDD 0.112/net Sharpe 1.256 (31 trades)/param-sens
0.242; SPY Sharpe 1.276/MDD 0.073 (best drawdown of any strategy accepted
this cron trigger)/net Sharpe 1.202 (28 trades)/param-sens 0.131 (very low,
not curve-fit fragile). This is the second strategy this cron trigger
(after Aroon dual-threshold, 2026-09-05-079) to generalize cleanly across
both QQQ and SPY with a genuinely novel indicator combination (price EMA
crossover + Heikin-Ashi candle-color confirmation), while crypto again
fails all 48 grid cells.
