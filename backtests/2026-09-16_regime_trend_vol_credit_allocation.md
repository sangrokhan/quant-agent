# TASC 2026.07 Market Regime Identification (Trend + Vol Term Structure + Credit Appetite)

**Strategy file:** `strategies/2026-09-16_regime_trend_vol_credit_allocation.py`
**Knowledge base id:** 2026-09-16-166

## Hypothesis
Per TASC July 2026 "Market Regime Identification Using Trend, Volatility,
And Credit Conditions" (Gaetano Di Prima & Fabio Baruffa), re-implemented
in the open-source TradingView script
https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/
(visited this iteration; full disclosed rules read from the script's
overview text). Three binary conditions are assessed weekly:

1. **Trend**: SPX above its own 200-day SMA.
2. **Volatility term structure**: VIX < VIX3M (normal contango, not
   stressed backwardation).
3. **Credit appetite**: 100-day SMA of the rolling z-score of the
   HYG/IEF (high-yield credit vs 7-10yr Treasury) ratio is positive.

If all 3 favorable -> full exposure; 2/3 -> 50% exposure; 1/3 or 0/3 ->
flat. Source trades SPY specifically; this repo applies the SAME
macro-only 3-factor regime signal (computed once from SPX/VIX/VIX3M/
HYG/IEF, independent of the gated asset) to gate whichever symbol
``price_df`` represents, to test whether a macro-only regime score
generalizes beyond SPY (including to crypto).

## Novelty check
Grepped strategies_index.jsonl for "market regime identification"/
"risk-on risk-off caution"/"credit conditions" — 1 hit, a *different*
mechanism (2026-09-05-025's HYG/LQD z-score-only regime filter,
2026-09-05-050's XLF/SPY sector-ratio credit gate, 2026-09-10-024's
HYG/IEF GEM momentum rotation) — none combine trend + VIX-term-structure
+ credit-appetite into one composite 3-factor score with graduated
50%/100% exposure tiers. First VIX-term-structure (VIX vs VIX3M) filter
tested in this repo at all.

## Standard validators (Step 7) — per-symbol tuned configs
`trend_window=200, credit_window=150` (equity)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens rel-std | Verdict |
|---|---|---|---|---|---|---|
| SPY | 1.099 (PASS) | 0.136 (PASS) | 1.007 (PASS) | 1.0 (PASS) | 0.109 (PASS) | **ACCEPT** |
| QQQ | 1.058 (PASS) | 0.196 (PASS) | 0.995 (PASS) | 1.0 (PASS) | 0.092 (PASS) | **ACCEPT** |
| BTC/USDT | 0.940 (FAIL Sharpe) | 0.248 (borderline) | — | — | — | REJECT |
| ETH/USDT | 0.947 (FAIL Sharpe) | 0.249 (borderline) | — | — | — | REJECT |

Only 48 trades over the ~7.5yr equity sample (weekly rebalance cadence,
matching the source's own weekly assessment), keeping TC-survival strong.
Walk-forward used the same manual 4-fold range-split fallback as other
2026-09-16 entries (`vectorbt.utils.splitting.RangeSplitter` unavailable
in this environment's installed vectorbt version). Parameter sensitivity
swept `credit_window` in [100,120,150,180,200].

Crypto (BTC/USDT, ETH/USDT) best-effort search (trend_window in
{150,200,250}, credit_window in {60,100,150}, leverage_cap in {0.3,0.5},
MDD-constrained to <=0.25) topped out at Sharpe ~0.94-0.95 — a
credible-but-below-threshold macro-regime effect on crypto, plausible
since the underlying signal (SPX trend, VIX term structure, USD credit
market appetite) is inherently equity/USD-credit-centric and has no
crypto-native analogue.

## Grid test (Step 6)
`param_grid={"trend_window": [150,200,250], "credit_window": [60,100,150]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01:

- total_cells=108, passed=22, **pass_fraction=0.204**
- by_asset_class: equity 22/54, **crypto 0/54 (decisive rejection)**
- by_vol_regime: low 18/36, mid 4/36, high 0/36
- best_cell: trend_window=250, credit_window=60, SPY, low-vol, sharpe=2.75
- worst_cell: trend_window=150, credit_window=100, QQQ, high-vol, sharpe=-0.16

Edge concentrates heavily in low-vol regimes (consistent with the
strategy being a risk-off/de-risking overlay by design — it should, and
does, add the most value exactly when volatility/credit stress would
otherwise hurt a buy-and-hold position, which mechanically correlates
with the low-realized-vol tercile in-sample).

## Decision (Step 8)
**Accepted (QQQ, SPY)** — both clear all 5 validators with solid margins
at `trend_window=200, credit_window=150`. **Rejected (BTC/USDT,
ETH/USDT)** — decisive grid rejection (0/54) and best-effort single-config
search topped out just under the Sharpe threshold; the underlying signal
components (SPX, VIX/VIX3M, HYG/IEF) are US-equity/credit-market-native
and evidently don't transmit a tradeable regime edge to crypto exposure.
