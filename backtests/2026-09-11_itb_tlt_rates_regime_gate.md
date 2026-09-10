# Backtest Report: ITB Homebuilders Trend-Following Gated by TLT Rates-Proxy Regime

**Strategy file:** `strategies/2026-09-11_itb_tlt_rates_regime_gate.py`
**Date:** 2026-09-11
**Sources:** https://www.google.com/search?q=homebuilder+ITB+XHB+mortgage+rates+10+year+treasury+yield+strategy+trading+rule (Yahoo Finance "What ITB Investors Need to Watch Before Mortgage Rates..." and general homebuilder-sector rate-sensitivity commentary synthesized via Google SERP)

## Hypothesis

Homebuilder stocks (ITB) are structurally sensitive to long-term interest
rates via mortgage affordability. Since TLT (long-duration Treasury ETF)
price moves inversely to long yields, a TLT uptrend (TLT close > its own
SMA) is a proxy for a favorable ("cheap financing") macro regime for
rate-sensitive sectors. This strategy gates a standard SMA trend-following
signal on the traded asset by requiring TLT to also be in an uptrend.
Tested on ITB (the direct rate-sensitive sector target), QQQ/SPY (broader
market controls -- should also benefit from a general "cheap money" tailwind
but less directly), and BTC/ETH (crypto falsification, no rate-sensitivity
mechanism expected). Distinct from every prior TLT-based repo strategy
(TLT/IEF duration ratio 2026-09-11-045, GLD/TLT ratio, SPY/TLT correlation
2026-09-05) since this pairs TLT's own absolute trend with a genuinely
rate-sensitive sector ETF rather than another ratio/correlation construct.

## Grid test summary (Step 6)

Grid: `trend_sma_window` in {50,100,150} x `tlt_sma_window` in {50,100,150},
vol_regime_splits=3, symbols equity={ITB,QQQ}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 23/54 cells passed (pass_fraction 0.426) -- the best
  pass_fraction of any strategy tested this cron trigger. By vol regime:
  low 14/18 (78%), mid 7/18 (39%), high 2/18 (11%) -- edge concentrated in
  calmer regimes but NOT exclusively (unlike the Dow Theory lineage's
  100%/0% split), still has some presence across all three terciles.
  Best cell: trend_sma_window=50, tlt_sma_window=50, QQQ, low-vol, Sharpe
  2.09. Worst: trend_sma_window=100, tlt_sma_window=150, QQQ, high-vol,
  Sharpe -0.57.
- **Crypto:** 0/54 cells passed (pass_fraction 0.0), confirming the
  falsification expectation.

## Single-config validation (Step 7): trend_sma_window=50, tlt_sma_window=50

| Validator | ITB | QQQ | SPY | Threshold |
|---|---|---|---|---|
| Sharpe ratio (full sample) | 1.093 ✅ | 1.019 ✅ | 0.845 ❌ | ≥ 1.0 |
| Max drawdown | 0.201 ✅ | 0.178 ✅ | 0.092 ✅ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.835 ✅ | 0.622 ✅ | 0.304 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.225 ✅ | 0.181 ✅ | 0.191 ✅ | ≤ 0.5 |

ITB (the direct sector target) and QQQ both clear every validator cleanly.
SPY is a near-miss -- Sharpe 0.845 and TC-survival fail (SPY's larger trade
count, 214, combined with its lower raw Sharpe erodes further under
costs), consistent with SPY's generally lower-beta/less rate-sensitive
profile relative to QQQ/ITB in this repo's historical pattern.

## Decision: ACCEPTED (ITB and QQQ); SPY near-miss rejected; crypto rejected decisively

ITB and QQQ both pass every validator at a shared config
(trend_sma_window=50, tlt_sma_window=50) -- no per-symbol tuning needed.
SPY remains a near-miss worth a future fine-tune iteration. Crypto rejected
decisively (0/54 grid cells), confirming no rate-sensitivity mechanism
applies there as expected.
