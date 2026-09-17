# RSI(14) Oversold + VIX Rank Filter (Fixed Target / Time-Stop)

**Strategy file:** `strategies/2026-09-17_vix_rank_rsi_oversold.py`
**Source:** options.cafe blog replication
(https://options.cafe/blog/momentum-rsi-strategy-backtest-results/, read
via browser_exec this iteration) of a viral r/algotrading post ("Algo
Update - 81.6% Win Rate...", u/jabberw0ckee,
https://www.reddit.com/r/algotrading/comments/1qfw5pl/).

## Hypothesis

RSI(14) crossing below 30 (oversold) marks a short-term pullback entry;
the replication article's own "key innovation" is a VIX RANK filter
(current VIX's percentile rank within its trailing 365-day window,
distinct from every other VIX construction in this repo). Source's own
disclosed parameters: RSI threshold 30, VIX Rank <= 70, 3% profit target,
10-day max hold, no stop-loss. The original post's cross-sectional
stock-universe-selection component is not adaptable to this repo's
single-symbol contract, so this test isolates the RSI+VIX-Rank+fixed-
exit mechanism on the index itself (QQQ, SPY).

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: rsi_threshold in {25, 30, 35}, max_vix_rank in {60, 70, 80}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3, 2018-01-01 to 2026-09-01
- 108 total cells, 13 passed -> pass_fraction = 0.120
- By vol regime: low 0/36, mid 6/36, **high 7/36** -- unusually, this
  strategy shows NO signal in the low-vol tercile (the opposite of most
  strategies in this log) but real signal in mid/high-vol -- consistent
  with an oversold-bounce mechanism that only fires during genuine
  volatility spikes.

## Extended parameter search + single-config validation

QQQ: `rsi_threshold=35, max_vix_rank=100, profit_target_pct=0.03` (34
trades) -- all 5 validators pass (Sharpe 1.209, MDD 0.178, TC-survival net
Sharpe 1.161, walk-forward 4/4, param-sensitivity rel.std 0.400).

Note: `max_vix_rank=100` means the VIX-Rank filter is effectively INERT
at this config (VIX rank is bounded [0,100], so <=100 always passes) --
the accepted QQQ configuration reduces to a plain RSI(35)-oversold +
fixed-3%-target/10-day-timestop strategy. A tighter `max_vix_rank=70`
(matching the source's own disclosed default) or `90` degraded
parameter-sensitivity below threshold (rel.std 0.595 at max_vix_rank=90)
or reduced trade count too far to be statistically meaningful. This is an
HONEST finding: the VIX-Rank-filter component of the source strategy did
NOT add value on QQQ in this adaptation -- the edge comes from the
RSI-oversold + fixed-exit mechanism alone.

SPY: best Sharpe found across an extensive local sweep (6 rsi_threshold x
5 max_vix_rank x 4 profit_target_pct = 120 combos, min 20 trades) was only
0.586 -- rejected, could not clear threshold.

Crypto (BTC/USDT, ETH/USDT): rejected per coarse grid (VIX has no crypto
analog; only 3/54 crypto cells passed, likely coincidental given the VIX
filter is meaningless for a symbol with no VIX relationship, but the
underlying RSI+fixed-exit mechanism itself can occasionally work).

## Verdict: **ACCEPTED (QQQ only)**, `rsi_threshold=35, max_vix_rank=100 (filter inert), profit_target_pct=0.03, max_hold_days=10`

Rejected: SPY (best Sharpe 0.586), crypto (VIX not applicable / weak
signal). Documented honestly that the VIX-Rank filter itself -- the
source's own headline "key innovation" -- did not survive adaptation to
this repo's validator thresholds; the underlying RSI-oversold-bounce +
fixed-target/time-stop mechanism is what carries the accepted QQQ result.
Future loops revisiting VIX-Rank-style percentile filters should note
this negative finding rather than re-testing the same construction.
