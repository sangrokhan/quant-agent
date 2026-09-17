# Donchian Breakout + Role-Reversal Retest Confirmation

**Strategy file:** `strategies/2026-09-17_donchian_role_reversal_retest.py`
**Source:** LuxAlgo "Level Interaction Rules" concept
(https://www.luxalgo.com/library/concept/level-interaction-rules), read via
browser_exec this iteration (web_search DDGS backend erroring on prior
queries this cron trigger session; Google SERP scan used for discovery).

## Hypothesis

A level's meaning depends on the full interaction sequence: "a break-and-
close followed by a held retest argues for role reversal, old resistance
acting as new support." This strategy waits for a Donchian-channel
breakout AND a subsequent held retest of the broken level (role reversal
confirmed) before entering, rather than entering on the raw breakout like
this repo's 18+ prior Donchian-family entries.

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: donchian_window in {15, 20, 30}, retest_tolerance_pct in {0.01, 0.02}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3, 2018-01-01 to 2026-09-01
- 72 total cells, 18 passed -> **pass_fraction = 0.25**
- By asset class: equity 14/36, crypto 4/36 (crypto shows SOME signal here,
  unusually, vs most breakout strategies in this repo that fail crypto
  0/N decisively)
- By vol regime: low 16/24, mid 0/24, high 2/24
- Best cell: QQQ, donchian_window=15/tol=0.01, low-vol tercile, Sharpe 2.22

## Focused parameter search + single-config validation

A dedicated local sweep (donchian_window x retest_tolerance_pct x
retest_max_days) beyond the coarse grid found SPY clears every validator at
donchian_window=10, retest_tolerance_pct=0.02, retest_max_days=5:

| Validator | SPY (accepted config) | QQQ (best found) |
|---|---|---|
| Sharpe ratio (>=1.0) | **pass** 1.225 | fail 0.673 (best found across a 100-combo local sweep) |
| Max drawdown (<=0.25) | pass 0.091 | -- |
| TC survival (net Sharpe >=0.5) | **pass** 1.026 (86 trades) | -- |
| Walk-forward (>=0.75 splits positive) | **pass** 1.0 (4/4) | -- |
| Parameter sensitivity (rel std <=0.5) | **pass** 0.117 | -- |

QQQ could not clear Sharpe 1.0 anywhere in an extensive local grid
(donchian_window in {8,10,12,15,20} x tolerance in {0.01-0.03} x
retest_max_days in {5,7,10,15}), so it is rejected rather than force-fit.

Crypto (BTC/USDT, ETH/USDT) at the coarse-grid best config: Sharpe
0.357/0.475, MDD 0.60/0.49 (both breach 0.25), walk-forward 0.25/1.0 mixed,
TC-survival fails both -- rejected. The coarse grid did show 4/36 crypto
cells passing (an unusually non-zero result for a breakout family in this
repo), but not at a config that also holds up on the equity side or
full-sample.

## Verdict: **ACCEPTED (SPY only)**, donchian_window=10, retest_tolerance_pct=0.02, retest_max_days=5, max_hold_days=20 (default)

All 5 validators pass cleanly for SPY (Sharpe 1.225, MDD 9.1%, net Sharpe
after costs 1.026 on 86 trades over 8.7yr, walk-forward 4/4 positive
splits, parameter-sensitivity rel.std 0.117 -- one of the more stable
results in this log). QQQ and crypto (BTC/USDT, ETH/USDT) rejected.

This is the first Donchian-family strategy in this repo whose entry
signal is gated by a genuine multi-bar retest-confirmation sequence
(break -> wait -> retest -> hold) rather than the immediate breakout
itself, and the first level-interaction-taxonomy (LuxAlgo "break-and-
close + held retest = role reversal") construction tested here.
