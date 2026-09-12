# BTC/ETH/SOL 3-way relative-strength rotation + absolute-momentum cash gate

**Strategy file:** `strategies/2026-09-13_btc_eth_sol_3way_rotation_absgate.py`
**Hypothesis id:** 2026-09-13-036

## Source / rationale

Direct follow-up to 2026-09-13-035 (plain always-invested 3-way BTC/ETH/SOL
rotation, decisively rejected: best Sharpe 0.339, MDD 79-95%). Adds Gary
Antonacci Dual-Momentum-style absolute-momentum cash gate (already tested
elsewhere in this repo, e.g. 2026-09-04-097) on top of the relative-
strength leader selection: hold the leader only if its own trailing
momentum is positive, otherwise go to cash.

## Full-sample parameter sweep

`momentum_window` in [7,14,21,30,45,60,90] x `min_hold_days` in [1,3,5,10],
28 combos, full 2019-2026 sample:

| momentum_window | min_hold_days | Sharpe | Max DD |
|---|---|---|---|
| 21 | 3 | 0.352 (best) | 0.623 |
| 21 | 1 | 0.340 | 0.631 |
| 21 | 5 | 0.322 | 0.694 |
| 60 | 1 | 0.279 | 0.614 (lowest MDD) |

The cash gate modestly improves max drawdown vs. the always-invested
version (best-Sharpe-combo MDD drops from 0.796 to 0.623) but Sharpe
remains essentially unchanged (0.339 -> 0.352) and nowhere near the 1.0
threshold. The absolute-momentum gate reduces exposure during broad
market-wide downturns (when ALL three assets have negative momentum) but
does nothing when the "leader" has barely-positive momentum while still
being in a severe, ongoing drawdown relative to its own recent peak --
which is the more common failure mode for a rotation that chases
already-hot assets.

## Outcome

**Rejected -- decisive.** The cash gate is a real but insufficient fix;
Sharpe stays far below threshold and MDD, while improved, still fails
decisively (62% vs. 25% cap). No further tuning attempted -- the
fundamental issue (chasing single-asset momentum leaders in a highly
correlated, high-beta asset class) is not resolved by either a cash gate
or turnover reduction.
