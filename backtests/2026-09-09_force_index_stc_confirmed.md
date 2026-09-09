# Force Index(2)+STC(50) Confirmed (QQQ accepted; SPY rejected)

**Strategy file:** `strategies/2026-09-09_force_index_stc_confirmed.py`
**Knowledge base id:** 2026-09-09-086

## Hypothesis + source

Per AlphaX Trading's Force Index quant-library page (surfaced via Google
search snippet, browser_exec fallback): "Enter a long position when the
2-period Force Index crosses above the zero line, provided the primary
trend is confirmed by the STC." Combines the fast 2-period Force Index
zero-line cross as the entry trigger with Schaff Trend Cycle (STC)>50 as
the trend-confirmation gate. Distinct from all prior Force Index strategies
in this repo (dual-EMA pullback 2026-09-04-049, divergence 2026-09-05-048,
MACD-histogram triple-screen 2026-09-09-007) -- first to pair FI with STC.

## Grid test (Step 6)

`param_grid={"fi_span": [2,3], "max_hold_days": [10,20]}`, symbols QQQ/SPY
(equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`, 2019-01-01 to
2026-09-01:

- **pass_fraction: 0.333** (16/48 cells) -- strong pass rate
- by_asset_class: equity 16/24, crypto 0/24 (decisive crypto rejection)
- by_vol_regime: low 8/16, mid 4/16, high 4/16 -- robust across all regimes

## Single-config validators (Step 7), config: fi_span=2, max_hold_days=10

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **1.051 PASS** | 0.705 FAIL |
| Max drawdown (<=0.25) | 0.110 PASS | 0.074 PASS |
| Transaction-cost survival (net Sharpe >=0.5) | 0.671 PASS | 0.254 FAIL |
| Walk-forward (4 splits, >=75% positive) | 4/4 PASS | 4/4 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.062 PASS | 0.030 PASS |

QQQ: all 5 validators pass. SPY: 3/5 pass -- Sharpe (0.705) and
transaction-cost survival (0.254) both fail, driven by a high trade count
(159 trades over 7.7yr) that erodes net returns after the 10bps/trade cost
assumption.

## Decision

**Accept for QQQ only.** Reject SPY (decisive Sharpe + TC-survival fail from
overtrading). Crypto rejected decisively (0/24 grid cells).
