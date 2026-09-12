# Backtest Report: Apirine TRAdj EMA Dual-Length Crossover + Min-Hold Hysteresis

**Strategy file:** `strategies/2026-09-12_apirine_tradj_ema_minhold.py`
**Hypothesis ID:** 2026-09-12-197
**Source:** Direct fix for rejected 2026-09-12-196 (Apirine TRAdj EMA
crossover, S&C Jan 2023); no new external source this iteration.

## Hypothesis

Add a `min_hold_days` hysteresis filter (opposite signal must persist for
N consecutive bars before flipping the position) on top of the prior
iteration's raw dual-TRAdj-EMA crossover, which was rejected for failing
Sharpe AND MDD with very high turnover (162-165 trades/8.5yr). This
established fix pattern (used successfully elsewhere in this repo, e.g.
Klinger 2026-09-04-085, ZLEMA 2026-09-06-171) should reduce whipsaw.

## Grid test (Step 6): `min_hold_days` in {3,5,10} (fast_length=8,
slow_length=40, tr_lookback=20, multiplier=7.5 fixed at prior iteration's
best config), QQQ/SPY equity + BTC/USDT, ETH/USDT crypto,
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.222** (8/36 cells) -- improved from the
  ungated version's 0.208.
- **By asset class:** equity 8/18; crypto 0/18 (decisive).
- **By vol regime:** low 6/12, mid 2/12, high 0/12.
- Best average-Sharpe configs: QQQ `min_hold_days=5` avg 1.403; SPY
  `min_hold_days=3` avg 1.297 (both markedly higher than the ungated
  version's 1.113/0.934).

## Single-config validation (Step 7), full 2018-2026 sample

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | min_hold=5 | 1.075 (pass) | **0.315** (**FAIL**, thr 0.25) | 1.043 (pass) | 1.00 (pass) | 0.233 (pass) | 36 |
| SPY | min_hold=3 | 1.110 (pass) | **0.200** (pass) | 1.032 (pass) | 1.00 (pass) | 0.301 (pass) | 56 |

Trade counts dropped dramatically vs. the ungated version (QQQ 165->36,
SPY 162->56), confirming the hysteresis filter worked as intended. SPY
now passes ALL 5 validators. QQQ improved substantially (Sharpe
0.757->1.075, trades cut by 78%) but still fails MDD -- also checked
`min_hold_days=3` (Sharpe 1.097 pass, MDD 0.324 fail) and `min_hold_days=
10` (Sharpe 0.626 fail, MDD 0.383 fail) as alternates for QQQ; none clear
the drawdown bar.

## Decision: **ACCEPT (SPY only, min_hold_days=3)**; reject QQQ and crypto

The min-hold hysteresis fix rescues SPY from the prior iteration's
decisive rejection to a full accept. QQQ remains rejected due to a
persistent MDD problem across all tested min_hold_days values -- its
volatility profile combined with this indicator's characteristic seems to
produce deeper drawdowns than SPY regardless of hold-period smoothing.
Crypto rejected decisively at the grid stage (0/18).
