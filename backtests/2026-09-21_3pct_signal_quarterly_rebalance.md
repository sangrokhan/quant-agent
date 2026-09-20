# Jason Kelly's "3% Signal" Quarterly Rebalancing — QQQ Backtest Report

**Date:** 2026-09-21 (cron trigger, iteration 8)
**Strategy file:** `strategies/2026-09-21_3pct_signal_quarterly_rebalance.py`
**Hypothesis source:** https://www.cxoadvisory.com/technical-trading/long-term-tests-of-simple-x-rules/
(rule fully disclosed, numeric backtest results paywalled; via Google SERP
browsing, web_search DDGS backend TLS-erroring on this iteration's queries)

## Hypothesis

Jason Kelly's "3% Signal" quarterly rebalancing rule (from *The 3% Signal:
The Investing Technique that Will Change Your Life*), summarized by CXO
Advisory: start with an X0% stock / (100-X0)% cash allocation. Each quarter,
compare the stock position's actual growth to a fixed target growth rate X%.
If it grew MORE than X%, sell the excess back to cash. If it grew LESS than
X% (including a decline), buy the shortfall from cash (systematic dip-
buying). Adapted here to a single-asset (QQQ/SPY/crypto) contract as a
CONTINUOUS stock-weight sizing rule (weight in [0,1]), following this
repo's established continuous-sizing pattern. This is a genuinely new
indicator family for this repo: a target-growth-rate rebalancing rule,
distinct from every moving-average/oscillator/pattern/seasonal strategy
tested so far.

## Grid test summary (initial_stock_pct x quarterly_target_pct x symbol x vol-regime)

- Grid: `initial_stock_pct` in {0.6, 0.8}, `quarterly_target_pct` in
  {0.02, 0.03, 0.04}; symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto);
  3 vol-regime terciles.
- **Total cells:** 72, **Passed:** 30, **pass_fraction = 0.417** (one of
  the strongest pass fractions this cron trigger).
- By asset class: equity 24/36; crypto 6/36.
- By vol regime: low 12/24, mid 18/24, high 0/24 -- fails outright in
  high-vol tercile (like most strategies tested this cron trigger), but
  actually performs BEST in the mid-vol tercile rather than low-vol, an
  unusual pattern suggesting the dip-buying/profit-taking mechanism
  benefits from moderate volatility (enough swings to trigger rebalances
  profitably, but not so much that quarterly rebalancing can't keep up).
- QQQ full-sample average Sharpe across ALL 6 param combos: 1.55-1.60 --
  remarkably stable and insensitive to both `initial_stock_pct` and
  `quarterly_target_pct` choices.

## Single-config validation, QQQ, full sample 2016-2026 (initial_stock_pct=0.8, quarterly_target_pct=0.03, source's own defaults)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.154 | 1.0 |
| Max drawdown | ✅ (marginal) | 0.244 | 0.25 |
| Transaction cost survival (10bps/trade, 40 rebalances) | ✅ | 1.121 net Sharpe | 0.5 |
| Walk-forward (4 splits) | ✅ | 1.0 pass fraction | 0.75 |
| Parameter sensitivity (6-cell QQQ grid) | ✅ | 0.012 relative std | 0.5 |

All validators passed using the source's own disclosed default parameters
(80% initial stock allocation, 3% quarterly growth target) -- no retuning
needed. Parameter sensitivity is exceptionally low (0.012), indicating this
strategy's edge (if real) is very robust to the exact target-growth-rate and
initial-allocation choices.

## Decision: ACCEPT (QQQ only, default params initial_stock_pct=0.8/quarterly_target_pct=0.03)

Scope: QQQ, low/mid vol regimes; fails outright in high-vol regime.
Max drawdown is only marginally under threshold (0.244 vs 0.25 limit) --
worth flagging as a near-limit pass for future loops considering
retuning/tightening this strategy further. Crypto shows some pass fraction
(6/36) but not enough to extend scope there without further tuning.
