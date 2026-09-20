# 2026-09-20: Hikkake Pattern (Chesler false-breakout of an inside bar) — REJECTED

**Hypothesis:** Per https://oxfordstrat.com/trading-strategies/hikkake-pattern/
(Dan Chesler, CTM/CTA; original 42-futures-market backtest 1980-2014): a
two-bar false-breakout-of-an-inside-bar reversal pattern. Bullish Hikkake
(inside bar at i-1, then bar i makes a lower high AND lower low than the
inside bar -- a false breakdown) is a bear-trap expected to reverse up;
bearish is the mirror. Entry on a close breaking back through the inside
bar's high/low within `signal_window` bars; exit via time-stop or ATR
stop-loss (ATR(20)*6, per source defaults). Optional trend filter
(source's own sensitivity test found it "redundant").

**Source:** https://oxfordstrat.com/trading-strategies/hikkake-pattern/
(browser_exec; web_search failed for this query -- DDGS "No results found"
-- fell back to Google SERP via browser_exec).

**Grid test** (time_index in [10,15,25], atr_stop in [3.0,6.0], trend_index
in [0,50], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles, 144 cells):
- **pass_fraction: 0.097** (14/144)
- by_asset_class: equity 10/72, crypto 4/72
- by_vol_regime: low 13/48, mid 1/48, high **0/48**
- best_cell: QQQ low-vol, sharpe 1.66 (time_index=25, atr_stop=6.0,
  trend_index=50)
- worst_cell: SPY high-vol, sharpe -1.84

**Full-sample confirmation** at the grid's best config
(time_index=25, atr_stop=6.0, trend_index=50):

| Symbol | Trade transitions | Sharpe | MDD |
|---|---|---|---|
| QQQ | 37 | 0.077 (FAIL) | 0.206 (pass) |
| SPY | 29 | -0.407 (FAIL) | 0.302 (FAIL) |
| BTC/USDT | 77 | 0.281 (FAIL) | 0.875 (FAIL) |
| ETH/USDT | 84 | 0.476 (FAIL) | 0.714 (FAIL) |

All 4 symbols fail the Sharpe >= 1.0 validator at full sample; 3 of 4 also
fail MDD.

**Decision: REJECTED.** Grid pass_fraction 0.097 is decisively low with
0/48 high-vol cells passing at any config; full-sample confirmation fails
Sharpe on all 4 symbols and MDD on 3 of 4. The pattern's frequency is also
low (29-84 trade transitions over ~7.7 years), consistent with the source's
own note that this is a futures-market pattern originally tested across 42
diverse markets rather than a single equity/crypto pair, and their own
finding that the trend filter was largely redundant is consistent with what
we see here (trend_index=50 in the "best" cell didn't rescue full-sample
performance). Walk-forward/param-sensitivity/tx-cost validators skipped
given the decisive Sharpe failure across all symbols.

Strategy file (`strategies/2026-09-20_hikkake_false_breakout.py`) kept as a
record of a rejected attempt — not live.
