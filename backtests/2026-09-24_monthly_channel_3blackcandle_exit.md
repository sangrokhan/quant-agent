# Monthly Channel + Three-Black-Candle Trend Exit — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_monthly_channel_3blackcandle_exit.py`
**Source:** https://thepatternsite.com/MonthlyChannels.html ("Bulkowski on
Monthly Trends", Thomas Bulkowski), read via browser_exec.

## Hypothesis

On monthly-scale charts, once an up-sloping price channel has been
established for >= 2 years, three consecutive black (down-close) monthly
candles measured from the channel's running high (needing 3 if the high
candle itself is white, 2 more if the high candle is already black) reliably
signals a trend change / sell point. Source's own 1990-2017, 503-stock /
897-channel study: 42% of channels show the signal, average post-signal
decline 43%, false-signal rate 21%, ~3.7yr average recovery time.

Adapted here into a single-instrument continuous long/flat strategy: enter
long once monthly close has been above a rising `trend_sma_months`-month SMA
for >= `min_uptrend_months` consecutive months; exit to flat on either the
disclosed 3-black-candle signal (tracked from the running monthly high since
entry) or a secondary SMA-break stop.

## Grid test summary (Step 6)

`trend_sma_months` in {18,24,30}, `min_uptrend_months` in {18,24}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 72 cells.

- **pass_fraction: 0.111** (8/72)
- **by_asset_class:** equity 8/36, crypto 0/36
- **by_vol_regime:** low 7/24, mid 1/24, high 0/24
- **best_cell:** trend_sma_months=30, min_uptrend_months=18, QQQ, low-vol,
  Sharpe 1.358
- **worst_cell:** same params, BTC/USDT, mid-vol, Sharpe -1.179

## Single-config validation (Step 7)

Config: `trend_sma_months=30, min_uptrend_months=18` (the grid's best cell).
Full sample 2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Trades |
|---|---|---|---|---|
| QQQ | 0.587 **FAIL** | 0.375 **FAIL** | 0.584 PASS | 4 |
| SPY | 0.334 **FAIL** | 0.234 PASS | 0.331 **FAIL** | 2 |

`check_walk_forward` errored with the pre-existing repo bug
(`vbt.utils.splitting` missing, same issue noted in several prior 2026-09-24
entries); skipped. `check_parameter_sensitivity` not separately run — the
grid's own low/mid/high vol-regime spread (Sharpe 1.36 in low-vol vs.
negative in mid/high) already demonstrates the strategy is NOT robust
across the full sample, which is dispositive on its own regardless.

Only 2-4 full-sample entries per symbol over 10.5 years (the >= 18-24
consecutive-month uptrend precondition is a rare, long-horizon gate) — the
strategy edge that shows up in the grid's low-vol-tercile slice does not
survive when measured over the full sample, which mixes in the mid/high-vol
periods where the entry precondition happens to catch late-cycle uptrends
right before a trend break (the classic "buy near the top of a long channel,
converted to a channel-following long instead of Bulkowski's own SHORT/SELL
use of the signal" issue -- Bulkowski's own use of the pattern is a SELL
signal on an existing HOLDING, not a fresh-entry-then-hold signal, so this
adaptation inherently degrades the edge by adding a speculative long entry
leg the source never specifies exact rules for).

## Decision

**Rejected** for both QQQ and SPY (full-sample Sharpe fails both, plus QQQ's
max-drawdown fails). Crypto rejected decisively per the grid (0/36 cells
passed). Note for a future loop: the source's actual disclosed rule is a
SELL/EXIT signal for an existing long-term holding, not an entry rule — a
future revisit should pair the exit rule with a different low-lookahead
entry (e.g. combine with an already-accepted trend-entry strategy) rather
than this iteration's speculative long-SMA-uptrend entry precondition.
