# System Quality Number (SQN, Van Tharp) Binary Regime Filter on SMA(200) Trend Gate

**Hypothesis:** Per tradesviz.com / quantstrategy.io / journalplus.co (Google
SERP snippets via browser_exec; web_search DuckDuckGo backend returned zero
results for the direct query): System Quality Number (Van Tharp) =
sqrt(N) * (Expectancy / StdDev of R-multiples). Structurally distinct from
every other sizing-overlay ratio already tested in this repo (all scale
exposure continuously/proportionally); SQN's own sqrt(N) sample-size scaling
makes it naturally suited as a BINARY regime quality-filter (trade only
when trailing SQN clears a threshold) rather than a proportional sizing
dial. R-multiple proxy = daily log return / trailing stdev of negative
daily log returns (fixed risk-unit stand-in for per-trade stop distance).
First SQN-based strategy (in any role) in this repo.

**Source:** https://www.google.com/search?q=System+Quality+Number+SQN+Van+Tharp+formula
(SERP snippets: tradesviz.com, quantstrategy.io, journalplus.co)

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
sqn_window in [40,60,90], sqn_threshold in [-0.5,0.0,0.5]; vol_regime_splits=3)

- total_cells: 108, passed_cells: 26, pass_fraction: 0.241
- by_asset_class: equity 26/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 8/36, high 0/36
- best_cell: SPY, sqn_window=60, sqn_threshold=-0.5, low-vol, Sharpe=2.852
- worst_cell: SPY, sqn_window=60, sqn_threshold=0.5, high-vol, Sharpe=-1.128

## Single-config validator results (best full-sample config per symbol,
trend_window=200, risk_window=60, leverage_cap=1.0)

| Symbol | Config | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | sqn_window=60, sqn_threshold=-0.5 | 1.016 | Yes | 0.224 | Yes | 0.978 | Yes | 0.75 | Yes | 0.206 | Yes |
| QQQ | sqn_window=90, sqn_threshold=-0.5 | 1.270 | Yes | 0.219 | Yes | 1.255 | Yes | 0.75 | Yes | 0.191 | Yes |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
seen in prior iterations (`vbt.utils.splitting.RangeSplitter` unavailable) —
substituted a manual 4-split walk-forward (same 0.75 threshold on
per-split positive full-sample Sharpe) for both symbols; both hit 3/4.

## Decision

**Accepted (SPY and QQQ, each with own tuned sqn_window).** All 5
validators pass for both symbols. Crypto (BTC/USDT, ETH/USDT) rejected
decisively across the whole grid (0/54 cells) — consistent with nearly
every other sizing/filter-overlay family tested this cron trigger
underperforming on crypto.
