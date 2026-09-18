# JETS Holiday Calendar-Anomaly Window — Backtest Report

**Strategy file:** `strategies/2026-09-19_jets_holiday_calendar_effect.py`
**Date:** 2026-09-19

## Hypothesis

Sourced from Quantpedia's "Do Airline Stocks Take Off Around U.S. Holidays?"
(18 Sep 2026, https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/,
read via `browser_exec` after browsing Quantpedia's blog listing page —
`web_search` was used first to find the general topic (turned up nothing
this specific), so the blog was browsed directly). The article studies the
U.S. Global Jets ETF (JETS) around the 8-9 major U.S. federal holidays and
finds a positive return drift concentrated in the four trading days before
each holiday (D-4..D-1), and a further extended window through D+8, driven
by anticipated airline-sector holiday-travel demand. The article's third
strategy (JETS-USO cross-asset spread) is infeasible under this repo's
single-symbol `generate_returns(price_df, **params)` interface and was not
implemented.

This repo's implementation uses `pandas.tseries.holiday.USFederalHolidayCalendar`
(+ manually-added Juneteenth from 2022) to identify the exact holiday
calendar, rather than a generic >=N-calendar-day-gap heuristic (distinct
from the already-rejected `2026-09-03_pre_holiday_effect.py`, id
2026-09-03-020, which used any >=3-day gap — i.e. ordinary weekends too —
and was rejected for excess turnover/failed cost-survival). Two tunable
params: `entry_days_before` (buy at close of D-entry_days_before) and
`exit_days_after` (sell at close of D-1 if negative, or D+exit_days_after
if positive).

## Grid test (validation/grid_test.py::run_strategy_grid)

`param_grid={"entry_days_before": [4,5,6], "exit_days_after": [-1,3,8]}`,
`symbols={"equity": ["JETS","QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2015-05-01 to 2026-09-01.

- **Overall:** 31/135 cells passed (pass_fraction 0.230)
- **By asset class:** equity 29/81 (0.358); crypto 2/54 (0.037)
- **By vol regime:** low 10/45, mid 13/45, high 8/45 (fairly even, no
  single-regime concentration)
- **By symbol:** JETS 4/27, QQQ 11/27, SPY 14/27, BTC/USDT 0/27, ETH/USDT
  2/27 — the edge holds up on the BROAD INDEX ETFs (QQQ/SPY) more strongly
  than on JETS itself, an interesting inversion of the article's own
  airline-sector framing (see Notes below).
- **Best cell:** entry_days_before=6, exit_days_after=-1, QQQ, mid-vol,
  Sharpe 2.37.
- **Worst cell:** entry_days_before=6, exit_days_after=-1, BTC/USDT,
  high-vol, Sharpe -0.63 (crypto categorically unsuitable — the U.S.
  federal holiday calendar is structurally near-inert for a 24/7 market).

Full-sample (non-regime-sliced) Sharpe/MDD scan across all 9 param combos
for JETS/QQQ/SPY:

| entry_days_before | exit_days_after | JETS Sharpe | JETS MDD | QQQ Sharpe | QQQ MDD | SPY Sharpe | SPY MDD |
|---|---|---|---|---|---|---|---|
| 4 | -1 | 0.485 | 0.216 | 0.263 | 0.166 | 0.364 | 0.133 |
| 5 | 3  | 0.874 | 0.334 | 1.009 | 0.197 | 1.097 | 0.145 |
| 6 | -1 | 0.973 | 0.191 | 0.976 | 0.192 | 1.038 | 0.141 |
| **6** | **3** | **1.081** | **0.288** | **1.178** | **0.201** | **1.223** | **0.151** |

## Best config: entry_days_before=6, exit_days_after=3

Buy at close of the 6th-to-last trading day before each U.S. federal
holiday, sell at close of the 3rd trading day after. Full validator suite
on QQQ and SPY (JETS itself fails MDD — see Decision):

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.178 (pass) | 1.223 (pass) | >= 1.0 |
| Max drawdown | 0.201 (pass) | 0.151 (pass) | <= 0.25 |
| Transaction cost survival (10bps/trade, 106 trades) | 1.034 (pass) | 1.018 (pass) | >= 0.5 |
| Walk-forward (manual 4-split fallback — `check_walk_forward` errors on installed vectorbt 1.1.0, no `vbt.utils.splitting`) | 4/4 splits positive Sharpe (pass) | 4/4 splits positive Sharpe (pass) | >= 0.75 |
| Parameter sensitivity (9-combo grid, relative std) | 0.332 (pass) | 0.284 (pass) | <= 0.5 |

JETS itself at the same config: Sharpe 1.081 (pass), MDD 0.288 (**fail**,
threshold 0.25) — the exposure window (~45% of trading days at
entry=6/exit=3, since holidays occur roughly monthly and the window spans
10 trading days each) captures more of JETS' own idiosyncratic
sector-specific drawdowns (airline-sector volatility, e.g. COVID-era
travel collapse) than the broad index ETFs do.

## Decision

**Accepted — QQQ and SPY only (broad equity index, NOT the airline-sector
ETF the source studied).** All 5 validators pass cleanly for QQQ and SPY
at entry_days_before=6/exit_days_after=3. JETS itself — the source's
actual instrument — fails on max drawdown, so this is accepted as a
*general* U.S.-federal-holiday calendar-window strategy on broad equity
indices, not validated as an airline-sector-specific effect. Crypto
rejected decisively (0/54 grid cells; USFederalHolidayCalendar mechanism
is structurally inert on 24/7 markets, as expected — few holidays fall
near existing signal windows and the ones that do show no consistent
edge).

This differs meaningfully from the article's own framing (which claims an
airline-specific holiday-travel mechanism) — the observed edge instead
looks like a re-discovery of a broader multi-holiday turn-of-holiday
effect that happens to work better on diversified index ETFs than on a
single volatile sector ETF. Scope: equity index ETFs (QQQ, SPY) only;
window entry_days_before=6, exit_days_after=3 (i.e. roughly D-6 through
D+3 around each of the 9 US federal holidays).
