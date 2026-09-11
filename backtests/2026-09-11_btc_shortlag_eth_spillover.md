# Backtest Report: BTC Short-Lag Lead-Lag Momentum Spillover into ETH

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_btc_shortlag_eth_spillover.py`
**Sources:**
- https://www.businessinsider.com/lead-lag-strategy-explained-crypto-investing-advice-digital-assets-token-02021-7
  ("How to Use 'Lead-Lag Strategy' to Profit in Crypto, Trader Explains",
  Business Insider, read via browser_exec after web_search backend failure
  for the query "lead lag bitcoin altcoin momentum spillover trading
  strategy rules" — Google SERP was used to locate this and related URLs
  such as "A seesaw effect in the cryptocurrency market" and "Bitcoin and
  Main Altcoins: Causality and Trading Strategies").
- Practitioner rule disclosed in that article (Martin Cheung, Pulsar
  Trading Capital): "if you see bitcoin is up 10% today and ether is doing
  nothing... if you believe in the lead-lag strategy, then you would buy
  ether and expect 10% gain."

## Hypothesis

BTC's price moves propagate into ETH with a SHORT lag (1-3 days), distinct
from the already-rejected 20-40 day TLT-neighbor momentum gate
(2026-09-08-143) and all prior ETH/BTC ratio-based strategies
(2026-09-04-083, 2026-09-04-108, 2026-09-08-084, all rejected via different
mechanisms — spread mean-reversion, always-invested rotation, ratio
breakout). This strategy instead: goes long ETH when BTC's trailing
`btc_lag_window`-day (1/2/3) return exceeds a threshold, using no ETH price
history in the signal at all (pure spillover, same isolation principle as
2026-09-08-143).

## Grid test summary (Step 6)

`param_grid={"btc_lag_window": [1,2,3], "btc_return_threshold": [0.0, 0.01]}`,
`symbols={"crypto": ["ETH/USDT"]}` (equity not applicable — no BTC-equity
lead-lag mechanism claimed by the source), `vol_regime_splits=3`,
2019-01-01 to 2026-09-01.

- **total_cells:** 18, **passed:** 0, **pass_fraction: 0.0**
- **by_vol_regime:** low 0/6, mid 0/6, high 0/6 — fails uniformly across all
  volatility regimes, not concentrated in one slice
- **best_cell:** ETH/USDT, btc_lag_window=3, btc_return_threshold=0.01,
  mid-vol regime, Sharpe 0.81 (still below the 1.0 grid-cell threshold)
- **worst_cell:** ETH/USDT, btc_lag_window=1, btc_return_threshold=0.0,
  high-vol regime, Sharpe 0.27

## Single-config validation (Step 7): btc_lag_window=3, btc_return_threshold=0.01 (grid's best cell)

| Validator | ETH/USDT | Threshold |
|---|---|---|
| Sharpe ratio | 0.983 (**FAIL**, just under) | >= 1.0 |
| Max drawdown | 0.503 (**FAIL**, catastrophic) | <= 0.25 |
| Trades | 760 over ~7.7yr | — |

Skipped walk-forward/parameter-sensitivity/TC-survival given the grid
already shows 0/18 pass and the full-sample confirmation fails decisively
on both Sharpe and MDD (suggested_workload=normal, but no value in
running the remaining validator suite on a config that already fails the
two primary gates).

## Decision: REJECT

Grid pass_fraction is 0.0 — no parameter combination across
`btc_lag_window` in {1,2,3} or `btc_return_threshold` in {0.0, 0.01}
achieves Sharpe >= 1.0 with MDD <= 0.25 in ANY volatility regime tercile,
not even the best cell. The full-sample confirmation on the single
best-performing grid cell still fails both Sharpe (0.983, just under
threshold) and max drawdown (50.3%, roughly double the allowed threshold —
this is a long-only always-latched-to-BTC-momentum exposure with no exit
mechanism beyond the daily threshold flip, so it fully inherits ETH's raw
downside volatility during BTC-momentum-positive drawdown periods, similar
in kind to why 2026-09-04-108's always-invested rotation failed on MDD).

This closes out the "short-horizon BTC->ETH lead-lag" angle as a naive
long/flat threshold rule — the practitioner's qualitative description
("buy ether, expect similar gain") does not translate into a durable
tradeable daily-bar edge at this simple specification. A future iteration
could try: (a) adding an exit/stop mechanism instead of the bare threshold
flip (the MDD failure mode is common to nearly every "always exposed
during a condition" crypto strategy tested in this repo), or (b) testing
at higher-frequency (hourly) bars where the lead-lag literature's effect
sizes are typically measured, rather than daily bars — this repo's crypto
loader would need an hourly interval test to explore that.
