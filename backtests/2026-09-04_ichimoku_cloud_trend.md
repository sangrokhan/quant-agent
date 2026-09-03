# Ichimoku Cloud Trend-Following (Tenkan/Kijun confirmed) — Backtest Report

**Hypothesis** (kb id 2026-09-04-034): price above the Ichimoku cloud (Kumo)
signals an established uptrend; combined with Tenkan-sen(9) > Kijun-sen(26)
bullish momentum confirmation, long-only entries should be more selective
than a raw above-cloud rule. Exit on close falling back inside/below the
cloud, or a bearish Tenkan/Kijun cross.

**Source**: https://www.quantifiedstrategies.com/ichimoku-strategy/ (web_search
succeeded first try; web_extract failed with the recurring DDGS
search-only-backend error, fell back to browser_exec). Source itself notes
Ichimoku reduces drawdowns but often fails to beat buy-and-hold across
assets — tested as confirmation/falsification given that documented prior.

## Grid test (Step 6)

`param_grid = {tenkan_window: [7,9], kijun_window: [22,26], senkou_b_window: [52]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 48 total cells.

- pass_fraction: **0.25** (12/48)
- by_asset_class: equity 12/24, crypto 0/24
- by_vol_regime: low 8/16, mid 4/16, **high 0/16** (the more typical low-vol
  concentration pattern seen across most accepted trend strategies in this
  repo, unlike the two immediately-preceding oscillator rejections -032/-033
  which concentrated in the high-vol tercile).
- best_cell: QQQ, tenkan_window=7, kijun_window=26, senkou_b_window=52, low-vol tercile, Sharpe 2.792

## Full-sample validators (Step 7) — grid-best config (tenkan_window=7, kijun_window=26, senkou_b_window=52)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | 1.028 (pass, thr 1.0) | **0.253 (fail, thr 0.25)** | 0.985 (pass, thr 0.5) | 32 |
| SPY | **0.961 (fail, thr 1.0)** | 0.125 (pass) | 0.902 (pass) | 34 |

Walk-forward (QQQ, 4 manual date-slices, vectorbt splitting API bug
workaround as used throughout this repo): 3/4 splits positive Sharpe = 0.75
pass fraction, **passes** the 0.75 threshold exactly.

Parameter sensitivity (tenkan_window in {7,9,11}, kijun_window=26 fixed, QQQ):
relative std 0.066 vs 0.5 ceiling — **passes** comfortably.

## Decision: REJECTED (near-miss on both tested equity symbols)

QQQ passes Sharpe, transaction-cost survival, walk-forward, and parameter
sensitivity, but narrowly fails max drawdown (25.3% vs the 25% ceiling — a
1.3 percentage-point overshoot, one of the closest MDD near-misses in this
log). SPY passes every validator except Sharpe (0.961 vs 1.0, a 3.9%
shortfall). Neither symbol clears all validators simultaneously at the
grid-optimal shared config, so this does not meet the accept bar despite
being one of the strongest showings among recent oscillator/indicator
strategies (grid pass_fraction 0.25, typical low-vol-tercile concentration,
strong walk-forward and parameter-sensitivity results). Crypto rejected
decisively (0/24 grid cells). A future loop could revisit with a slightly
tighter kijun_window or an added ATR-based position-size cap specifically
to shave QQQ's MDD below 25% without materially hurting Sharpe.
