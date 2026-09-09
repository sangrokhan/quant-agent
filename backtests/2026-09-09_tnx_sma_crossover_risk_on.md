# 10Y Treasury Yield (^TNX) SMA Crossover Risk-On — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_tnx_sma_crossover_risk_on.py`
**Knowledge base id:** 2026-09-09-051

## Hypothesis

Per QuantifiedStrategies.com's "19 Best Intermarket Strategies" (disclosed
via Google search snippet, visited this iteration): "When the ten-year
Treasury rate crosses below its 25-day moving average, we buy the S&P
500." Falling/declining long-term yields reflect looser financial
conditions and a lower equity discount rate -- both risk-on tailwinds.
Distinct from every prior yield-related repo entry (spread-un-inversion
constructions, not a level-vs-its-own-SMA crossover of the yield itself).

## Source URLs (visited this iteration)

- https://www.google.com/search?q=time-weighted+average+price+TWAP+mean+reversion+signal+crypto+strategy (TWAP oscillator, not used -- construction overlaps heavily with already-tested z-score/divergence family)
- https://www.google.com/search?q=Ehlers+cyber+cycle+indicator+trading+strategy+rules (Cyber Cycle already tested twice, not used)
- https://www.google.com/search?q=intermarket+analysis+bond+yield+equity+strategy+signal+rules+10-year+treasury (used -- QuantifiedStrategies' 10Y-vs-SMA(25) crossover rule)

## Step 6 grid test summary

Grid: `sma_window` in {15,25,40} x `max_hold_days` in {20,40} x
{QQQ, SPY, BTC/USDT, ETH/USDT} x low/mid/high vol terciles, 72 cells,
2018-01-01 to 2024-12-31.

- **pass_fraction:** 0.319 (23/72)
- **by_asset_class:** equity 23/36, crypto 0/36 (decisive -- ^TNX has no
  crypto-relevant analogue, out of scope by construction)
- **by_vol_regime:** low 12/24, mid 6/24, high 5/24 (holds up reasonably
  across regimes, not concentrated in one)
- **best_cell:** sma_window=25, max_hold_days=40, QQQ, low-vol, Sharpe=2.81
- **worst_cell:** sma_window=25, max_hold_days=20, ETH/USDT, low-vol, Sharpe=-0.27 (crypto, out of scope)

## Step 7 single-config validation (primary config: sma_window=25 [source's own default], max_hold_days=20)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.913 | 1.816 | >= 1.0 | Yes (both) |
| Max drawdown | 0.134 | 0.086 | <= 0.25 | Yes (both) |
| Net Sharpe after costs (10bps/trade, 95 trades) | 1.730 | 1.585 | >= 0.5 | Yes (both) |
| Walk-forward pass fraction (manual 4-split) | 1.0 (4/4) | 1.0 (4/4) | >= 0.75 | Yes (both) |
| Parameter sensitivity (relative std across 6-cell QQQ sweep) | 0.303 | -- | <= 0.5 | Yes |

Note: same vectorbt `check_walk_forward` API mismatch flagged in
2026-09-09-048's report (`vectorbt.utils.splitting` unavailable) --
substituted the same manual 4-equal-split walk-forward.

## Decision: **ACCEPT**

All validators pass cleanly on both QQQ and SPY for the primary config
(sma_window=25, matching the source's own stated default). Trade
frequency (95 trades over ~7 years) is moderate and transaction-cost
survival is strong (net Sharpe still >1.5 after 10bps/trade). Crypto is
out of scope by construction (no analogous "risk-free rate proxy" input
series for crypto); strategy validity recorded as equity-only (QQQ, SPY).
Requires an auxiliary `yield_df` (^TNX) input, same pattern as this
repo's other cross-asset ratio strategies (e.g. GLD/SLV ratio RSI).
