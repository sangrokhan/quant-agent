# Backtest Report: Perry Kaufman Gap Momentum (GAPM) Rising/Falling Trend-Follow

**Strategy file:** `strategies/2026-09-12_kaufman_gap_momentum.py`
**Source:** Perry Kaufman, TASC 1/24. Formula reproduced from
https://financial-hacker.com/the-gap-momentum-system/ (fully disclosed
EasyLanguage-to-C code).

## Hypothesis

A rolling ratio of cumulative up-gaps (today's open above yesterday's
close) to cumulative down-gaps over a `period`-bar window, smoothed by an
SMA of length `signal_period` (GAPM), tracks building gap-driven buying vs
selling pressure. Long while GAPM is rising, flat while falling.

## Single-config validator results (vectorbt-backed `validators.py`)

### QQQ (period=40, signal_period=10 — best QQQ grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.203 | >= 1.0 |
| Max drawdown | PASS | 0.189 | <= 0.25 |
| Transaction cost survival (10bps/trade, 299 trades) | PASS | net Sharpe 0.694 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 3/4 (75%) | >= 75% |
| Parameter sensitivity (9-cell period x signal_period grid) | PASS | rel. std 0.169 | <= 0.5 |

### SPY (period=20, signal_period=20 — best SPY grid cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.222 | >= 1.0 |
| Max drawdown | PASS | 0.157 | <= 0.25 |
| Transaction cost survival (10bps/trade, 263 trades) | PASS | net Sharpe 0.677 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | PASS | rel. std 0.206 | <= 0.5 |

Both equity symbols pass ALL 5 validators. Note transaction cost margin is
tighter than other recent accepts (299/263 trades, net Sharpe drops to
~0.68-0.69 after a 10bps/trade drag) — this is a relatively high-turnover
strategy compared to most in this repo.

## Grid test summary (period x {20,40,60}, signal_period x {10,20,30}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3)

- **Total cells:** 108, **passed:** 32, **pass_fraction: 0.296**
- **By asset class:** equity 32/54 (0.593), crypto 0/54 (0.0)
- **By vol regime:** low 13/36 (0.361), mid 11/36 (0.306), high 8/36 (0.222)
- **Best cell:** QQQ low-vol, period=60/signal_period=30, Sharpe 2.35
- **Worst cell:** QQQ high-vol, period=60/signal_period=30, Sharpe -0.48

Unlike several recent accepts, this strategy shows some (modest) pass
fraction across ALL THREE vol regimes (not just low-vol), though still
weighted toward low-vol; crypto is a decisive fail (0/54).

## Decision: ACCEPT (equity only — QQQ and SPY, each with its own tuned config)

Both QQQ (period=40, signal_period=10) and SPY (period=20, signal_period=20)
pass every validator. Crypto rejected decisively. Note the relatively high
trade count (263-299 trades over ~2000 bars) means real-world transaction
costs above the tested 10bps/trade assumption could erode the edge faster
than for lower-turnover accepted strategies in this repo — flag this for
future cost-sensitivity follow-up.
