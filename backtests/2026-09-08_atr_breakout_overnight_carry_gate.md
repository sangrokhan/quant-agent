# Backtest Report: ATR Breakout-from-Open with Overnight Carry Gate (2026-09-08)

## Hypothesis
Per Concretum Group's "Breaking the Rules of Intraday Trading"
(https://concretumgroup.com/breaking-the-rules-of-intraday-trading/), an
intraday-trend strategy's long side benefits from carrying the EOD position
overnight into the next session's open (overnight-return premium), while
the short side does not. Adapted here as a daily-bar proxy: define a
bullish "breakout day" as one where close finishes atr_mult*ATR above that
day's own open, capture that day's open->close return AND hold overnight
into the next day's open on breakout days.

## Strategy file
`strategies/2026-09-08_atr_breakout_overnight_carry_gate.py`

## Grid test summary (Step 6)
Grid: `atr_mult` in [0.25,0.5,0.75] x `atr_period` in [10,14,20], equity
(QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3. 108 cells.

- pass_fraction: 1.00 (108/108) -- suspiciously perfect
- best_cell Sharpe: 11.6 (QQQ, low-vol) -- implausibly high

## Decision: REJECTED (methodological flaw -- look-ahead bias, not a real edge)

Diagnostic check (`scripts/check_lookahead_atr_breakout.py`) found that
97.3% of "breakout day" returns are non-negative (only 2.7% negative) --
because the breakout day INDICATOR ITSELF is defined using that same day's
CLOSE (close > open + atr_mult*ATR), the strategy is trivially guaranteed
to book a large positive open->close return on every day it "enters",
since the entry condition and the realized intraday return are definitionally
the same event observed with the same information. This is not a real
tradable edge -- a live trader cannot know at the open whether today will
close far enough above the open to qualify as a "breakout day"; the entire
100% grid pass_fraction and 11.6 Sharpe are an artifact of using the
outcome to define the signal (classic look-ahead bias), not evidence the
Concretum Group's actual thesis (True intraday breakout entry + overnight
carry gated on realized EOD direction) has any edge.

This strategy file and grid/validator scripts are being LEFT IN THE REPO
as a deliberately-flagged rejected artifact (not deleted) so a future loop
does not mistake the grid_result_atr_breakout_overnight.json's 1.0
pass_fraction for a real accepted result if it stumbles on the file
without reading this report. The correct fix for a future iteration
revisiting this idea: only count a day as a valid trading signal using
information available at the time of the entry decision (e.g. an actual
intraday ATR-band breakout detected using intraday bars where the
breakout timestamp precedes the entry, not a same-bar close-based
proxy) -- this repo's OHLCV-only daily bars from data/loaders.py cannot
correctly implement this idea without intraday (sub-daily) equity data,
which load_equity does not provide.
