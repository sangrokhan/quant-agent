# Regime-conditional 12-1/12-0 skip-month momentum switch — REJECTED

**Hypothesis source:** Dikhit (Jan 2026), "The Informational Role of the Most
Recent Month in Industry-Level Momentum Strategies", summarized by Larry
Swedroe / Alpha Architect via IBKR Quant News:
https://www.interactivebrokers.com/campus/ibkr-quant-news/the-skip-month-mystery-what-last-months-returns-are-really-telling-you/
(read via `browser_exec`, `web_extract` unavailable on this backend).

Fama-French 48-industry study (1975-2024) found the classic 12-1 skip-month
momentum construction outperforms in "Stable Trend" regimes (2.32%/mo) but
degrades in "Stress/Crash" regimes (0.94%/mo) where the 12-0 (include-month)
variant does better (1.35%/mo). Strategy adapts this to a single-asset daily
signal: use 12-1 momentum when trailing realized vol is calm, switch to 12-0
momentum when trailing realized vol is elevated, gated by an SMA(200) trend
filter, rebalanced ~monthly (21 trading days).

## Grid test (Step 6)

`vol_regime_ratio ∈ {0.9, 1.1, 1.3} × trend_window ∈ {150, 200}`,
symbols = QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3
(low/mid/high realized-vol terciles), 72 total cells.

- **pass_fraction: 0.25** (18/72 cells passed Sharpe/MDD)
- **by_asset_class:** equity 18/36 passed; **crypto 0/36 passed** (strategy
  entirely fails on crypto — no crypto cell survives)
- **by_vol_regime:** low-vol 12/24, mid-vol 6/24, **high-vol 0/24** — the
  edge is concentrated almost entirely in the low-vol tercile, which is the
  opposite of what would make the regime-switch component (specifically
  meant to rescue high-vol performance) actually add value; the high-vol
  regime is a decisive 0% pass rate across all params/assets.
- **best_cell:** SPY, vol_regime_ratio=0.9/trend_window=200, low-vol
  tercile, Sharpe 2.56
- **worst_cell:** SPY, vol_regime_ratio=0.9/trend_window=150, mid-vol
  tercile, Sharpe 0.02

## Single-config validation (Step 7) — SPY, vol_regime_ratio=0.9, trend_window=200

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period 2019-2026) | 0.591 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.341 | ≤ 0.25 | **FAIL** |
| Transaction-cost survival (10bps/trade, 9 trades) | net Sharpe 0.581 | ≥ 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual — `vbt.utils.splitting.RangeSplitter` unavailable in installed vectorbt, known pre-existing repo issue) | 2/4 splits positive (0.50) | ≥ 0.75 | **FAIL** |
| Parameter sensitivity (24-cell vol_regime_ratio×trend_window sweep) | relative_std 0.056 | ≤ 0.5 | PASS |

## Verdict: REJECTED

The grid-level "best cell" Sharpe (2.56) is a cherry-picked single vol
tercile, not representative of full-period performance — the whole-period
single-config Sharpe (0.591) and MDD (0.341) both fail decisively, and
walk-forward robustness fails (only 2/4 splits profitable). The
regime-switching mechanism itself is not vindicated: the strategy's edge is
concentrated in the LOW-vol tercile, not rescued in the high-vol tercile as
the source paper's own finding would predict (12-0 fallback should help
there) — high-vol pass rate is a decisive 0/24. Crypto fails entirely
(0/36). The monthly-rebalance daily-bar adaptation of the source's discrete
calendar-month construction may itself be imprecise, but the more
fundamental finding is that this construction does not add value over the
already-tested plain 12-1 momentum (2026-09-09-032, also rejected) for
single-asset daily-bar trading.
