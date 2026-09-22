# 2026-09-22: Monday Weakness Reversal (close below prior Friday's low)

**Hypothesis source:** QuantifiedStrategies.com, "Is This Still The Best
Reversal Strategy?"
(https://www.quantifiedstrategies.com/is-this-still-the-best-reversal-strategy/),
accessed 2026-09-22 via browser_exec (web_extract's ddgs-only backend could
not fetch this page's content this iteration).

**Disclosed rule (source, tested on SSO):**
- Today is Monday.
- Monday's close < prior Friday's low.
- Buy at the close.
- Exit at the close on the first day close exceeds yesterday's high, or
  after 4 trading days (Friday), whichever comes first.
- No stop-loss (source's explicit design choice).

**Implementation:** `strategies/2026-09-22_monday_below_friday_low_reversal.py`
(equity/crypto agnostic, standard `generate_signals`/`generate_returns`
keyword-args contract). "Prior Friday's low" is found by scanning back up
to `friday_lookback` bars for the most recent bar with weekday==4; this
handles the normal case (previous bar is Friday) and holiday-shortened
weeks (skips signal if no Friday found in the lookback window).

## Step 6 — Grid test summary

`param_grid={"friday_lookback": [4,5,6], "max_hold_days": [3,4,5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall:** 45/108 cells passed (pass_fraction 0.417).
- **By asset class:** equity 45/54 passed; crypto **0/54 passed** (decisive
  reject on crypto — the weekday-conditional, Friday-reference-price
  mechanic has no equivalent in a 24/7 market and the strategy should be
  scoped to equity only).
- **By vol regime:** low-vol 9/36, mid-vol 18/36, high-vol 18/36 (equity
  cells only, since crypto passed none) — edge present across all three vol
  regimes on equities, somewhat stronger in mid/high vol.
- **Best cell:** QQQ, mid-vol, friday_lookback=4/max_hold_days=4, Sharpe 1.88.
- **Worst cell:** BTC/USDT, low-vol, same params, Sharpe -0.20.

## Step 7 — Validators (best config: friday_lookback=4, max_hold_days=4)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.239 ✅ | 1.130 ✅ | >= 1.0 |
| Max drawdown | 0.105 ✅ | 0.095 ✅ | <= 0.25 |
| Transaction-cost survival (10bps/trade) | net Sharpe 1.064 ✅ | net Sharpe 0.943 ✅ | >= 0.5 |
| Walk-forward (manual 4-split; vectorbt `RangeSplitter` API broken in this install, per repo-wide known issue) | 4/4 splits positive ✅ | 4/4 splits positive ✅ | >= 0.75 |
| Parameter sensitivity (12-combo grid, friday_lookback x max_hold_days) | relative_std 0.096 ✅ | relative_std 0.031 ✅ | <= 0.5 |

QQQ: 65 trades over the sample. SPY: 70 trades.

## Decision: ACCEPT (equity only — QQQ and SPY)

All 5 validators pass for both QQQ and SPY at the shared config
(friday_lookback=4, max_hold_days=4). Crypto is explicitly out of scope
(0/54 grid cells passed) — the mechanic depends on a Friday/weekend market
close that has no analog in 24/7 crypto trading.
