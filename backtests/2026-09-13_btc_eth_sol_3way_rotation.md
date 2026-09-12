# BTC/ETH/SOL 3-way relative-strength rotation

**Strategy file:** `strategies/2026-09-13_btc_eth_sol_3way_rotation.py`
**Hypothesis id:** 2026-09-13-035

## Source

Lukra.ai's "Crypto Rotation Strategies: How AI Allocates Across BTC, ETH,
and SOL" (https://lukra.ai/blog/crypto-rotation-strategy-btc-eth-sol),
read this iteration via browser_exec -- `web_search` (DDGS backend)
returned errors/no results on the queries attempted this iteration, so the
Bing SERP fallback was used throughout.

Disclosed mechanism (qualitative, no exact numeric formula available):
"The model measures 7-day, 14-day, and 30-day relative momentum for each
asset. When one asset is dramatically outperforming peers with
strengthening momentum, it receives higher allocation." Time-series-
adapted here (no on-chain/sentiment data available to this repo's
OHLCV-only loaders) as: hold whichever of BTC/USDT, ETH/USDT, SOL/USDT has
the highest trailing `momentum_window`-day return, always fully invested
in exactly one of the three.

First 3-way crypto rotation (and first rotation including SOL) tested in
this repo -- all prior rotation entries (2026-09-04-083/108, 2026-09-08-084)
are pairwise BTC/ETH only.

## Full-sample parameter sweep

Rather than running the full grid harness, a direct full-sample sweep
(`momentum_window` in [7,14,21,30,60] x `min_hold_days` in [1,3,5], 15
combos, 2019-2026 BTC/USDT primary window) was run first since results
were decisively negative across the entire grid:

| momentum_window | min_hold_days | Sharpe | Max DD |
|---|---|---|---|
| 7 | 1 | 0.216 | 0.914 |
| 14 | 1 | 0.274 | 0.938 |
| 21 | 3 | 0.339 (best) | 0.796 |
| 30 | 1 | 0.216 | 0.864 |
| 60 | 5 | 0.270 | 0.832 |

Best Sharpe across all 15 combos: 0.339 (momentum_window=21,
min_hold_days=3) -- nowhere close to the 1.0 threshold. Max drawdown is
catastrophic across every combo (79-95%), driven by the strategy being
ALWAYS fully invested in the single most-recently-hot asset with no cash
position and no diversification -- when the current "leader" itself
crashes (e.g. holding SOL into its 2022 -90% collapse because SOL had the
best trailing momentum right before the top), the rotation offers no
protection.

## Outcome

**Rejected -- decisive full-sample failure**, no further grid/validator
testing warranted given results are an order of magnitude below threshold
across the entire parameter sweep. The core issue is structural (always-
invested, no cash/diversification, chases whichever asset already
outperformed) rather than a parameterization artifact.
