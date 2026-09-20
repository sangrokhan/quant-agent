# 2026-09-20 — Laguerre RSI + ADX Trend-Strength Filter

## Hypothesis

Per Sword Red's "Laguerre RSI with ADX Filtered Trading Signals Strategy"
(https://medium.com/@redsword_23261/laguerre-rsi-with-adx-filtered-trading-signals-strategy-cb7ab0c02694,
read via `browser_exec` fallback after `web_extract`'s DDGS backend refused
extraction — "search-only backend and cannot extract URL content"), a fast
momentum oscillator (4-stage recursive Laguerre filter → RSI-style [0,1]
oscillator) crossing above a `buy_level` signals a momentum shift worth
trading LONG, but only when `ADX > adx_level` confirms the market is
actually trending — filtering out false crossovers in choppy/range-bound
conditions. Exit on the Laguerre RSI crossing back below `sell_level`, ADX
dropping back to/below `adx_level` (trend confirmation lost), or a
`max_hold_days` time-stop backstop.

Novelty: this repo has 15+ prior Laguerre RSI entries (oversold-recovery,
zero-line regime, continuous-sizing variants) but none combine it with an
ADX trend-strength confirmation gate — a distinct dual-indicator
confirmation design vs. a standalone threshold trigger.

Strategy file: `strategies/2026-09-20_laguerre_rsi_adx_filter.py`

## Grid test (Step 6)

`param_grid={"buy_level": [15,20,25], "adx_level": [15,20,25], "alpha": [0.2,0.3]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3` → 216 cells total.

- **pass_fraction: 0.269** (58/216)
- **by_asset_class:** equity 55/108 (51%) — crypto 3/108 (3%)
- **by_vol_regime:** low 29/72 (40%) — mid 17/72 (24%) — high 12/72 (17%)
- **best_cell:** QQQ, mid-vol, `buy_level=15, adx_level=20, alpha=0.3`, Sharpe=2.22
- **worst_cell:** BTC/USDT, low-vol, `buy_level=25, adx_level=20, alpha=0.3`, Sharpe=-1.11
- **best full-sample config (aggregated across vol regimes and both equity symbols):**
  `buy_level=25, adx_level=20, alpha=0.2` (6/12 cells pass)

This strategy holds up broadly on equity (across roughly half the vol
regimes / param combos) but is essentially non-functional on crypto —
scope should be recorded as equity-only.

## Single-config validation (Step 7) — `buy_level=25, adx_level=20, alpha=0.2`

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (≥1.0) | **1.097 — PASS** | 0.933 — FAIL |
| Max drawdown (≤0.25) | 0.099 — PASS | 0.048 — PASS |
| Transaction cost survival (net Sharpe ≥0.5, 10bps/trade) | 1.036 — PASS | 0.823 — PASS |
| Walk-forward (4 splits, ≥75% positive-Sharpe splits) | 0.75 (3/4) — PASS | 1.0 (4/4) — PASS |
| Parameter sensitivity (relative std ≤0.5) | 0.212 — PASS | 0.185 — PASS |

Note: `validators.check_walk_forward`'s `vbt.utils.splitting.RangeSplitter`
raised `AttributeError` (API removed from the installed vectorbt version —
a pre-existing repo-wide issue noted in prior iterations). Used a manual
4-way contiguous date-slice walk-forward fallback matching the documented
intent (same pass criterion: ≥75% of splits with positive Sharpe).

## Decision (Step 8)

**Accept for QQQ** (all 5 validators pass). **Reject/near-miss for SPY**
(only Sharpe fails, by a small margin: 0.933 vs 1.0 threshold — everything
else, including walk-forward robustness, passes cleanly). Strategy file
kept in `strategies/` as a QQQ-scoped accepted strategy; SPY near-miss is a
good candidate for a future direct-fix sub-iteration (e.g. retune
`buy_level`/`adx_level` specifically for SPY, following this repo's
established near-miss-rescue pattern). Crypto (BTC/USDT, ETH/USDT) is
decisively out of scope per the grid (3/108 cells pass) — do not deploy
this strategy on crypto without a substantial redesign.
