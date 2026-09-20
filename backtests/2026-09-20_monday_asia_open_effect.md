# 2026-09-20: Monday Asia Open Effect (BTC/ETH intraday trend window) — REJECTED

**Hypothesis:** Per
https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/
(Concretum Group): a high-frequency, volatility-targeted Bitcoin
trend-following benchmark shows a "Monday Asia Open Effect" -- strongly
positive trend-following performance from Sunday ~19:00 ET through Monday
~19:00 ET, aligned with the Tokyo cash equity market's Monday open, most
pronounced post-mid-2020. Adapted to a testable long-only single-asset
rule: gate a short-term momentum signal to the Sun-19:00-ET-to-Monday
window (flat outside it), on hourly bars.

**Source:**
https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/
(browser_exec).

**Infrastructure limitation encountered:** `validation/grid_test.py`'s
`run_strategy_grid` hard-codes `interval="1d"` when calling the crypto
loader (a documented prior bug-fix, per its own inline comment), so this
strategy's inherently intraday/hourly signal cannot be properly exercised
through the standard Step 6 grid-test pipeline -- on daily bars the
Sunday-evening/Monday sub-24h window collapses to noise (a daily close-only
series has no way to represent "Sunday 19:00 ET" as a distinct bar). Per
RESEARCH_LOOP.md's spirit of grounding decisions in what was actually
tested, this was checked manually on native hourly data via
`validators.check_sharpe_ratio`/`check_max_drawdown` directly, bypassing
`run_strategy_grid`, and annualized with `periods_per_year=24*365` for the
hourly frequency.

**Full-sample check on hourly bars** (default params: mom_lookback_hours=6,
max_hold_hours=30):

| Symbol | Active bars | Sharpe (hourly-annualized) | MDD |
|---|---|---|---|
| BTC/USDT | 10,580 | 0.185 (FAIL) | 0.326 (FAIL) |
| ETH/USDT | 10,435 | 0.176 (FAIL) | 0.457 (FAIL) |

Both symbols fail decisively on both Sharpe and MDD even on native hourly
data, so this is not merely an infra-scoping issue -- the simple
momentum-in-the-window adaptation itself does not carry the source's
claimed edge. This is unsurprising: the source's own benchmark is a
long-short, multi-model, volatility-targeted ENSEMBLE trend signal
(Sharpe ~1.6 over 2018-2025), not a single simple momentum lookback gated
to a calendar window -- a much richer signal than what a single-indicator
repo strategy file can reproduce.

**Equity (QQQ/SPY):** not run given the crypto-native mechanism (Sunday
trading, Tokyo-open alignment) has no equity analog, as flagged in advance
in the strategy file's own docstring; would be expected to produce a
fully degenerate all-flat signal since equity markets don't trade Sunday
evening at all.

**Decision: REJECTED.** Fails decisively on native hourly BTC/ETH data
(the only asset class where the mechanism is even meaningful); grid-test
infra cannot properly exercise an intraday-window hypothesis
(daily-bar-only limitation, noted for future reference rather than
worked around). Walk-forward/param-sensitivity/tx-cost skipped given the
decisive Sharpe+MDD double failure.

Strategy file (`strategies/2026-09-20_monday_asia_open_effect.py`) kept as
a record of a rejected attempt — not live.
