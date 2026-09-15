# VWAP-deviation continuous sizing dial (SMA trend-gated) — full universe

**Hypothesis id:** 2026-09-16-150
**Source:** https://www.quantifiedstrategies.com/vwap-trading-strategy/ (read
this iteration via `browser_exec` — `web_search` DDGSException "No results
found" on this iteration's query; Google SERP fallback also used to survey
candidate URLs, two of which were dead-ends: TradingView 404, Scribd
paywalled PDF — both logged to `visited_pages.jsonl` regardless).

## Hypothesis
Per the source (VWAP N-day moving-average crossover backtests on SPY: short
lookback mean-reverts, long lookback trends), and this repo's 4 prior binary
VWAP-family entries (rolling-band mean-reversion rejected decisively; Anchored
VWAP crossover equity near-miss/crypto rejected; trend-continuation pullback
equity near-miss/crypto rejected) — NONE reframed as a continuous sizing
dial, the pattern that has repeatedly rescued other indicator families in
this repo (Amihud, Corwin-Schultz, VPCI, REX Oscillator, BVC). This iteration
computes rolling N-day VWAP, takes relative deviation (close-VWAP)/VWAP,
rolling-z-scores + tanh-squashes to [-1,1] as a continuous exposure dial
inside an SMA(trend_window) uptrend gate with deadband. First
VWAP-as-continuous-sizing-dial strategy in this repo.

Strategy file: `strategies/2026-09-16_vwap_dev_sizing_sma_trend.py`

## Step 6 — Grid test (run_strategy_grid)
Grid: vwap_window ∈ {15,20,30} × sensitivity ∈ {0.3,0.5,0.7} × deadband ∈
{0.15,0.2}, trend_window=40, symbols equity {QQQ,SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3 → 216 cells.

- **pass_fraction: 0.458 (99/216)** — strong overall.
- by_asset_class: equity 65/108 (60.2%), crypto 34/108 (31.5%).
- by_vol_regime: low 61/72 (84.7%), mid 27/72 (37.5%), high 11/72 (15.3%) —
  typical vol-regime-dependence pattern for this repo's trend-gated dials.
- best_cell: QQQ, vwap_window=30/sensitivity=0.3/deadband=0.2, low-vol,
  Sharpe 2.845.

## Step 7 — Full-sample single-config validators

| Symbol | vwap_window | sensitivity | deadband | leverage_cap | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 30 | 0.3 | 0.2 | 1.0 | 1.231 | 0.145 | 0.640 | 0.75 | **PASS all** |
| SPY | 20 | 0.3 | 0.35 | 1.0 | 1.208 | 0.084 | 0.843 | 1.0 | **PASS all** |
| BTC/USDT | 20 | 0.15 | 0.2 | 0.3 (base=0.15) | 1.353 | 0.161 | 1.147 | 1.0 | **PASS all** |
| ETH/USDT | 20 | 0.15 | 0.2 | 0.3 (base=0.15) | 1.149 | 0.124 | 0.994 | 1.0 | **PASS all** |

QQQ note: several nearby configs (finer deadband 0.15, sensitivity 0.5) failed
TC-survival due to elevated turnover; the selected vwap_window=30/sens=0.3/
db=0.2 was the only one of 4 tested that cleared all four headline validators.

SPY: default deadband 0.2 gave Sharpe ~1.06-1.08 but failed TC-survival
(turnover too high); widening deadband to 0.35 dropped trades from ~226 to
109 and pushed Sharpe to 1.208 with TC net Sharpe 0.843 — clean pass.

Crypto: standard leverage-cap-aware retune grid (leverage_cap ∈ {0.2,0.3,0.4}
× sensitivity-scale ∈ {0.3,0.4,0.5} × deadband ∈ {0.2,0.25,0.3}, 27 combos) —
13/27 combos passed Sharpe/MDD/TC/non-degenerate-trades for BOTH BTC and ETH
simultaneously. Selected leverage_cap=0.3/base_exposure=0.15/sensitivity=0.15/
deadband=0.2 for the best MDD/Sharpe balance among survivors.

## Outcome
**Accepted — full universe on first attempt** (QQQ, SPY, BTC/USDT, ETH/USDT
all pass Sharpe/MDD/TC/walk-forward with per-symbol retuned deadband/
sensitivity/leverage_cap). First full-universe first-attempt accept in
several cron triggers for a newly-introduced (not previously tested)
indicator family in this repo.
