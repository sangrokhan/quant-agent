# Backtest Report: IBD-style Weighted RS Composite Momentum (2026-09-23)

**Strategy file:** `strategies/2026-09-23_ibd_weighted_rs_composite_momentum.py`
**Knowledge base id:** 2026-09-23-138
**Status: REJECTED** (kept in `strategies/` as a documented rejected attempt, not a live strategy)

## Hypothesis

IBD's classic RS Rating formula weights the most recent quarter (3-month,
63 trading days) at 40% and each of the prior three quarters (6/9/12-month,
126/189/252 trading days) at 20%. Sources (all visited this iteration via
`browser_exec` Google SERP fallback -- `web_search` DDGS backend returned
"No results found" on the discovery query):
- https://kr.tradingview.com/scripts/ibd/page-2/ (RS Score formula confirmation)
- Shibui Finance RS Rating Screener (https://shibui.finance/rs-rating-screener) --
  "weights the most recent quarter at 40% and the three prior quarters at 20%
  each"
- Stockbee "IBD 200" methodology (https://stockbee.blogspot.com/2007/05/ibd-200.html)
  -- "Allocate 40% weight to [quarter 1] and 20% weight each to [quarters 2,3,4]"

This repo had prior RS-line entries (2026-09-09-039, 2026-09-10-095) but both
used a simple price-ratio-vs-benchmark-MA construction, not IBD's actual
disclosed 40/20/20/20 weighted-quarter composite computed directly on the
traded symbol's own multi-horizon returns. This iteration implements that
exact formula (adapted to a single-symbol weighted-return composite since
this repo's loaders don't support cross-sectional percentile ranking against
a full market universe).

## Signal logic

`weighted_rs = 0.4*ret(63d) + 0.2*ret(126d) + 0.2*ret(189d) + 0.2*ret(252d)`

Long when `weighted_rs > entry_threshold`; flat when `weighted_rs <
exit_threshold` or `max_hold_days` reached.

## Grid test summary (Step 6)

`param_grid={"entry_threshold": [0.0, 0.05], "exit_threshold": [0.0, -0.05],
"max_hold_days": [40, 60, 90]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, period 2018-01-01 to
2026-09-01.

- `total_cells`: 144, `passed_cells`: 38, `pass_fraction`: 0.264
- `by_asset_class`: equity 38/72 passed, **crypto 0/72 passed** (decisive
  reject for crypto)
- `by_vol_regime`: low 24/48, mid 12/48, high 2/48 (edge concentrated in
  low-vol regime, as usual for this repo's momentum-family strategies)
- `best_cell`: SPY, `entry_threshold=0.0, exit_threshold=-0.05,
  max_hold_days=60`, low-vol regime, Sharpe 2.63
- `worst_cell`: QQQ, high-vol regime, Sharpe -0.27

## Single-config validator results (best grid config: entry_threshold=0.0,
exit_threshold=-0.05, max_hold_days=60)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.040 | **FAIL** 0.863 |
| Max Drawdown (<=0.25) | **FAIL** 0.341 | **PASS** 0.228 |
| TC survival (net Sharpe >=0.5, 10bps/trade) | PASS 1.014 | PASS 0.828 |
| Walk-forward (4-split, >=0.75 pass frac) | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (relative std <=0.5) | PASS 0.072 | PASS 0.082 |

A follow-up local grid search (45 combos: entry_threshold in
[-0.02,0,0.02,0.05,0.08] x exit_threshold in [-0.10,-0.08,-0.05,-0.03,-0.02,0]
x max_hold_days in [10,15,20,30,40,60,90], filtered to exit<entry) found
**no single config on QQQ that clears both Sharpe>=1.0 AND MDD<=0.25
simultaneously** -- QQQ's Sharpe-optimal region trades off directly against
its MDD budget. SPY never cleared Sharpe>=1.0 in the same search space.

## Decision: REJECTED

QQQ fails max_drawdown decisively (0.341 vs 0.25 budget) despite passing all
4 other validators cleanly. SPY fails Sharpe (0.863 vs 1.0, a real miss not
a razor-thin near-miss) despite passing max_drawdown and the other 3
validators. Crypto is decisively rejected in the grid (0/72 cells). No
config found that clears both symbols' primary validators simultaneously in
an expanded 45-combo local search, so this is a genuine (not fixable via
easy retuning) rejection, though the underlying signal quality (excellent
walk-forward and parameter-sensitivity robustness on both symbols) suggests
this family could work with a volatility-targeting/leverage-cap overlay in a
future iteration specifically targeting the QQQ MDD failure mode (similar to
prior "leverage_cap_aware_design" entries in this repo).
