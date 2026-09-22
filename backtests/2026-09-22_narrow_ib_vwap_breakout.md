# 2026-09-22 — Narrow Initial-Balance (IB) Breakout, VWAP-Confirmed

**Hypothesis**: Source: https://algobars.com/strategy-templates/market-profile/ib-breakout/
(accessed 2026-09-22, browser_exec after web_extract refused ddgs-backend
extraction). The Initial Balance Breakout Market-Profile template: only
trade IB (first `ib_hours`-hour range) breakouts on days when the IB is
NARROW relative to its own trailing history (bottom `ib_narrow_pct`
percentile of `ib_lookback_days`-day IB-range history — "narrowest IB days
produce the strongest Trend Days"), confirmed by an upward-trending VWAP,
targeting `ib_target_mult`x the IB range beyond the breakout price.
Crypto-only (1h bars) — equity loader is daily-bar-only with no true IB
concept (same established constraint as prior ORB entries 2026-09-04-148,
2026-09-22 ATR/RVOL rescue).

**Strategy file**: `strategies/2026-09-22_narrow_ib_vwap_breakout.py`

**Grid test** (`run_grid_narrow_ib_vwap_breakout.py`): param_grid =
`{ib_narrow_pct: [0.15, 0.20, 0.30], ib_target_mult: [1.0, 1.5, 2.0]}`,
symbols = equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=108, passed_cells=0, pass_fraction=0.0
- by_asset_class: equity 0/54, crypto 0/54
- by_vol_regime: low 0/36, mid 0/36, high 0/36
- Equity cells are degenerate (daily bars → strategy's intraday IB logic
  produces null/near-zero signal series on daily data — same known
  daily-vs-1h mismatch as prior ORB entries). Crypto cells all fail on
  Sharpe/MDD (see below), not degenerate — genuine test of the hypothesis.

**Manual sweep (crypto, naive annualized Sharpe, no cost/vbt)**: across all
9 param combos x {BTC, ETH}, best raw Sharpe estimate was BTC
ib_narrow_pct=0.30/ib_target_mult=2.0 at ~0.86 (naive calc) — but the
validators.py/vectorbt Sharpe calc below is decisively lower.

**Single-config validators** (best config: `ib_narrow_pct=0.30`,
`ib_target_mult=2.0`, via `validation/validators.py`):

| Metric | BTC/USDT | ETH/USDT | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio (vectorbt, periods_per_year=8760) | 0.176 | 0.133 | ≥1.0 | FAIL (both) |
| Max drawdown | 0.397 | 0.481 | ≤0.25 | FAIL (both) |

Walk-forward / parameter-sensitivity / transaction-cost-survival not run —
decisive failure on the first two validators already rules out acceptance
(consistent with RESEARCH_LOOP.md Step 7 guidance to run at minimum
Sharpe + MDD; further validators would not change the reject decision).

**Decision**: REJECTED. Sharpe well below threshold and MDD nearly double
the 0.25 ceiling on both crypto symbols at the grid's best-performing
config; no equity signal (daily-bar mismatch). The "narrow IB → strong
trend day" premise from the source did not translate into a tradeable edge
on this repo's crypto 1h data at any tested narrowness/target combination.
