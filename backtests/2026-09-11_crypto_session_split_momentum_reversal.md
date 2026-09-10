# Backtest report: Crypto session-split (daytime/overnight) lagged
# momentum/reversal (Wu & Pinsky 2026)

**Strategy file:** `strategies/2026-09-11_crypto_session_split_momentum_reversal.py`
**Hypothesis source:** Wu, Z. & Pinsky, E. (2026), "On the Performance of
Lagged Momentum and Reversal Strategies Across Daytime and Overnight
Sessions in Bitcoin and Ethereum Cryptocurrencies", J. Risk Financ. Manag.
19(9), 692. https://www.mdpi.com/1911-8074/19/9/692 (visited this iteration
via browser_exec fallback -- web_search returned only listing snippets, the
full abstract/methodology required rendering the actual MDPI page).

## Hypothesis

Splitting the 24h crypto trading day into two complementary 12h sessions and
applying a conditional momentum/reversal rule (current session's position =
sign or inverse-sign of the SAME session type's immediately preceding
realized return) reveals return predictability not visible in daily
aggregated returns. The paper's own full-sample-optimal rules: BTC =
Reversal/Reversal starting the "day" session at 08:00 UTC; ETH = Long
(night)/Reversal (day) starting the "night" session at 05:00 UTC. The
paper's own out-of-sample chronological holdout (train 2016-2020, test
2021-2025) found the ETH rule persists but the BTC rule does NOT (BTC
underperforms buy-and-hold out-of-sample), and neither full-sample result is
statistically significant after a Superior Predictive Ability test
accounting for the 300-combination search space -- i.e. the source paper
itself is candid that these are NOT proven abnormal-profit opportunities.
This iteration tests both the paper's own selected BTC and ETH rules on this
repo's independent Binance-hourly data (2018-2026, distinct exchange/period
from the paper's Kraken 2016-2025 sample) as a genuine out-of-sample
replication check.

## Grid test summary (Step 6)

`param_grid={"session_start_hour": [5,8], "night_rule": ["long","reversal","cash"], "day_rule": ["reversal","momentum"]}`,
`symbols={"equity": ["QQQ"] (falsification -- no hourly loader for equity, expected no-op), "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 108 total cells, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.0 (0/108)** -- decisive rejection across every asset
  class and vol regime.
- by_asset_class: equity 0/36 (expected -- daily-bar loader returns an
  all-flat no-op series, `check_sharpe_ratio` correctly fails a zero-return
  series), crypto 0/72.
- by_vol_regime: low 0/36, mid 0/36, high 0/36.
- best_cell: BTC/USDT, session_start_hour=8/night_rule=reversal/day_rule=reversal
  (the paper's own BTC-optimal rule), high-vol tercile only, Sharpe=1.973 --
  but this is a single vol-regime slice, not the full-sample result (see
  below), and MDD failed on that same cell.

## Single-config validation (Step 7)

Full-sample (2018-01-01 to 2026-09-01) replication of the paper's own two
selected rules, on this repo's independent Binance-hourly data:

| Rule | Symbol | Sharpe | MDD |
|---|---|---|---|
| Paper's ETH rule (session_start_hour=5, night=long, day=reversal) | ETH/USDT | 0.451 | 0.959 |
| Paper's BTC rule (session_start_hour=8, night=reversal, day=reversal) | BTC/USDT | 0.770 | 0.592 |

- `check_sharpe_ratio`: **FAILED** for both (0.451 and 0.770, both < 1.0
  threshold).
- `check_max_drawdown`: **FAILED decisively** for both (0.959 and 0.592, vs
  0.25 budget) -- the always-long-or-short (never cash for most bars)
  construction means these rules carry continuous directional exposure with
  no risk-off mechanism, unlike this repo's typical trend/regime-gated
  strategies.
- Walk-forward / parameter-sensitivity: not run given the decisive
  full-sample Sharpe/MDD failure on both of the paper's own hand-picked
  rules (workload=max, but no incremental value running the full suite on
  configs already failing the two cheapest/most fundamental gates).

## Decision: REJECTED

Both of the paper's own selected rules (ETH and BTC) fail full-sample Sharpe
and max-drawdown decisively on this repo's independent Binance hourly data
(2018-2026), consistent with the source paper's own candid conclusion that
these full-sample-optimal rules are the product of an unadjusted-for-
multiple-testing search over 300 combinations and do not survive the
authors' own out-of-sample holdout (for BTC) or SPA statistical significance
test (for either asset). This iteration's independent replication on a
different exchange/period reinforces the paper's own skepticism rather than
finding a fresh testable edge.

## Notes for future loops

- The extreme MDD (up to 0.96) confirms these rules are near-constantly
  directionally exposed (long or short every session, rarely cash) --
  fundamentally different risk profile from this repo's trend/regime-gated
  family. A future loop revisiting this idea might explore whether ADDING a
  volatility-regime or trend-confirmation gate (this repo's standard fix
  pattern for near-misses) rescues the Sharpe without requiring the full
  always-in-market construction, though given the paper's own SPA-test
  failure this may not be worth further iteration budget.
- This confirms (again) that session/hour-of-day effects in crypto are
  fragile and highly search-space-dependent, consistent with this repo's
  separate finding (2026-09-XX "Hour-of-Day Effect" rejection) that
  hour-of-day patterns change dramatically year to year.
