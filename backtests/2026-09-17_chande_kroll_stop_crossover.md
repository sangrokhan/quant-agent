"""Backtest report: Chande Kroll Stop dual-line crossover (2026-09-17).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Direct fix attempt for prior rejection id=2026-09-04-116 (Chande Kroll Stop
breakout: QQQ MDD breach 0.285>0.25, SPY Sharpe near-miss 0.976 + TC-survival
fail, crypto decisive 0/36 grid cells). This iteration adds an SMA(trend_window)
uptrend regime gate and a min_hold_days hysteresis (this repo's standard
whipsaw-reduction pattern) on top of the identical CKS dual-line-crossover
signal (long when close > both short_stop and long_stop).

Source: Google AI-overview + IBKR Glossary (via browser_exec fallback --
web_search DDGS/Yahoo backend down with RequestError/TLS errors on every
query attempted this iteration). IBKR's own stated rule: "Sell when the
price crosses below both lines. Buy when the price crosses above both
lines."

## Grid summary (p in {10,15} x x in {1.0,1.5} x min_hold_days in {3,5},
q=9/trend_window=100/max_hold_days=40 fixed, QQQ+SPY+BTC/USDT+ETH/USDT,
vol_regime_splits=3)

- 96 cells total, 35 passed (36.5% pass_fraction)
- by_asset_class: equity 24/48 (50%), crypto 11/48 (22.9%)
- by_vol_regime: low 22/32 (68.8%), mid 13/32 (40.6%), high 0/32 (0%)
- best config across all cells: p=15/x=1.0/min_hold_days=3 (6/12 passed,
  avg per-cell Sharpe 0.91)
- best cell: p=15/x=1.0/min_hold_days=3, ETH/USDT mid-vol, Sharpe=2.43
- worst cell: p=10/x=1.0/min_hold_days=3, QQQ high-vol, Sharpe=-0.77

The trend_window gate + min_hold_days hysteresis DID fix the prior QQQ MDD
breach (13.4% vs prior 28.5%) but the trend gate is too restrictive on the
FULL SAMPLE (fewer, more filtered entries) -- full-sample Sharpe collapsed
well below the per-tercile grid Sharpes.

## Single-config validators (best config: p=15, x=1.0, q=9, trend_window=100,
min_hold_days=3, max_hold_days=40), full sample 2019-01-01 to 2026-09-01

| Symbol   | Sharpe (>=1.0) | MDD (<=0.25) | TC-survival net Sharpe (>=0.5) | Walk-forward | Param sensitivity (<=0.5 rel.std) |
|----------|---------------:|-------------:|--------------------------------:|--------------|------------------------------------:|
| QQQ      | 0.739 FAIL     | 0.134 PASS   | 0.298 FAIL                      | vectorbt RangeSplitter bug (known repo issue, see 2026-09-04-116 notes) -- not scored | 0.459 PASS |
| SPY      | 0.668 FAIL     | 0.099 PASS   | 0.098 FAIL                      | same bug, not scored | 0.295 PASS |
| BTC/USDT | 0.180 FAIL     | 0.541 FAIL   | -0.048 FAIL                     | same bug, not scored | 0.206 PASS |
| ETH/USDT | 0.263 FAIL     | 0.303 FAIL   | -0.027 FAIL                     | same bug, not scored | 1.409 FAIL |

## Decision: REJECT (all 4 symbols)

The trend gate fixed the MDD problem for equities (QQQ 13.4%, SPY 9.9%, both
well under 25%) but over-filtered the number of entries such that full-sample
Sharpe fell well short of 1.0 for all symbols, and net-of-cost Sharpe is
decisively negative/near-zero for every symbol -- the strategy does not
survive flat 10bps/trade transaction costs at its current trade frequency.
Crypto additionally still fails MDD outright (BTC 54.1%, ETH 30.3%).

This is the opposite failure mode from the original rejection (2026-09-04-116
failed on drawdown/whipsaw; this fix over-corrects into a low-trade-frequency,
low-Sharpe regime). A future revisit could try a looser trend_window (e.g. 50
instead of 100) or removing the min_hold hysteresis gate specifically to
recover trade frequency without reintroducing the original whipsaw/MDD
problem, but that is left for a future iteration.
"""
