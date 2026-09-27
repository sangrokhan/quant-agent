# Backtest Report: Dual-RSI(2) Bollinger-Band-Bottom Mean Reversion (rejected)

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_dual_rsi2_bb_bottom_meanrev.py`
**Hypothesis id:** 2026-09-27-048

## Hypothesis

Per SetupAlpha's "Why Simpler Trading Strategies Survive Longer (4 Trading
Rules Beat 12 Rules)" (https://setup4alpha.substack.com/p/every-rule-you-add-is-a-risk,
read via `browser_exec`), the article's free-preview section discloses in
full the "simple" 4-condition mean-reversion baseline it contrasts against
an over-fit 12-rule version: primary-asset RSI(2)<20 pullback, AND the
broader market's own RSI(2)<20 pullback (adapted here to a primary/
benchmark pair: QQQ vs SPY for equity, ETH/USDT vs BTC/USDT for crypto),
AND entry at the Bollinger Band lower touch, exiting when RSI(2)>70.
Source's own out-of-sample (2019-2026) result: this simple version's
Sharpe IMPROVED out of sample (0.69->1.18).

## Grid test summary (Step 6)

`param_grid={"rsi_entry": [15, 20, 25], "bb_std": [1.5, 2.0, 2.5]}`,
equity primary=QQQ/benchmark=SPY, crypto primary=ETH/USDT/benchmark=
BTC/USDT, `vol_regime_splits=3`, sample 2019-01-01 to 2026-09-01.

- **total_cells:** 54, **passed_cells:** 11, **pass_fraction:** 0.204
- **by_asset_class:** equity 11/27 (0.41), crypto 0/27 (decisive reject)
- **by_vol_regime:** low 5/18 (0.28), mid 0/18 (0.0), high 6/18 (0.33)
- **best_cell:** QQQ, low-vol, `rsi_entry=15/bb_std=2.0`, Sharpe 1.44
- **worst_cell:** ETH/USDT, low-vol, `rsi_entry=15/bb_std=2.0`, Sharpe -0.65

## Single-config validation (Step 7) — best cell config, full sample

Config: `rsi_entry=15, bb_std=2.0` (default `rsi_exit=70`, `rsi_period=2`,
`max_hold_days=15`).

| Validator | QQQ (vs SPY) | SPY (vs QQQ) |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL 0.642 | FAIL 0.478 |
| Max drawdown (<=0.25) | PASS 0.171 | PASS 0.227 |
| Transaction-cost survival (net Sharpe >=0.5) | PASS 0.593 (35 trades) | FAIL 0.423 (36 trades) |
| Walk-forward (manual 4-split substitute) | PASS 1.0 (4/4) | PASS 0.75 (3/4) |
| Parameter sensitivity (relative_std<=0.5) | PASS 0.140 | PASS 0.197 |

Both fail Sharpe at the grid's best cell (full-sample Sharpe is
substantially lower than the single low-vol-regime cell's Sharpe of 1.44
that drove grid selection — the edge only shows up narrowly in the
low-vol tercile, not across the full sample). A broader 500-combination
retune (`rsi_entry` x `bb_std` x `rsi_exit` x `max_hold_days`) on QQQ/SPY
found the best achievable full-sample Sharpe is only 0.879
(`rsi_entry=15/bb_std=1.5/rsi_exit=75/max_hold_days=15`), still short of
the 1.0 threshold.

## Decision

**Rejected** (both QQQ/SPY and SPY/QQQ primary/benchmark pairings, and
decisively rejected on crypto). The source's disclosed simple 4-rule
mean-reversion baseline does not clear this repo's Sharpe threshold on
full-sample daily bars, even after a targeted retune. Note this is not
necessarily inconsistent with the source's own claim (their out-of-sample
period and universe differ — they test a cross-sectional S&P 500
constituent universe with per-stock entries, not a fixed QQQ/SPY pair,
and this repo's single-symbol interface cannot replicate the
cross-sectional selection effect that may be doing real work in the
source's own result).
