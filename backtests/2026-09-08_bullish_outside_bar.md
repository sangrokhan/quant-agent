# Bullish Outside Bar Reversal

**Hypothesis:** Per https://journalplus.co/patterns/outside-bar-pattern/, a
bullish Outside Bar (today's high/low fully engulf yesterday's including
wicks, close in the upper 40% of today's range, volume >=1.5x 20-day
average) is a stricter/more-reliable variant of a bullish engulfing
candle. Long entry at close of the qualifying bar; stop below the bar's own
low; target = the bar's own range projected up from close (measured move);
15-day time-stop otherwise. First full-range-engulf Outside Bar strategy
in this repo, distinct from body-only Bullish Engulfing and the
gap-required Bullish Kicker (already tested).

**Strategy file:** `strategies/2026-09-08_bullish_outside_bar.py`

## Grid test (Step 6)

`param_grid={"close_position_pct": [0.55, 0.60, 0.70], "volume_mult": [1.2, 1.5]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 72 total cells, 3 passed (pass_fraction=0.042) -- decisive fail
- By asset class: equity 3/36, crypto 0/36
- By vol regime: low 3/24, mid 0/24, high 0/24
- Best cell: SPY, close_position_pct=0.55/volume_mult=1.5, low-vol regime, Sharpe 1.08
- Worst cell: QQQ, close_position_pct=0.60/volume_mult=1.2, mid-vol regime, Sharpe -0.47

## Single-config validators (Step 7) -- best config close_position_pct=0.55/volume_mult=1.5

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe | 0.369 FAIL | 0.096 FAIL |
| Max drawdown | 5.0% PASS | 8.3% PASS |
| TC-survival (10bps) | 0.337 FAIL | 0.069 FAIL |
| num_trades | 7 | 8 |

## Decision (Step 8)

**Reject.** Grid pass_fraction only 4.2% (3/72), decisively weak. The
compound entry filter (full-range engulf + upper-40% close + 1.5x volume)
is so restrictive that only 7-8 qualifying trades occur over the entire
7.7-year sample on either equity symbol -- far too sparse for a reliable
edge, and the full-sample Sharpe (0.37/0.10) confirms no exploitable signal
survives outside the isolated low-vol grid cell. Crypto rejected
decisively (0/36 cells).
