# 2026-09-27 GTAA Dual-Momentum with IEF Bond-Proxy Fallback

**Hypothesis:** Direct follow-up to rejected 2026-09-11-041 (GTAA 5-asset
SPY/EFA/EEM/GLD/TLT dual-momentum, absolute-momentum CASH gate), whose own
`notes` field explicitly suggested trying an IEF bond-proxy fallback
instead of parking in 0%-yielding cash when the absolute-momentum gate
fails, mirroring the accepted GEM/IEF dual-momentum result
(2026-09-07-023). Source: Quantpedia "Active Dual Momentum GTAA Strategy"
(22 May 2026), https://quantpedia.com/active-dual-momentum-gtaa-strategy/
(re-visited this iteration; methodology unchanged from 2026-09-11-041,
only the "cash" leg replaced with IEF).

Basket: SPY/EFA/EEM/GLD/TLT, ranked every `rebalance_days` trading days by
trailing `lookback_days` rate-of-change. Primary asset held only if
top-ranked in basket AND its own trailing RoC is positive; IEF held
otherwise (instead of cash).

## Grid test (Step 6)

`param_grid={lookback_days:[63,126,252], rebalance_days:[5,21]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` -> total_cells=72

- **passed_cells: 6/72 (pass_fraction=0.083)**
- by_asset_class: equity 2/36, crypto 4/36
- by_vol_regime: low 6/24, mid 0/24, **high 0/24**
- best_cell: crypto ETH/USDT lookback=63/rebalance=21, mid-vol, Sharpe 1.61
- worst_cell: crypto BTC/USDT lookback=126/rebalance=21, high-vol, Sharpe -0.92
- Equity passing cells: QQQ (lookback=126, rebalance=21, low-vol, Sharpe
  1.04, MDD 12.5%), SPY (lookback=63, rebalance=21, low-vol, Sharpe 1.02,
  MDD 12.9%) — both **only in the low-vol tercile**.

IEF-fallback did NOT rescue the strategy the way it did for GEM/IEF
(2026-09-07-023): pass_fraction actually got slightly WORSE than the cash
variant (0.083 vs 0.139 for 2026-09-11-041), and remains entirely
concentrated in the low-vol regime slice with zero pass in mid/high vol —
the fundamental problem (basket relative-momentum ranking is noisy/whipsawy
outside calm regimes) isn't fixed by swapping the flat leg for a bond ETF.

## Full-period validators (Step 7) — QQQ, lookback_days=126, rebalance_days=21

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.066 | >= 1.0 |
| Max drawdown | **FAIL** | 51.9% | <= 25% |
| Transaction cost survival | **FAIL** | net Sharpe 0.050 | >= 0.5 |
| Walk-forward (4-split, manual RangeSplitter replacement) | PASS | 0.75 pass fraction | >= 0.75 |
| Parameter sensitivity | **FAIL** | relative std 1.63 | <= 0.5 |

(`check_walk_forward`'s `vbt.utils.splitting.RangeSplitter` is unavailable
in the installed vectorbt version — same known issue documented in
`backtests/2026-09-27_donchian_shannon_entropy_regime_gate.md` — replicated
manually with the same n_splits-chunk / per-split positive-Sharpe-fraction
contract.)

## Decision: REJECTED

4 of 5 validators fail decisively on the full sample; the grid's 6 passing
cells are a narrow low-vol-regime/short-horizon artifact, not a broadly
robust edge. The strategy shows extreme parameter sensitivity (relative
std 1.63 >> 0.5 threshold) — small lookback/rebalance changes flip Sharpe
from ~1.6 to negative.
