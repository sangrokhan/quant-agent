# Coppock Curve Momentum (Daily-Bar Adaptation)

**Strategy file:** `strategies/2026-09-08_coppock_curve_momentum.py`
**Source:** https://www.quantifiedstrategies.com/coppock-curve-strategy/

## Hypothesis

Edwin Coppock's 1962 momentum indicator — `WMA(ROC(close,11)+ROC(close,14),10)`
on MONTHLY bars, zero-line crossover for long entry/exit — captures broad
market uptrends while filtering downtrends. Source's own monthly backtest
(S&P 500 since 1960): 12 trades, 100% win rate, avg gain 45%/trade, max
drawdown 30.16% vs buy-and-hold 52.56%. Adapted here to daily bars by
scaling all three periods to trading-day equivalents (~21 trading
days/month): roc1≈231d, roc2≈294d, wma≈210d as defaults, with a shorter
variant (110/140/100d ≈ half-length) also grid-tested since the repo's
~26-year daily-bar equity history is still short relative to monthly-bar
requirements.

## Grid test summary (Step 6)

`param_grid`: `roc1_period in {110,231}`, `roc2_period in {140,294}`,
`wma_period in {100,210}`; `vol_regime_splits=3`; symbols: equity
QQQ/SPY (2000-2026), crypto BTC/USDT + ETH/USDT daily bars (2017-2026,
forced `interval="1d"` since Coppock's periods are meaningless on the
default 1h crypto interval).

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 16/48 (0.333) | 16/16 | 0/16 | 0/16 |
| crypto (BTC/ETH, daily) | 0/48 (0.0) | 0/16 | 0/16 | 0/16 |

Best cell: equity, `roc1_period=110, roc2_period=140, wma_period=100`,
low-vol regime, Sharpe 1.91 (QQQ). Crypto rejected decisively across all
cells/regimes — likely because BTC/ETH's ~9-year history is too short
relative to these long lookback periods (110-294 trading days) to
generate a meaningful number of trades/regime coverage.

**Finding:** the strategy's edge, if any, is entirely confined to the
low-vol tercile — identical pattern to several other momentum/trend
strategies tested this cron trigger. Full-period (all-regime) Sharpe
likely diluted below threshold, confirmed below.

## Single-config validation (Step 7) — best config: roc1_period=110, roc2_period=140, wma_period=100, max_hold_days=500

| Symbol | Sharpe | MDD | TC-survival | Walk-forward |
|---|---|---|---|---|
| QQQ | ❌ 0.956 (< 1.0) | ❌ 0.302 (> 0.25) | ✅ 0.954 net Sharpe | ✅ 4/4 splits positive |
| SPY | ❌ 0.737 (< 1.0) | ❌ 0.341 (> 0.25) | ✅ 0.735 net Sharpe | ✅ 4/4 splits positive |

Both QQQ and SPY fail Sharpe AND max drawdown on the full-period
(all-vol-regime) backtest, despite passing TC-survival and walk-forward.
Only 11-12 trades over the full ~26-year window each — consistent with
the source's own monthly-bar version having very few trades (12 since
1960), scaled down but still low-frequency even at half the original
periods.

## Decision: **REJECTED** (equity and crypto both)

Full-period Sharpe and max drawdown both fail for QQQ and SPY (worse for
SPY). The grid's edge was confined entirely to the low-vol tercile (16/16
pass) and diluted to nothing by mid/high-vol periods when combined into
the full-period backtest — the same regime-concentration pattern already
seen across many other momentum/trend strategies logged this cron
trigger. Crypto (BTC/ETH) rejected decisively, likely a data-length
limitation (only ~9 years vs the strategy's 110-294 trading-day lookback
periods) rather than a fundamental rejection of the underlying edge.

**Notes for future iterations:** the Coppock Curve's own historical track
record (monthly bars, 63 years, 100% win rate but modest annual return)
suggests it's fundamentally a low-frequency, buy-and-hold-adjacent signal
rather than a high-Sharpe active strategy — consistent with what this
daily-bar adaptation found (very few trades, Sharpe below 1.0). Not worth
re-testing with different period scalings; the underlying signal appears
to lack enough edge over buy-and-hold once max-drawdown is properly priced
in (the source's own reported 30.16% monthly-bar drawdown already exceeds
this repo's 0.25 MDD budget). Consider this indicator family closed unless
a future iteration wants to test it purely as a long-term regime filter
(not a standalone trading signal) alongside another indicator.
