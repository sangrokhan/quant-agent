# Sentiment Zone Oscillator (SZO, Walid Khalil) Contrarian Oversold-Bounce — REJECTED

## Hypothesis
Per TASC May 2012 Traders' Tips excerpt by Walid Khalil (creator of the
already-tested VZO/PZO): SZO = 100*(TEMA(daily up/down sign, window)/window).
Author's own disclosed thresholds: SZO<-7 = extreme pessimism (contrarian
buy), SZO>+7 = extreme optimism. Tested: long entry when SZO crosses below
`oversold_threshold`, exit on cross back above `exit_threshold=0.0` or a
max_hold_days time-stop.

Source: https://traders.com/documentation/feedbk_docs/2012/05/traderstips.html
(read via browser_exec after web_search's DDGS returned unrelated results
for this iteration's query).

## Grid test summary (Step 6)
`param_grid={"szo_window": [10,14,20], "oversold_threshold": [-5,-7,-10]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2016-01-01 to 2026-09-01, 108 total cells.

- pass_fraction: 0.046 (5/108)
- by_asset_class: equity 5/54 passed, crypto 0/54 passed
- by_vol_regime: low 0/36, mid 2/36, high 3/36
- Note: the source's own -7 threshold and the grid's -10 threshold are too
  extreme given this data's realized SZO distribution (1st percentile
  ~-6.9 on QQQ at window=14) — several grid cells at threshold=-10
  generated ZERO trades, producing degenerate "infinite Sharpe" false
  passes that were excluded from the follow-up single-config search below.

## Single-config validation (Step 7) — full-sample sweep at realistic thresholds

| Symbol | Best config | Full-sample Sharpe | Trades | Passed (>=1.0)? |
|---|---|---|---|---|
| QQQ | szo_window=14, oversold=-4 | 0.763 | 116 | No |
| SPY | szo_window=10, oversold=-4 | 0.769 | 251 | No |
| BTC/USDT | szo_window=10, oversold=-4 | 0.283 | — | No |
| ETH/USDT | szo_window=10, oversold=-4 | 0.184 | — | No |

No symbol clears Sharpe>=1.0 at any realistic (non-degenerate, >=10-trade)
threshold. MDD/TC/walk-forward/param-sensitivity not run given the
decisive full-sample Sharpe failure across the entire universe.

## Decision: REJECTED

Best full-sample Sharpe is 0.769 (SPY) — a moderate near-miss but clearly
below the 1.0 threshold across the realistic parameter space. Crypto fails
decisively (Sharpe 0.18-0.28), as expected for a pure up/down-day-count
sentiment measure with no obvious economic link to 24/7 crypto markets.

## Notes for future loops
- The author's own disclosed threshold (±7) is too extreme for this
  dataset/window combination and produces near-zero-trade degenerate
  results at longer windows; a future revisit could try SHORTER windows
  (5-8 days) which would make ±7 achievable more often, or add a trend
  filter (this repo's standard rescue pattern for oversold-bounce near
  misses) to see if it lifts SPY/QQQ's ~0.76-0.77 Sharpe past 1.0.
