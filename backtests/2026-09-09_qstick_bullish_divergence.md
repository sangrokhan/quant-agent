# Backtest report: Qstick (Chande) bullish price/indicator divergence

**Strategy file:** `strategies/2026-09-09_qstick_bullish_divergence.py`
**KB id:** 2026-09-09-088

## Hypothesis

Per https://www.tradingpedia.com/forex-trading-indicators/chandes-quick-stick-qstick/
(accessed via browser_exec fallback — web_search's DDGS backend errored with
a TLS connection error), Chande's Qstick documents three signal families:
zero-line crossover (tested 3x already in this repo), extreme-level
reversal, and divergence ("If the market is forming lower lows while the
Qstick is forming higher lows, this represents a bullish divergence and is
a signal to buy"). First Qstick-divergence variant tested in this repo.
Implementation: divergence flagged when price makes a new swing-lookback-bar
low while Qstick sits above its value at the prior new-low bar; entry fires
when Qstick then crosses back above zero (source's own crossover trigger,
reused as timing confirmation); exit on Qstick crossing back below zero or
a max_hold_days time-stop.

## Grid test (Step 6)

`param_grid`: `qstick_window=[10,14,20]`, `swing_lookback=[15,20]`,
`max_hold_days=[10,15,20]`; `symbols`: equity `[QQQ, SPY]`, crypto
`[BTC/USDT, ETH/USDT]`; `vol_regime_splits=3`; period 2019-01-01..2026-09-01.

- **pass_fraction:** 0.093 (20/216)
- **by_asset_class:** equity 20/108, crypto 0/108 (crypto rejected decisively)
- **by_vol_regime:** low 14/72, mid 4/72, high 2/72 — again, like the prior
  SFP iteration, edge concentrated almost entirely in low-vol regimes.
- **best_cell:** qstick_window=14, swing_lookback=15, max_hold_days=15, SPY,
  low-vol regime, Sharpe 2.07 (regime-sliced).
- **worst_cell:** qstick_window=20, swing_lookback=20, max_hold_days=10, QQQ,
  low-vol regime, Sharpe -1.19.

## Single-config validation (Step 7) — best full-period config (qstick_window=14, swing_lookback=15, max_hold_days=15)

vectorbt's `check_walk_forward` remains broken repo-wide — substituted the
established manual 4-equal-split walk-forward check.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | -0.249 — **FAIL** | 0.112 — **FAIL** |
| Max drawdown (<=0.25) | 0.287 — **FAIL** | 0.152 — pass |
| TC survival (net Sharpe >=0.5, 10bps/trade) | -0.339 — **FAIL** | 0.010 — **FAIL** |
| Walk-forward (manual 4-split, >=75% positive) | 2/4 (0.5) — **FAIL** | 3/4 (0.75) — pass |
| Parameter sensitivity (relative std <=0.5) | 0.687 — **FAIL** | 0.977 — **FAIL** |

Full-sample results are far worse than the grid's best regime-sliced cell
(Sharpe 2.07) — the divergence-confirmation signal produces very few trades
(46-66 over 7.7yr) and is highly sensitive to the exact combination of
qstick_window/swing_lookback, consistent with the pattern only working
reliably in a narrow low-vol slice rather than broadly.

## Decision

**Rejected** (both QQQ and SPY) — nearly every validator fails on the
full, un-regime-filtered sample; QQQ additionally breaches the max-drawdown
threshold. Crypto rejected decisively (0/108 grid cells).

**Worth revisiting:** same pattern as the SFP iteration earlier this cron
trigger — low-vol-regime slices pass far more often (14/72 vs 4/72 mid, 2/72
high). A future iteration could explicitly gate this signal (or the SFP one)
to only trade in the low-vol tercile, similar to
`2026-09-03_bb_meanrev_qqq_volregime.py`'s explicit regime filter, rather
than trading either raw pattern across all regimes.
