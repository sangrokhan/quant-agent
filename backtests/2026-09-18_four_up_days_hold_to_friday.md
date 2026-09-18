# Backtest Report: Four Consecutive Up Days -> Hold Into Friday's Open

**Strategy file:** `strategies/2026-09-18_four_up_days_hold_to_friday.py`
**Date:** 2026-09-18
**Hypothesis:** Per QuantifiedStrategies.com's "TRADING IDEA - FOUR UP DAYS
IN A ROW - S&P 500" (disclosed via Google AI-overview synthesis, read via
browser_exec fallback -- web_search's DDGS backend errored on this
iteration's queries; corroborated via a Facebook excerpt of the same
source): "buying the S&P 500's close after four consecutive up days and
selling Friday's open." Four consecutive up-closes is read as a
momentum-continuation signal (opposite economic thesis of every
consecutive-down-days-as-oversold-bounce strategy already tested in this
repo), entering at the close of the 4th up-day and holding through to the
next Friday's open.

## Grid summary (Step 6)

Parameter grid: `streak_len` in {3,4,5}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; sample 2016-01-01 to
2026-09-01.

- Total cells: 36, passed: 9, **pass_fraction = 0.25**
- By asset class: equity 6/18 passed, crypto 3/18 passed
- By vol regime: low 4/12, mid 3/12, high 2/12
- Best cell: crypto BTC/USDT mid-vol, streak_len=3, Sharpe=1.99
- Worst cell: crypto ETH/USDT high-vol, streak_len=3, Sharpe=-0.85

## Single-config validation (Step 7): streak_len=4 (source's literal rule)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample, 2016-2026) | 0.770 | 0.745 | >= 1.0 | **FAIL both** |
| Max drawdown | 0.089 | 0.074 | <= 0.25 | PASS both |
| Net Sharpe after costs (5bps/trade) | 0.414 | 0.323 | >= 0.5 | **FAIL both** |
| Parameter sensitivity (3-value local sweep, relative std) | 0.163 | 0.124 | <= 0.5 | PASS both |

Note: MDD is excellent (low exposure, calendar-anchored short holds) but
the raw edge itself (Sharpe <1.0) is too weak to clear the transaction-cost
bar at 5bps/trade with 210-242 trades over the sample -- the strategy fires
often enough (every 4-in-a-row up-streak) that trading costs meaningfully
erode an already-marginal edge.

## Decision: REJECT

Full-sample Sharpe (QQQ 0.770, SPY 0.745) misses the 1.0 threshold and net
Sharpe after 5bps/trade costs (QQQ 0.414, SPY 0.323) misses the 0.5
threshold for both primary equity symbols. Grid confirms the effect is
real but modest and not particularly regime-concentrated (roughly flat
pass-rate across low/mid/high vol), unlike many rejected strategies in this
repo that show a strong narrow-regime edge worth rescuing with a gate --
here there's no obvious single dimension to gate on. Crypto (streak_len=3)
shows a genuinely interesting mid-vol cell (Sharpe 1.99) but full crypto
pass fraction (3/18) is too thin to warrant a standalone crypto-only
accept without further per-symbol tuning, which is left as a possible
future-iteration rescue attempt.

Strategy file and this report are kept as a rejected-attempt record.
