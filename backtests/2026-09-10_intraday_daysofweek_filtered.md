# Backtest report: Intraday-only (open->close) hold, Friday-excluded

**Strategy file:** `strategies/2026-09-10_intraday_daysofweek_filtered.py`
**Hypothesis id:** see `knowledge_base/strategies_log.jsonl` entry for
2026-09-10 (intraday_daysofweek_filtered)

## Source

https://blog.harbourfronts.com/2026/04/21/volatility-risk-premium-and-clustering-intraday-vs-overnight-dynamics/
(Relative Value Arbitrage blog), summarizing Papagelis & Dotsis (2024),
"The Variance Risk Premium Over Trading and Non-Trading Periods" (SSRN
4954623). Key disclosed finding used here: the variance risk premium is
significantly negative overnight and positive/insignificant intraday, and
"going long volatility at the open and closing the position at the close
tends to be profitable on most days, except Fridays."

## Hypothesis

Long SPY/QQQ at the open, exit at the close (intraday-only, flat
overnight), excluding Fridays (flat all day Friday) since the source's own
day-of-week finding suggests Friday's intraday session doesn't share the
same risk-premium dynamics as Mon-Thu. Crypto included as a
falsification/contrast check (no discrete session boundary).

## Grid test (Step 6)

`param_grid={"exclude_weekday": [-1, 4]}` (× -1 = unconditional baseline
control arm, 4 = Friday-excluded per hypothesis) × `symbols={"equity":
["SPY","QQQ"], "crypto": ["BTC/USDT","ETH/USDT"]}` × `vol_regime_splits=3`
(low/mid/high realized-vol terciles), 2019-01-01 to 2026-09-01.

- **pass_fraction: 4/24 = 0.167** (min_sharpe=1.0, max_mdd=0.25 thresholds)
- **by_asset_class:** equity 4/12 passed, crypto 0/12 passed
- **by_vol_regime:** low 4/8 passed, mid 0/8, high 0/8
- **best_cell:** exclude_weekday=-1, SPY, low-vol regime, Sharpe 1.684
- **worst_cell:** exclude_weekday=-1, SPY, mid-vol regime, Sharpe -0.649
- The Friday-exclusion filter (`exclude_weekday=4`) did **not** improve
  Sharpe over the unconditional baseline (`exclude_weekday=-1`) in any
  cell — SPY low-vol: 1.429 vs 1.684 baseline; QQQ low-vol: 1.066 vs 1.068
  baseline (essentially identical, since Fridays are ~20% of trading days
  and removing them barely moves the aggregate). The strategy only clears
  the Sharpe bar in the low-vol tercile, and only for equities.

## Single-config validators (best-effort primary config: SPY, exclude_weekday=-1, full period)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.643 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.143 | ≤ 0.25 | PASS |
| Transaction-cost survival (2bps/trade, 1922 trades) | 0.156 net Sharpe | ≥ 0.5 | **FAIL** |
| Walk-forward | not run | — | skipped: `vbt.utils.splitting` API not available in installed vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`) — a pre-existing repo/environment issue, not specific to this strategy |
| Parameter sensitivity | derivable from grid (see above): exclude_weekday=-1 vs 4 basically indistinguishable per symbol/regime | — | not decisive either way |

## Decision

**Rejected.** Full-period Sharpe (0.643) is well below the 1.0 threshold
and collapses further after simple transaction-cost drag (net Sharpe
0.156). Only the low-vol tercile clears the bar, and only for the
unconditional baseline — the Friday-exclusion filter itself adds no
measurable edge over just holding intraday every day. Crypto (0/12 grid
cells) confirms the effect (such as it is) doesn't transfer to a 24/7
market without a discrete session boundary, consistent with the
strategy's own construction.
