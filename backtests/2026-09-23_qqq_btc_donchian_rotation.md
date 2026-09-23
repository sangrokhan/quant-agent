# QQQ/SPY-BTC Donchian Breakout Rotation (Variant A: Equity-First) — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_qqq_btc_donchian_rotation.py`
**Outcome:** ACCEPTED (QQQ and SPY, all 5 validators pass at `lookback=20`)

## Hypothesis + source

Per Radovan Vojtko & Cyril Dujava's Quantpedia/SSRN paper "Silicon vs.
Satoshi: Tactical Asset Rotation Between NASDAQ-100 and Bitcoin"
(https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/,
SSRN abstract=7055018, read via `browser_exec` this iteration —
`web_search`'s DDGS backend returned low-quality Korean-localized SERP
snippets for the discovery queries, so the detail read went via
`browser_exec` directly to the Quantpedia blog page), Bitcoin and NASDAQ-100
tech stocks compete for the same finite pool of retail attention/speculative
capital. The paper's own disclosed signal: for lookback window `w`, upper
channel = max(close over the trailing `w` bars, excluding today);
breakout fires when today's close exceeds that bound. Three-state rotation
(**Variant A**, the paper's own risk-adjusted-preferred ordering): hold the
equity leg if it's breaking out; else hold BTC if IT's breaking out; else
100% cash. Genuinely novel in this repo: first cross-asset rotation
strategy (equity vs crypto vs cash three-state allocation, as opposed to a
single-instrument entry/exit rule or same-asset-class dual-momentum vote).

## Implementation notes

This repo's `generate_returns_fn` contract is per-symbol (single `price_df`
in), so `price_df` is treated as the equity leg (QQQ/SPY); the crypto leg
is always BTC/USDT, fetched internally via `data/loaders.py`'s
`load_crypto` and forward-filled onto the equity leg's trading-day index
(matching the paper's own continuous-BTC-onto-equity-calendar alignment
methodology). Signal computed on day t's close is shifted 1 day before
being applied to returns (no look-ahead).

## Grid summary (Step 6)

`run_strategy_grid`: `param_grid={lookback:[10,20,30]}` (spanning the
paper's own tested 5-50 day range, narrowed per `suggested_workload=normal`),
`symbols={equity:[QQQ,SPY]}` (crypto asset-class slot intentionally
skipped — this strategy is architecturally equity-vs-BTC-vs-cash, not a
generic single-instrument strategy that can be re-run with a crypto
symbol as the primary leg), `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 18 cells total.

- **pass_fraction: 0.722** (13/18) — exceptionally broad for this KB
- **by_asset_class:** equity 13/18 (only asset class tested by design)
- **by_vol_regime:** low 5/6; mid 2/6; **high 6/6** — the cash-fallback
  mechanism appears to actively help MOST in high-vol regimes (matches the
  paper's own finding that the drawdown-compression benefit comes
  specifically from retreating to cash during consolidation/stress)
- **best_cell:** QQQ, lookback=20, high-vol tercile, Sharpe 2.05
- **worst_cell:** SPY, lookback=30, low-vol tercile, Sharpe 0.90 (still a
  reasonable Sharpe, just below the grid's 1.0 pass bar)

## Single-config validators (QQQ, SPY; `lookback=20`, 2019-01-01 to 2026-09-01)

| Validator | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.651 | 1.221 | >= 1.0 | **PASS** (both) |
| Max drawdown | 0.174 | 0.169 | <= 0.25 | PASS (both) |
| TC survival (10bps/trade, 234/259 trades) | 1.389 | 0.928 | >= 0.5 | **PASS** (both) |
| Walk-forward (4 manual date splits — `vbt.utils.splitting.RangeSplitter` still broken in installed vectorbt, same repo-wide workaround used since 2026-09-03) | 4/4 splits positive (1.0) | 4/4 splits positive (1.0) | >= 0.75 | PASS (both) |
| Parameter sensitivity (lookback 10/20/30 grid-mean Sharpe relative std) | 0.038 | 0.069 | <= 0.5 | PASS (both) |

## Decision (Step 8): ACCEPT (QQQ, SPY)

All 5 validators pass cleanly on both equity legs, with a notably high grid
pass_fraction (0.722) and low parameter sensitivity (relative std ~0.04-0.07,
among the cleanest in this repo's history) — the strategy is robust across
the 10/20/30-day lookback range, matching the paper's own finding of "a
robust plateau across the 5-30 day range." The high number of trades
(234-259 over 7.7 years, ~30/year) reflects the strategy's frequent
rotation between legs and cash, but TC survival still passes comfortably
even at a conservative 10bps/trade assumption. First accepted cross-asset
(equity-vs-crypto-vs-cash) rotation strategy in this repo.

Not tested this iteration: `lookback` values beyond 10-30 (paper's wider
5-50 range), Variant B (BTC-first priority — paper reports this as inferior
on a risk-adjusted basis, kept for a possible future iteration), and
crypto-leg-as-primary variants (architecturally different construction,
would need a separate strategy file).
