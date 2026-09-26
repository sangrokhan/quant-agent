# TLT Month-End Bond Effect — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_tlt_month_end_bond_effect.py`
**Source:** https://algocloud.com/the-month-end-bond-effect-a-high-probability-tlt-seasonal-strategy/
(read via browser_exec, web_extract's ddgs backend cannot fetch this
domain), corroborated by a paywalled QuantifiedStrategies.com summary
claiming "the first seven trading days of the month produce strong
negative returns, while the rest of the month has doubled the returns of
buying and holding TLT."

## Hypothesis

Pure calendar rule: long TLT from the first trading day whose calendar
day-of-month >= 15 through month-end, flat otherwise. Source's own claimed
backtest: 12% max drawdown, "low volatility", consistent month-end
momentum capture (source itself notes the shown backtest excludes
transaction costs and part of the effect may be TLT's dividend-timing).
First TLT-specific calendar/seasonality strategy in this repo.

## Grid test summary (Step 6)

`entry_dom` in {10,15,20}, equity {TLT,IEF} + crypto {BTC/USDT,ETH/USDT}
(as sanity-check falsification symbols, no analogous "month-end" concept
for crypto's 24/7 market), vol_regime_splits=3. 36 cells.

- **pass_fraction: 0.056** (2/36) -- decisively weak
- **by_asset_class:** equity 2/18, crypto 0/18
- **by_vol_regime:** low 0/12, mid 1/12, high 1/12
- **best_cell:** entry_dom=20, IEF, high-vol, Sharpe 1.207 (isolated,
  not part of a broader passing pattern)
- **worst_cell:** entry_dom=15 (source's own disclosed default), TLT,
  low-vol, Sharpe -0.445

## Single-config validation (Step 7)

Config: `entry_dom=15` (source's own disclosed default). Full sample
2016-01-01 to 2026-09-01, TLT.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Trades |
|---|---|---|---|---|
| TLT | 0.215 **FAIL** (decisive) | 0.233 PASS | 0.070 **FAIL** | 128 |

`check_walk_forward` / `check_parameter_sensitivity` skipped given the
decisive Sharpe rejection at the grid stage plus the single-config
confirmation -- not worth the additional compute for a result this far
below threshold.

## Decision

**Rejected (all symbols).** TLT's full-sample Sharpe (0.215) is far below
the >=1.0 threshold and the grid pass fraction (5.6%) is one of the
weakest tested this cron trigger. The source's own claimed "12% max
drawdown, low volatility" result likely reflects either (a) a different
backtest window/data source than this repo's own TLT series, (b) the
un-modeled dividend-timing contribution the source itself flagged as a
caveat (TLT's ex-dividend date near month-start with a 5-7 day payout lag
could inflate the second-half-of-month return artificially in some data
feeds, an effect this repo's presumably-adjusted-close series should
already capture but may handle differently), or (c) survivorship/overfit
in the source's own claimed backtest. Not worth pursuing further this
iteration; the underlying "month-end bond effect" claim did not replicate
on this repo's own TLT data and validator stack.

Novelty: checked `strategies_index.jsonl` for "TLT seasonal"/"month-end
bond" -- 0 prior hits, confirmed non-duplicate (distinct from all prior
SPY/QQQ turn-of-month strategies and all prior SPY/TLT cross-asset ratio
strategies, neither of which trades TLT outright on its own calendar
cycle).
