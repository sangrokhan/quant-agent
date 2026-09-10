# 2026-09-11 Monthly-Decision Golden Cross (SMA50/SMA200) Regime

## Hypothesis
Per SetupAlpha's "This Bitcoin Indicator Turned $10,000 Into $4.7 Million"
(Sep 6 2026, https://setup4alpha.substack.com/p/bitcoin-indicators-ranked,
visited this iteration): source's disclosed methodology evaluates a
regime rule ONCE PER MONTH at month-end and holds verbatim for the entire
following month (rather than continuously re-evaluating daily). Source's
disclosed free-tier example, Golden Cross (SMA50>SMA200), ranked #9/17 on
Bitcoin with only 18 switches over 11 years, reaching $2,136,221 from
$10,000 vs BTC buy-and-hold's $3,442,843 but with shallower drawdown
(64.7% vs 83.4%). This repo has tested SMA50/200 golden-cross before but
always with daily continuous re-evaluation; this iteration isolates the
monthly-decide/hold-for-month mechanic as the new, testable variable.

Source: https://setup4alpha.substack.com/p/bitcoin-indicators-ranked (visited this iteration)

## Grid summary (run_strategy_grid, param_grid={fast_sma_window:[20,50,100], slow_sma_window:[150,200,250]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 108, passed_cells: 28, pass_fraction: 0.259
- by_asset_class: equity 28/54, crypto 0/54 (decisively rejected on its own native domain, contrary to source's claim -- see note below)
- by_vol_regime: low 18/36, mid 10/36, high 0/36
- best_cell: QQQ, fast_sma_window=20, slow_sma_window=250, low-vol regime, Sharpe 2.41

## Single-config validation (full sample)

| Config | Symbol | Sharpe | MDD | TC-adj Sharpe (10bps, N trades) |
|---|---|---|---|---|
| fast=50, slow=200 (classic) | QQQ | 0.797 | 0.286 | 0.787 (33 trades) |
| fast=50, slow=200 (classic) | SPY | 0.709 | 0.354 | 0.700 (23 trades) |
| fast=20, slow=250 (grid best) | QQQ | 0.876 | 0.297 | 0.867 (29 trades) |
| fast=20, slow=250 (grid best) | SPY | 0.772 | 0.341 | 0.760 (29 trades) |

## Decision: REJECT

Full-sample Sharpe (0.71-0.88) fails the >=1.0 threshold across all
tested configs, AND max drawdown (0.29-0.39) also breaches the 0.25
threshold on both QQQ and SPY -- a double failure, not a near-miss.
Transaction-cost survival is fine (low trade count from monthly-decision
cadence, as the source's own methodology claims), but that low turnover
doesn't compensate for the underlying signal's weak full-sample
risk-adjusted return on this repo's equity universe. Crypto (BTC/ETH,
the source's OWN native domain where it reportedly reached $4.7M) is
rejected decisively here (0/54) -- likely explained by the source's
sample only spanning 2015-2026 with BTC's specific historical bull
cycles, while this repo's grid start date and possibly different
BTC/USDT vs BTC-USD data source produce a different result; a future
iteration could retest with the source's exact 2015-09-30 start date
isolated to BTC only, in case the equity generalization is what fails,
not the crypto-native rule itself.
