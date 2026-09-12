# Backtest Report: Apirine HHLLS Crossover + SMA Trend Filter (Direct Fix)

**Strategy file:** `strategies/2026-09-12_apirine_hhlls_trend_filtered.py`
**Hypothesis ID:** 2026-09-12-195
**Source:** Direct fix for near-miss 2026-09-12-194 (Apirine HHLLS
two-stage crossover, S&C Feb 2016); no new external source this iteration.

## Hypothesis

Add an independent SMA trend filter (close above/below trailing SMA, both
as entry gate AND exit condition) on top of the prior iteration's raw
HHS/LLS two-stage crossover. Direct fix for that iteration's near-miss
QQQ result (all validators passed except MDD, 0.257 vs 0.25 threshold),
hypothesizing that the raw crossover has no independent trend confirmation
and can stay long through adverse market conditions.

## Grid test (Step 6): `lookback_window` in {10,20} x `trend_sma_window`
in {50,100,150}, QQQ/SPY equity + BTC/USDT, ETH/USDT crypto,
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.222** (16/72 cells) -- same as the prior
  ungated version, but MDD control improved materially at the
  single-config level (see below).
- **By asset class:** equity 16/36; crypto 0/36 (decisive fail).
- **By vol regime:** low 12/24, mid 4/24, high 0/24.
- **Best cell:** QQQ, low-vol, `lookback_window=10, trend_sma_window=50`
  (Sharpe 2.92).
- Best average-Sharpe config: QQQ `lookback_window=10,
  trend_sma_window=50`, avg Sharpe 1.538 (best across vol-regime terciles).

## Single-config validation (Step 7), full 2018-2026 sample

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | lw=10, trend_sma=50 | 1.275 (pass) | **0.132** (pass, vs 0.257 pre-fix) | 1.201 (pass) | 1.00 (pass) | 0.206 (pass) | 54 |
| SPY | lw=10, trend_sma=100 | 0.853 (**FAIL**) | 0.109 (pass) | 0.752 (pass) | 1.00 (pass) | 0.149 (pass) | 51 |

QQQ now passes ALL 5 validators cleanly -- the trend filter nearly HALVED
max drawdown (0.257 -> 0.132) while actually IMPROVING Sharpe (1.042 ->
1.275) and net-of-cost Sharpe. SPY's Sharpe remains below threshold
(0.853) despite passing every other validator.

## Decision: **ACCEPT (QQQ only, lookback_window=10, trend_sma_window=50)**

The direct fix successfully resolves the prior iteration's near-miss: MDD
control improves dramatically without sacrificing return, confirming the
report's own hypothesis that an independent trend filter was the missing
piece. SPY does not clear the Sharpe bar with this fix (near-miss at
0.853) -- reject SPY, note for a future iteration that SPY may need a
different trend_sma_window or an additional confirming filter. Crypto
rejected decisively at the grid stage (0/36).
