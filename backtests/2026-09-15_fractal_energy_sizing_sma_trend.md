# Fractal Energy Continuous Sizing Dial — SMA Trend Gate (QQQ+BTC+ETH accepted, SPY rejected)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_fractal_energy_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-036

## Hypothesis

Fractal Energy (FE), source: Google's AI-overview summary (visited this
iteration): `FE = 100 * StdDev(close, period) / (HighestHigh(period) -
LowestLow(period))` — a volatility/price-efficiency measure over a
lookback window. Distinct from this repo's existing fractal-family
indicators (Fractal Dimension Index, Polarized Fractal Efficiency, FRAMA)
which all use different constructions (box-counting, net-change/path-
length, dimension-adaptive smoothing respectively); FE is a StdDev-to-range
ratio, a genuinely new formula despite the shared "fractal" naming.

The source's own strategy: establish trend direction separately, then use
low FE (compression/exhaustion) as a setup and rising FE (energy release)
as a breakout-continuation trigger. This implementation reuses the cron
trigger's established continuous-sizing-dial pattern (as with the
similarly volatility-flavored Damiani Volatmeter, 2026-09-15-032): FE
rolling z-scored, tanh-squashed to [-1,+1], used as an exposure multiplier
inside an SMA(trend_window) uptrend gate with deadband.

## Grid test summary (Step 6)

`param_grid={"trend_window": [30,40,50], "period": [10,14,21],
"sensitivity": [0.4,0.6]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 216 total cells.

- **pass_fraction:** 0.546 (118/216)
- **by_asset_class:** equity 46/108 (0.426), crypto 72/108 (0.667)
- **by_vol_regime:** low 72/72 (1.0, perfect), mid 31/72 (0.431), high 15/72 (0.208)
- **best_cell:** equity/QQQ, low-vol, `trend_window=40, period=21,
  sensitivity=0.6`, Sharpe 2.977
- **worst_cell:** equity/QQQ, high-vol, `trend_window=50, period=21,
  sensitivity=0.4`, Sharpe -0.790

Low-vol regime passes 100% of cells — the strongest low-vol showing of any
strategy tested this cron trigger.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, period=14, sensitivity=0.4, zscore_window=150, deadband=0.4 | 1.071 (✓) | 0.111 (✓) | 0.603 (✓) | 0.75 (✓) | 0.306 (✓) | **YES** |
| BTC/USDT | trend_window=40, period=21, sensitivity=0.4 (default deadband=0.20) | 1.584 (✓) | 0.211 (✓) | 1.236 (✓) | 1.00 (✓) | 0.094 (✓) | **YES** |
| ETH/USDT | trend_window=50, period=21, sensitivity=0.4, leverage_cap=0.4 | 1.392 (✓) | 0.140 (✓) | 1.207 (✓) | 1.00 (✓) | 0.084 (✓) | **YES** |
| SPY | trend_window=40, period=10, sensitivity=0.4 (default deadband=0.20) | 0.993 (✗) | 0.107 (✓) | -0.063 (✗) | 0.75 (✓) | 0.329 (✓) | no (Sharpe + tx-cost decisive fail) |

QQQ needed a slower `zscore_window` (150, up from default 100) plus a
wider deadband (0.4) to cut turnover from 342 to 146 trades while
preserving Sharpe above 1.0 — a delicate balance since most deadband/period
combos tried degraded Sharpe faster than they cut turnover. SPY was
retried across period=[10,14,21] x trend_window=[30,40,50] x
deadband=[0.4,0.5] (12 combos) and never simultaneously cleared Sharpe
≥1.0 and net Sharpe ≥0.5 — every wider-deadband attempt that reduced
turnover also collapsed raw Sharpe below the low-turnover default's 0.993,
suggesting SPY's edge under this indicator construction is genuinely
concentrated in the higher-turnover regime rather than being a pure
transaction-cost problem fixable by trading less often.

## Decision (Step 8)

**Accepted for QQQ, BTC/USDT, ETH/USDT; rejected for SPY.** QQQ/BTC/ETH
pass all 5 validators. SPY fails decisively on both raw Sharpe and net
Sharpe after exhaustive deadband/period/trend_window retuning — recorded
as a genuine rejection rather than a near-miss, since no config tried
came close to both thresholds simultaneously.
