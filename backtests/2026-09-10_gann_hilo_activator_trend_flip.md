# Gann HiLo Activator trend-flip (long-only)

**Hypothesis source:** https://trendsandbreakouts.com/gann-hilo-activator
Gann HiLo Activator state machine: `HMA(n) = SMA(High,n)`, `LMA(n) =
SMA(Low,n)`; if `Close > prior HMA(n)`, state -> uptrend; if
`Close < prior LMA(n)`, state -> downtrend; otherwise hold prior state.
This strategy trades the state flip itself: long while state=uptrend,
flat while state=downtrend (or after `max_hold_days` time-stop).

## Grid test (Step 6)

`param_grid={"n": [5,8,13], "max_hold_days": [20,40]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 20/72 = 0.278**
- By asset class: equity 20/36 (0.56), crypto 0/36 (0.0) — decisive crypto rejection
- By vol regime: low 12/24, mid 6/24, high 2/24
- Best cell: QQQ, low-vol, n=13/max_hold_days=20, Sharpe 2.22
- Worst cell: QQQ, high-vol, n=5/max_hold_days=20, Sharpe -0.72

## Full-sample validator suite (Step 7), config n=13/max_hold_days=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.074 ✅ | 0.979 ❌ (near-miss) |
| Max drawdown (<=0.25) | 0.270 ❌ (near-miss) | 0.177 ✅ |
| Tx-cost survival (net Sharpe >=0.5, 10bps/trade) | 0.939 ✅ | 0.807 ✅ |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ (3/4) | 0.75 ✅ (3/4) |
| Parameter sensitivity (relative std <=0.5) | 0.436 ✅ | 0.349 ✅ |

QQQ: 101 trades over 7.7yr, fails only MDD (0.270 vs 0.25 threshold, razor-
thin miss). SPY: 97 trades, fails only Sharpe (0.979 vs 1.0, razor-thin miss).

## Decision

**Reject** for both QQQ and SPY at the shared config — each fails exactly
one validator by a very narrow margin (QQQ's MDD 0.270 vs 0.25 threshold;
SPY's Sharpe 0.979 vs 1.0 threshold). Neither symbol clears all 5
validators at the same parameter setting. Crypto rejected decisively
(0/36 grid cells) — the state machine's High/Low-SMA basis appears to
whipsaw excessively in crypto's higher-volatility 24/7 regime. Worth
revisiting in a future iteration with either a tighter max_hold_days (to
reduce QQQ's drawdown exposure) or a volatility-regime gate (grid shows
this strategy only really works in low/mid-vol regimes, 18/48 there vs
2/24 in high-vol) rather than trading unconditionally through all regimes.
