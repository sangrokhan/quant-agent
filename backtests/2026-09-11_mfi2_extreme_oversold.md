# 2026-09-11 2-Period MFI Extreme-Oversold Mean Reversion — Backtest Report

**Hypothesis:** 2-period MFI (Money Flow Index) below 10 signals extreme
oversold conditions; buy at the close, exit when close > yesterday's high,
with a 10-trading-day time stop. Source:
https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(visited this iteration, fully disclosed rule). Source's own QQQ backtest:
average gain per trade 0.46%, win rate 70%, annual return 11.1% at 34%
time invested.

## Threshold sensitivity note

At a 2-period lookback, MFI is strongly bimodal (saturates near 0 or 100
depending on whether the single most-recent typical-price change was
positive or negative) -- confirmed empirically (SPY 2010-2024: identical
806 signal days at oversold_threshold=5, 10, AND 15). This means the
"threshold" parameter has essentially no discriminating power at
mfi_window=2 in practice; the strategy behaves as a simple "did the most
recent up-day's money flow dominate the 2-bar window" binary trigger
rather than a genuinely graded oversold measure.

## Single-config validators (SPY/QQQ, 2010-2024, oversold_threshold=10, max_hold_days=10)

| Symbol | Sharpe | MDD | Trades | Net Sharpe (10bps/trade) | Passed |
|---|---|---|---|---|---|
| SPY | 0.970 | 0.172 ✅ | 1109 | 0.050 | Sharpe FAIL, TC FAIL (decisive) |
| QQQ | 0.884 | 0.205 ✅ | 1121 | 0.076 | Sharpe FAIL, TC FAIL (decisive) |

## Step 6 grid summary (oversold_threshold in [5,10,15] x max_hold_days in [5,10], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3)

- 72 total cells, 24 passed (pass_fraction 0.333)
- **by_asset_class**: equity 24/36 (66.7%), crypto 0/36 (0%)
- **by_vol_regime**: low 12/24, mid 6/24, high 6/24 (reasonably broad
  across regimes on the grid's per-slice Sharpe/MDD check, which does NOT
  incorporate transaction costs -- see full-sample validators above for
  the decisive TC failure)
- Best cell: SPY, oversold_threshold=5.0/max_hold_days=5, low-vol regime, Sharpe 1.71
- Worst cell: ETH/USDT, mid-vol regime, Sharpe 0.087

## Decision: REJECTED (decisive on transaction costs)

Both SPY and QQQ are near-misses on raw Sharpe (0.97/0.88, both just
under the 1.0 threshold) but this strategy trades extremely frequently
(~1100 trades over 14 years, ~79/year -- roughly one trade every 3-4
trading days) due to the 2-period MFI's near-binary daily oscillation.
Transaction-cost survival fails decisively (net Sharpe 0.05-0.08 at
repo-standard 10bps/trade vs 0.5 threshold) -- this is the highest
trade-frequency rejection this cron trigger, and unlike 2026-09-11-072/
-074 (near-miss on TC), this is not close. Crypto rejected decisively
(0/36).

## Notes for future iterations

- Third mean-reversion rejection this cron trigger to fail specifically
  on transaction costs (see also 2026-09-11-072, 2026-09-11-074) --
  reinforces the pattern that short-hold/high-frequency mean-reversion
  constructions are systematically hard to clear at this repo's 10bps/
  trade cost assumption, even when Sharpe/MDD look reasonable gross of
  costs. A future iteration should treat "trade frequency" as a
  first-class screening criterion BEFORE investing in a full grid/
  validator run for any oscillator-threshold mean-reversion idea with a
  very short lookback period (2-3 bars) -- these inherently generate
  high signal frequency and are unlikely to survive costs regardless of
  gross Sharpe.
- Confirmed technical quirk: 2-period MFI is bimodal/saturating (0 or
  100), making its "threshold" parameter largely non-discriminating in
  practice -- worth remembering if a future iteration considers any
  very-short-period (2-3 bar) money-flow-weighted oscillator.
