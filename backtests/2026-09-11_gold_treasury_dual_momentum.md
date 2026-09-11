# Backtest Report: Gold Cross-Asset Momentum (Gold + 10yr Treasury dual momentum) — REJECTED

**Strategy file:** `strategies/2026-09-11_gold_treasury_dual_momentum.py`
**Hypothesis ID:** 2026-09-11-082

## Hypothesis

Per QuantifiedStrategies.com's "7 Best Algo Trading Strategies for
Beginners"
(https://www.quantifiedstrategies.com/7-best-algo-trading-strategies-for-beginners/,
visited this iteration), the source's own disclosed "Gold Momentum
Strategy": go long GLD only when BOTH GLD's own trailing 12-month return
AND the 10-year Treasury proxy (IEF)'s trailing 12-month return are
positive; move to cash if either turns negative. Source's own claim:
annualized return 11.5% with max drawdown 31% vs buy-and-hold gold's
higher return but 64% max drawdown over 5 decades — i.e. the edge is
claimed to be drawdown reduction, not return enhancement, and the source
itself notes the advantage "waned" since ~2002.

## Single-config validator results (GLD, lookback_days=189, min_hold_days=10; 2016-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ (narrow) | 1.015 | ≥ 1.0 |
| Max drawdown | ✅ | 0.192 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 16 trades) | ✅ | net Sharpe 0.999 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | ❌ | 2/4 splits positive (0.5) | ≥ 0.75 pass fraction |
| Parameter sensitivity (9-combo grid: lookback∈{189,252,315}d × min_hold∈{1,5,10}d) | ✅ | relative_std 0.298 | ≤ 0.5 |

**Walk-forward fails decisively** — confirmed on a second nearby config
(lookback_days=189, min_hold_days=5: Sharpe 1.064, same 2/4 walk-forward
result) — this is not a borderline/near-miss single-config artifact, the
failure is consistent across the two best-performing param combos in the
grid.

## Step 6 grid summary (param_grid lookback_days=[189,252,315] x min_hold_days=[1,5,10], symbols equity=[GLD,QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2016-01-01 to 2026-09-01)

- total_cells=135, passed=37, **pass_fraction=0.274**
- by_asset_class: equity 37/81 pass, crypto **0/54 decisive reject**
- by_vol_regime: low 27/45, mid 10/45, **high 0/45 decisive fail** — the
  dual-momentum gate provides ZERO high-vol-regime protection across every
  parameter combo and every equity symbol tested, directly contradicting
  the source's own drawdown-reduction thesis for exactly the regime
  (crisis/high-vol) where it matters most.
- best_cell: GLD, lookback=252, min_hold=10, low-vol, Sharpe 2.66
- worst_cell: GLD, lookback=315, min_hold=5, high-vol, Sharpe -0.37

## Decision: REJECTED

Full-sample Sharpe narrowly clears 1.0 on the best config, but walk-forward
robustness fails decisively (2/4 out-of-sample chunks negative Sharpe) on
both of the two best-performing parameter combos, and the grid's own
by_vol_regime breakdown shows 0/45 passes in the high-vol tercile across
the ENTIRE grid — directly falsifying the source's central claim that this
dual-momentum construction reduces drawdown risk precisely when volatility
spikes. The narrow full-sample Sharpe pass appears to be driven by a
handful of favorable low-vol-regime periods rather than a robust,
regime-agnostic edge.

## Notes

- Source: https://www.quantifiedstrategies.com/7-best-algo-trading-strategies-for-beginners/
  (visited this iteration, first read of this URL).
- Novel indicator-family combination for this repo: no prior strategy
  gates GOLD using a TREASURY BOND's own absolute momentum as a
  confirming co-signal (verified via strategies_index.jsonl keyword search
  for "gold treasury 12 month" / "dual momentum gold" — zero matches).
- The min_hold_days smoothing (added here, not in the source's own rule)
  did not rescue walk-forward robustness across the values tested
  (1/5/10 days) — the underlying signal itself, not noise around the
  zero-crossing, appears to be the limiting factor.
- Worth a future revisit: try the source's own likely MONTHLY check
  cadence (not daily with min-hold smoothing) exactly as described, or
  test whether adding a stricter minimum-momentum-magnitude threshold
  (not just sign) improves the high-vol-regime failure.
