# Accumulative Swing Index (ASI) Price-Trend Confirmation — Backtest Report (2026-09-24)

## Hypothesis

J. Welles Wilder's Accumulative Swing Index (ASI) is designed as a
**confirmation tool**: "if price is rising and ASI is also rising, the
indicator is confirming the direction of the move" (source's own stated
use). This strategy operationalizes that idea mechanically: long when BOTH
price is above its own SMA(`trend_window`) AND the ASI line is above its
own SMA(`asi_trend_window`) — i.e. price and the Wilder swing-based
indicator agree the trend is up. Exit when either condition breaks, or a
`max_hold_days` time-stop.

Sources (both read via `browser_exec` this iteration after `web_search`'s
first query returned empty/no-results; subsequent `web_search` calls
worked normally):
- https://www.investopedia.com/terms/a/asi.asp (ASI concept, "positive ASI
  = uptrend confirmed" interpretation)
- https://alphasquawk.com/accumulative-swing-index-asi-an-in-depth-guide-for-traders/
  (exact Swing Index formula: SI = 50*[((C2-C1)+0.5(C2-O2)+0.25(C1-O1))/R]*(K/T);
  K = max(|H2-C1|,|L2-C1|); R depends on which of |H2-C1|,|L2-C1|,|H2-L2| is
  largest; ASI = cumsum(SI); explicit trading-use guidance on
  trend/breakout confirmation and divergence)

This is the **first Accumulative Swing Index / Wilder Swing Index strategy
in this repo** (0 prior `strategies_index.jsonl` hits for "Swing Index",
"ASI", or "Accumulative Swing").

**Limit-move value proxy**: the source explicitly notes stocks/ETFs/crypto
have no official exchange limit-move value the way futures do, and
instructs "if you use a proxy, document it." This implementation uses
`limit_move_pct * previous_close` (default 3%, swept 2%/3% in the grid) as
a documented non-futures proxy for T.

## Strategy file

`strategies/2026-09-24_asi_price_trend_confirmation.py`

## Grid test summary (Step 6)

144 cells: `trend_window ∈ {30, 50, 100}` × `asi_trend_window ∈ {10, 20}` ×
`limit_move_pct ∈ {0.02, 0.03}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}`
× 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.319 (46/144) |
| equity pass | 34/72 |
| crypto pass | 12/72 |
| low-vol pass | 34/48 |
| mid-vol pass | 10/48 |
| high-vol pass | 2/48 |
| best cell | QQQ low-vol, trend_window=50/asi_trend_window=20/limit_move_pct=0.02, Sharpe 2.83 |
| worst cell | QQQ high-vol, trend_window=100/asi_trend_window=20/limit_move_pct=0.02, Sharpe -0.79 |

QQQ configs concentrate at 0.67 pass_fraction (2/3 vol regimes) across most
of the grid; ETH/USDT decisively fails all 12 cells (0/12); BTC/USDT and
SPY sit at 0.33 (1/3, low-vol only).

## Single-config validation (Step 7) — best config: trend_window=50, asi_trend_window=20, limit_move_pct=0.02, max_hold_days=40

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.139 | FAIL 0.770 |
| Max Drawdown (<=0.25) | PASS 0.163 | PASS 0.208 |
| Transaction Cost Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 0.993 | PASS 0.581 |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.222 | PASS 0.190 |

QQQ: all 5/5 validators pass. SPY: 4/5 pass, Sharpe near-miss (0.770 vs
1.0 threshold) — decisively short, not a fine margin.

Crypto (BTC/USDT, ETH/USDT) not run through the single-config validator
suite given the grid's decisive rejection (BTC/USDT 0.33, ETH/USDT 0.0
pass fraction) — no config showed promise worth the extra validator run.

## Decision

**Accept for QQQ only.** Reject SPY (Sharpe fail) and crypto (grid
decisive fail). Strategy file and this report are kept; the log entry
records the narrow (QQQ-only) accepted scope explicitly.
