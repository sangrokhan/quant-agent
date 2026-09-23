# Dual-SMA(200/300) Trend + RSI Oversold-Turn-Up, Fixed Holding-Period Exit

**Strategy file:** `strategies/2026-09-23_dualsma_rsiturn_fixedhold.py`
**Hypothesis source:** Sofien Kaabar, CFA, "I Backtested a Powerful Strategy
on Bitcoin - The Results"
(https://abouttrading.substack.com/p/i-backtested-a-powerful-strategy),
read via browser_exec this iteration.

## Hypothesis

Long entry when SMA(short_len=200) > SMA(long_len=300) (established uptrend)
AND RSI(14) previous bar < rsi_us (oversold) AND current RSI > previous RSI
(turning up). Exit exactly `holding_period` bars later (pure time-stop, no
other exit condition) -- source's own disclosed bull-only BTC parameters:
short_len=200, long_len=300, rsi_ov=60, rsi_us=35, holding_period=20.

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = {rsi_us: [30,35,40], holding_period:
[10,20,30]}, symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]},
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 16, **pass_fraction: 0.148**
- by_asset_class: equity 15/54, crypto 1/54 (crypto essentially fails
  entirely under this construction)
- by_vol_regime: low 8/36, mid 6/36, high 2/36
- Best equity config by avg per-vol-regime Sharpe: rsi_us=30,
  holding_period=30 (avg 0.882), driven mostly by QQQ's low-vol slice
  (Sharpe 2.00) -- SPY's slices were much weaker/negative in places.

## Single-config validation (Step 7), config = rsi_us=30, holding_period=30 (short_len=200/long_len=300 fixed)

| Symbol | Full-sample Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.631 (FAIL, thresh 1.0) | 0.169 (PASS) | 0.614 (PASS) | 0.75 (PASS, thresh 0.5) | 0.165 (PASS) |
| SPY | 0.278 (FAIL, thresh 1.0) | 0.172 (PASS) | 0.263 (FAIL, thresh 0.5) | 0.50 (borderline PASS) | 0.165 (PASS) |

The grid's per-vol-regime slice Sharpes looked promising in isolated low-vol
slices (QQQ 2.00), but the full-sample single-config Sharpe (what actually
matters for the accept/reject decision) is decisively below threshold on
both equities -- the low-vol-slice outperformance doesn't generalize across
the full sample. Very low trade counts (10-12 trades over ~7.5 years) also
mean these Sharpe estimates carry wide uncertainty.

## Decision

**Reject** (all symbols). Neither QQQ nor SPY clears the Sharpe>=1.0
threshold on the full sample despite reasonable MDD; SPY additionally fails
transaction-cost survival. Crypto pass_fraction (1/54) confirms the
construction doesn't transfer to that asset class either, despite being
sourced from a BTC-focused article. Strategy files retained as a documented
rejected attempt.
