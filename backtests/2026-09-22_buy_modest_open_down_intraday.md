# 2026-09-22: Buy Every (Modest) Open Down — Intraday Reversal (REJECTED)

**Hypothesis source:** QuantifiedStrategies.com, "Buy Every Open Down
Trading Strategy"
(https://www.quantifiedstrategies.com/buy-every-open-down/), accessed
2026-09-22 via browser_exec (this article's rule text was not paywalled).

**Disclosed rule (source, tested on SPY, Jan 2010-Jun 2012):** if today's
open is below yesterday's close but the down-open magnitude is under
~0.45-0.5%, buy at the open and sell at the close (same trading day, no
overnight hold); source's own improvement gates the entry additionally on
"yesterday itself was a down day" (raised avg gain 0.11% -> 0.14% in their
short 2.5-year sample).

**Implementation:** `strategies/2026-09-22_buy_modest_open_down_intraday.py`
— first same-day open-to-close intraday strategy in this repo (distinct
from all prior multi-day-hold strategies and from the overnight-gap
strategies, which trade the close->open gap rather than the open->close
session).

## Step 6 — Grid test summary

`param_grid={"down_threshold_max": [0.004,0.005,0.007], "require_prior_down_day": [True,False]}`,
equity QQQ/SPY + crypto BTC/ETH, `vol_regime_splits=3`, 2019-2026.

- Overall: 12/72 cells passed (pass_fraction 0.167).
- By asset class: equity 9/36, crypto 3/36 (crypto surprisingly non-zero,
  but weak overall).
- By vol regime: low-vol 11/24, mid-vol 0/24, high-vol 1/24 — edge is
  almost entirely confined to low-volatility regime terciles; this is a
  classic "vol-regime grid overstates full-sample" warning sign.
- Best cell: SPY, low-vol, down_threshold_max=0.007/require_prior_down_day=False,
  Sharpe 2.46 (regime-tercile only, not representative of full sample).

## Step 7 — Validators (full sample, two candidate configs)

| Config | Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| dtm=0.007, no prior-day gate | QQQ | 0.598 ❌ | 0.141 ✅ | -0.136 ❌ | 1.0 ✅ | 0.255 ✅ |
| dtm=0.007, no prior-day gate | SPY | 0.683 ❌ | 0.092 ✅ | -0.183 ❌ | 1.0 ✅ | 0.230 ✅ |
| dtm=0.005, prior-day gate (source's stated improvement) | QQQ | 0.601 ❌ | 0.131 ✅ | 0.143 ❌ | 0.75 ✅ | 0.197 ✅ |
| dtm=0.005, prior-day gate (source's stated improvement) | SPY | 0.115 ❌ | 0.151 ✅ | -0.308 ❌ | 0.5 ❌ | 0.574 ❌ |

Both candidate configs fail Sharpe (>=1.0 threshold) and transaction-cost
survival (>=0.5 net Sharpe) on the full sample for both symbols, despite
the grid's low-vol-regime terciles looking attractive. The high trade
count (180-638 trades over the sample, since this is a near-daily
same-day signal) makes the strategy especially cost-sensitive, and the
source's own original test window (2010-2012, pre-regime-shift, no
transaction costs modeled) likely does not generalize to today's tighter
intraday spreads/higher HFT competition for this exact edge.

## Decision: REJECT (all configs, all asset classes)

Sharpe and transaction-cost survival fail full-sample for every config
tested, on both QQQ and SPY, despite promising low-vol-regime grid
cells. Strategy/backtest files kept as a record of a rejected attempt —
do not mistake as live.
