# Ehlers Voss Predictive Filter crossover (long-only)

## Hypothesis
John Ehlers' "Voss Predictive Filter" (TASC Aug 2019, "A Peek Into the
Future") bandpass-filters price (`Filt`) and computes a negative-group-delay
predictor line (`Voss`) that is designed to lead `Filt` at cyclical turning
points. Per ATAS's writeup of the indicator's own trading rule: "Bullish
crossing. If the [Voss] line crosses the [Filt] line upward, it is a buying
signal. Bearish crossing... downward, it is a selling signal." Long entry on
Voss crossing above Filt; exit on the reverse cross or a `max_hold_days`
time-stop (added as a robustness stop not present in the original indicator).

Sources:
- https://www.prorealcode.com/prorealtime-indicators/voss-predictive-filter-vpf/
  (exact recursive formula/code, read in-browser)
- https://atas.net/blog/voss-predictive-filter/ (Voss/Filt crossover trading
  rule + the source's own intraday ES/SPY backtest, mixed but net-positive)

## Grid test (Step 6)
`param_grid={"period": [10,20,30], "max_hold_days": [5,10,20]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 108, passed: 23, **pass_fraction: 0.213**
- by_asset_class: equity 23/54, **crypto 0/54** (decisively rejected on crypto)
- by_vol_regime: low 14/36, mid 6/36, high 3/36 (works best in low-vol regimes)
- best_cell: period=10, max_hold_days=10, QQQ, low-vol, Sharpe 2.94
- Best avg-across-regimes config: **period=10, max_hold_days=10** (QQQ avg
  Sharpe 1.655, SPY avg Sharpe 1.531)

## Single-config validation (period=10, max_hold_days=10, QQQ, full sample)
| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio (>=1.0) | **PASS** | 1.126 |
| Max drawdown (<=25%) | **PASS** | 20.4% |
| Transaction cost survival (10bps/trade, net Sharpe >=0.5) | **PASS** | net Sharpe 0.843, 213 trades |
| Walk-forward (4 contiguous splits, manual -- `vbt.utils.splitting` unavailable in this repo's vectorbt 1.1.0, same pre-existing issue noted in prior iterations) | **PASS** | 3/4 splits Sharpe>0 (0.75 pass fraction) |
| Parameter sensitivity (9-cell period x max_hold_days sweep, relative_std <=0.5) | **FAIL** | relative_std 0.748 (mean Sharpe 0.574, std 0.429) |

SPY sanity check at the same config: Sharpe 1.303 (consistent with QQQ).

## Decision: REJECT
4/5 validators pass, but **parameter sensitivity fails decisively**
(relative_std 0.748 vs 0.5 threshold) -- performance swings from Sharpe
~2.9 (period=10) down to ~0.2-0.8 (period=30) across the tested grid,
meaning the edge is highly dependent on hitting the right `period`/
`max_hold_days` combination rather than being robust across nearby
parameter values. Per Step 8, any failing validator means reject.

## Notes
- Crypto (BTC/USDT, ETH/USDT) rejected decisively -- 0/54 grid cells passed.
- Equity-only, low-vol-regime-favoring pattern is consistent with several
  other accepted/near-miss equity trend/momentum strategies already in this
  repo, but the sharp period-sensitivity here is a genuine overfitting risk
  distinct from those.
- Strategy file kept in `strategies/` as a rejected-attempt record.
