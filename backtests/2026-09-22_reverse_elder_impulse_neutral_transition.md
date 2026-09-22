# Reverse Elder Impulse System — Neutral-Transition Trigger (2026-09-22)

## Hypothesis

Per Tradinformed's "How to Trade the S&P500 Using The Impulse Indicator"
(https://www.tradinformed.com/how-to-trade-the-sp500-using-the-impulse-indicator/,
read via browser_exec this iteration — web_search's DDGS backend intermittently
TLS-erroring/no-results on several queries this iteration), the source's own
20-year SPY backtest (1996-2016) found:

- **Standard** Elder Impulse rule (long when Impulse turns Positive from
  Neutral, exit on return to Neutral): net **-$81,551**, profit factor 0.73,
  36% win rate, 85% max drawdown.
- **Reversed** rule (long when Impulse turns Negative from Neutral instead):
  net **+$350,922**, profit factor 1.6, 64% win rate, 20% max drawdown.

This repo has 3 prior Elder Impulse entries (2026-09-04-064 green-bar-long,
2026-09-04-125 HTF-filtered variant, 2026-09-14-133 continuous-sizing dial),
all using the standard (bullish=long) direction with a persistent-state
color trigger. This is the first REVERSED-direction test, using a distinct
**Neutral->Negative transition** trigger (per the source's exact rule) rather
than the repo's usual persistent-color-state convention.

## Grid summary (Step 6)

Grid: `ema_window` in {13, 21} x `trend_window` in {0, 100} x QQQ/SPY/BTC-USDT/ETH-USDT
x 3 vol regimes (low/mid/high) = 48 cells.

- `pass_fraction` = 0.292 (14/48)
- `by_asset_class`: equity 12/24, crypto 2/24
- `by_vol_regime`: low 8/16, mid 2/16, high 4/16
- `best_cell`: BTC/USDT, ema_window=21/trend_window=100, high-vol regime, Sharpe 2.09 (isolated cell, not broadly consistent)
- Best **equity** full-sample-average config: SPY ema_window=13/trend_window=0 (avg Sharpe 1.41 across regimes); QQQ ema_window=21/trend_window=0 (avg Sharpe 1.04)
- Primary config selected for single-config validation: `ema_window=13, trend_window=0` (best average on SPY, second-best full-sample class overall; trend_window=0 outperformed the SMA(100) gate at every equity cell tested — the reversal/contrarian mechanic works better ungated)

## Single-config validation (ema_window=13, trend_window=0)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 0.803 **FAIL** (<1.0) | 0.974 **FAIL** (near-miss, <1.0) |
| Max drawdown | 0.191 **PASS** (<0.25) | 0.187 **PASS** (<0.25) |
| TC-survival (10bps/trade) | 0.443 **FAIL** (<0.5, 289 trades) | 0.498 **FAIL** (near-miss, <0.5, 293 trades) |
| Walk-forward (4 splits) | 1.0 **PASS** | 1.0 **PASS** |
| Parameter sensitivity | 0.486 **PASS** (<0.5) | 0.453 **PASS** (<0.5) |

## Decision: REJECT

3/5 validators pass on both symbols (MDD, walk-forward, param-sensitivity),
but Sharpe and TC-survival both fail (SPY Sharpe is a near-miss at 0.974,
2.6% short). The trade count (~290 trades over 7.75yr, roughly weekly) is
high enough that the 10bps/trade cost assumption erodes the edge below the
TC-survival threshold on both symbols. The `trend_window=100` SMA gate
variant was tested in the grid and made things *worse* (lower avg Sharpe on
every equity cell), so it isn't a viable rescue lever here — the fix would
need to reduce trade frequency (e.g. min-hold gate) rather than add a trend
filter, unlike most of this cron trigger's other successful SMA-trend-gate
rescues.

Source: https://www.tradinformed.com/how-to-trade-the-sp500-using-the-impulse-indicator/
