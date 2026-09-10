# Backtest Report: QQQ Trend-Following Gated by TIP (Real-Yield Proxy) Regime

**Strategy file:** `strategies/2026-09-11_gld_tip_realyield_gate.py`
**Date:** 2026-09-11
**Source:** Google SERP synthesis of "Gold vs Real Yields: Why TIPS Are Pressuring Gold Again" and general real-yield/gold inverse-relationship commentary

## Hypothesis (as originally framed, GLD-focused)

Gold (GLD) is structurally sensitive to real interest rates: rising real
yields raise the opportunity cost of holding non-yielding gold. TIP price
moves inversely to real yields (like TLT for nominal yields), so a TIP
uptrend is a proxy for a favorable gold regime. Gate a standard SMA
trend-following signal on GLD by requiring TIP to also be in an uptrend.
QQQ/SPY were tested as broader-market controls.

## Grid test summary (Step 6)

Grid: `trend_sma_window` in {30,50,100} x `tip_sma_window` in {30,50,100},
vol_regime_splits=3, symbols equity={GLD,QQQ}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 29/54 cells passed (0.537 pass_fraction -- the BEST of any
  strategy tested this cron trigger). By vol regime: low 18/18 (100%), mid
  11/18 (61%), high 0/18 (0%). Best cell: trend_sma_window=30,
  tip_sma_window=50, **GLD** (not QQQ), low-vol, Sharpe 3.06 -- the single
  best-cell number belongs to GLD, but as with 2026-09-11-058, the
  full-sample validator behaves differently.
- **Crypto:** 0/54 cells passed, falsification confirmed.

## Single-config validation at trend_sma_window=30, tip_sma_window=50

| Validator | GLD | QQQ | SPY | Threshold |
|---|---|---|---|---|
| Sharpe ratio (full sample) | 0.492 ❌ | 1.452 ✅ | 0.893 ❌ | ≥ 1.0 |
| Max drawdown | 0.196 ✅ | 0.117 ✅ | 0.107 ✅ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.241 ❌ | 1.099 ✅ | 0.456 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.281 ✅ | 0.061 ✅ | 0.090 ✅ | ≤ 0.5 |

## Decision: ACCEPTED (QQQ only); rejected (GLD, decisive; SPY, near-miss); crypto rejected decisively

Another instance of the pattern seen in 2026-09-11-058: the real-yield-proxy
gate (TIP uptrend) is a strong signal for QQQ specifically (Sharpe 1.452,
all validators pass comfortably, including a robust net-of-cost Sharpe
1.099), but does NOT work for the originally-hypothesized target (GLD
itself, decisive Sharpe/TC failure) or for SPY (near-miss, worth a possible
future fine-tune). This likely reflects that falling real yields are more
directly a tech/growth-equity valuation tailwind (long-duration cash-flow
discounting) than a gold-specific mechanism -- gold's price action is
apparently driven by other factors (dollar strength, central bank buying,
geopolitical risk) that this simple TIP-trend gate doesn't capture well
enough to produce a clean, consistently-timed edge on GLD itself. Recorded
honestly per RESEARCH_LOOP.md guidance.
