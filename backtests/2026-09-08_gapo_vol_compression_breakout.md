# Gopalkrishnan Range Index (GAPO) Volatility-Compression Breakout — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_gapo_vol_compression_breakout.py` | **Outcome: ACCEPTED (QQQ only); near-miss (SPY); rejected (crypto)**

## Hypothesis
Per gocharting.com's GAPO docs (browser_exec fallback — first web_search
query returned unrelated "happy" synonyms results from a stale DDG cache;
a corrected second query surfaced the right sources), GAPO=ln(HH(n)-LL(n))/
ln(n) is a log-normalized range-volatility gauge. Source's explicit
strategy: "When GAPO drops to historical lows, anticipate a volatility
expansion. Set breakout entries above recent highs and below recent lows,
entering whichever side breaks first. Use a wider stop during high GAPO
periods." Long-only implementation (SAFETY.md): enter on a Donchian
breakout while GAPO is in its own historical-low percentile band; exit on
an ATR-scaled trailing stop that ratchets up with the running max close
(auto-widening if realized volatility increases post-entry, honoring the
source's caution) or a max_hold_days time-stop.

Source: https://gocharting.com/docs/charting/technical-indicator/oscillators/gopalkrishnan-range-index
Also read: https://theforexgeek.com/gopalakrishnan-range-index (corroborating breakout-after-compression framing; https://www.stockmaniacs.net/gopalakrishnan-range-index-gapo/ blocked by Cloudflare, formula confirmed via search snippet instead)

## Grid test (gapo_pct_threshold=[0.15,0.2,0.3] x atr_mult=[2.0,2.5,3.0], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 108 cells total, 22 passed (pass_fraction 0.204)
- By asset class: equity 22/54, crypto 0/54 (decisive fail)
- By vol regime: low 12/36, mid 10/36, high 0/36
- Best cell: gapo_pct_threshold=0.15/atr_mult=3.0, QQQ mid-vol, Sharpe 2.51
- Best avg-across-regime config: gapo_pct_threshold=0.3/atr_mult=2.5, QQQ avg Sharpe 1.18, SPY same config avg Sharpe 0.86

## Single-config validators (shared config: gapo_pct_threshold=0.3, atr_mult=2.5, gapo_window=14, gapo_lookback=100, donchian_window=20, atr_window=14, max_hold_days=40)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | **1.144 PASS** | 0.884 near-miss | >= 1.0 |
| Max Drawdown | **0.129 PASS** | 0.096 PASS | <= 0.25 |
| TC survival (10bps) | **1.098 PASS** | 0.810 PASS | >= 0.5 |
| Walk-forward (4-split manual) | **1.00 PASS** | 1.00 PASS | >= 0.75 |
| Parameter sensitivity | **0.053 PASS** | 0.278 PASS | <= 0.5 |
| Trade count | 24 | 25 | n/a (informational, healthy sample) |

Crypto context (same shared config): BTC/USDT Sharpe 0.178, ETH/USDT Sharpe
0.212 — clear fail.

## Verdict
**ACCEPTED for QQQ (shared config with SPY).** All five validators pass on
QQQ with a healthy 24-trade sample, low max drawdown (12.9%), and a
remarkably tight parameter-sensitivity relative std (0.053 — the tightest
of any strategy logged in this repo recently), indicating this result is
not a fragile cherry-pick. SPY is a genuine near-miss (Sharpe 0.884,
everything else passes) and is left un-deployed/rejected pending a
possible SPY-specific parameter retune in a future iteration; note in
knowledge base for that purpose. Crypto rejected decisively (0/54 grid
cells, full-sample Sharpe 0.18-0.21). Scope: equity only, QQQ config live.
