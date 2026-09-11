# PMax (Profit Maximizer) MA-Crosses-PMax Trend Following

**Hypothesis:** PMax (KivancOzbilgic, 2020) combines SuperTrend's ATR
trailing-stop mechanism with Anil Ozeksi's MOST idea of applying that
trailing stop to a smoothed Moving Average of price rather than raw
close. Per https://kr.tradingview.com/script/sU9molfV/ (creator's own
page, via browser_exec/google.com fallback): "We are under the effect of
the uptrend in cases where the Moving Average is above PMax... BUY when
Moving Average crosses above PMax, SELL when Moving Average crosses
under PMax."

Source: https://kr.tradingview.com/script/sU9molfV/ (via browser_exec
fallback; web_search DDGS backend TLS/connection error on initial query
this iteration).

## Step 6 Grid Test Summary (108 cells: 3 ma_length x 3 atr_multiplier x
1 max_hold_days x 4 symbols x 3 vol regimes)

- pass_fraction: 0.25 (27/108)
- by_asset_class: equity 27/54 passed, crypto 0/54 (decisively rejected)
- by_vol_regime: low 18/36, mid 9/36, high 0/36 (edge concentrated
  low/mid-vol, fails entirely in high-vol)
- best_cell: ma_length=10, atr_multiplier=2.0, max_hold_days=60, SPY,
  low-vol regime, Sharpe=2.69

## Step 7 Single-Config Validation (best config: ma_length=10,
atr_multiplier=2.0, max_hold_days=60, full sample 2019-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|--------|--------|-----|-------------|---------------|---------------------|
| QQQ | 1.016 (PASS) | 0.383 (FAIL, thr 0.25) | 0.993 (PASS) | 0.75 (PASS) | 0.0 rel std (PASS, suspiciously flat) |
| SPY | 0.928 (FAIL, thr 1.0) | 0.342 (FAIL, thr 0.25) | 0.900 (PASS) | 1.00 (PASS) | ~0 rel std (PASS, suspiciously flat) |

Note: parameter-sensitivity sweep (atr_multiplier in [2.0,3.0,4.0]) gave
essentially identical Sharpe for every value tested -- this looks like a
possible implementation artifact (the MA-crossing-PMax entries may be
dominated by MA-slope changes rather than the ATR band width in this
strategy's low-frequency full-sample regime, since only 31 trades fired
over 7+ years) rather than genuine parameter robustness; flagged for a
future revisit if this strategy is ever reconsidered.

## Decision: REJECTED (decisively)

Max drawdown fails badly on BOTH QQQ (38.3% vs 25% threshold) and SPY
(34.2% vs 25% threshold) at the grid-best config -- despite decent
full-sample Sharpe on QQQ (1.016) and near-miss on SPY (0.928), the
strategy's very low trade frequency (31 trades over 7+ years, i.e. long
holds via max_hold_days=60 ratchet) lets drawdowns run far past the
25% risk tolerance before the trailing stop reacts. Crypto decisively
rejected 0/54 grid cells. Not accepted; MDD failure is severe enough
that no minor parameter tweak is expected to close the gap without a
tighter ATR multiplier or shorter max_hold -- a future iteration could
retry with atr_multiplier<2.0 and a stop-loss overlay if revisited.
