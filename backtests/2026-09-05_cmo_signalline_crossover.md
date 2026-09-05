# CMO Signal-Line Crossover — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_cmo_signalline_crossover.py`
**KB id:** 2026-09-05-064

## Hypothesis

Per https://www.quantifiedstrategies.com/chande-momentum-oscillator-trading-strategy/:
"Some traders also add a 9-period moving average of the CMO to the
indicator as a signal line. When the indicator crosses above the signal
line, they consider it a bullish signal, and when it drops below the
signal line, they consider it a bearish signal." The source's own
backtest found a short (5-day) max holding period outperformed longer
holds (10/15/30 days). This strategy implements that CMO/signal-line
crossover rule directly (long on bullish cross, exit on bearish cross or
a `max_hold_days` time-stop), with no separate trend filter — distinct
from the already-rejected `2026-09-04-055` fixed ±50-threshold
oversold-reversal variant.

## Step 6 — Grid test (cmo_window x signal_window x max_hold_days x QQQ/SPY/BTC/ETH x 3 vol regimes)

- param_grid: `cmo_window=[9,14,20]`, `signal_window=[5,9]`, `max_hold_days=[5,10]`
- symbols: equity `[QQQ, SPY]`, crypto `[BTC/USDT, ETH/USDT]`
- vol_regime_splits=3 (low/mid/high realized-vol terciles)
- **144 total cells, 28 passed (pass_fraction = 0.194)**
- by_asset_class: equity 28/72 passed; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 17/48; mid 11/48; **high 0/48 (decisive fail in high-vol)**
- best_cell: SPY, cmo_window=14/signal_window=5/max_hold_days=5, low-vol regime, Sharpe=1.95
- worst_cell: SPY, cmo_window=20/signal_window=5/max_hold_days=5, mid-vol regime, Sharpe=-0.53

Grid shows a real but narrow edge concentrated in low/mid-vol equity slices; high-vol equity and all of crypto decisively fail. This narrow-but-real per-regime edge is consistent with the source's own note that CMO thrives with short holding periods and struggles otherwise.

## Step 7 — Single-config validators (best-looking config: cmo_window=14, signal_window=5, max_hold_days=5)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | 0.69 — FAIL | 0.76 — FAIL | >= 1.0 |
| Max drawdown | 0.227 — PASS | 0.252 — FAIL | <= 0.25 |
| Transaction cost survival (10bps/trade, ~260 trades) | 0.35 — FAIL | 0.35 — FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split, manual fallback — vbt.utils.splitting missing) | 0.75 — PASS | 0.75 — PASS | >= 0.75 |
| Parameter sensitivity (relative std across 12-cell sweep) | 0.283 — PASS | 0.546 — FAIL | <= 0.5 |

Despite a promising best-cell Sharpe of 1.95 in the low-vol regime alone,
the **full-period (unconditional) Sharpe on both QQQ and SPY fails the
>=1.0 threshold, and transaction costs (~260 round trips over the sample
at 10bps) crush the net Sharpe to ~0.35** on both symbols — the strategy
trades too frequently (short 5-day holds, frequent signal-line crossovers)
for its edge to survive realistic costs.

## Step 8 — Decision: **REJECT**

Multiple validators fail decisively (full-period Sharpe, transaction-cost
survival on both QQQ/SPY; max drawdown and parameter sensitivity also fail
on SPY). The grid's low/mid-vol-only edge does not survive unconditional
full-period testing or cost-adjustment. Crypto is a decisive 0/72 grid
fail. Strategy/report kept as a record of a rejected attempt — this is
NOT a live strategy.
