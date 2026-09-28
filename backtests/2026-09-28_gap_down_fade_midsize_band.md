# Gap-Down Fade, Mid-Size Band — 2026-09-28

**Hypothesis:** Direct retune of prior near-miss `2026-09-03-010` (plain
minimum-threshold gap-down fade, rejected). Add an upper gap-size bound
(`gap_max_threshold`) alongside the existing lower bound
(`gap_min_threshold`), restricting entries to a mid-size gap-down band, per
pomegra.io's gap-size/fill-probability claims (1-3% gaps fill 60-80% of the
time; >5% gaps fill only 30-50%, "real" repricings).

**Source:** https://pomegra.io/wiki/overnight-gap-trading-strategy/ (read
via `browser_exec`; `web_extract` cannot extract content on this backend).

## Grid test

48 cells: `gap_min_threshold` in [0.01, 0.015] x `gap_max_threshold` in
[0.03, 0.05], equity [QQQ, SPY] + crypto [BTC/USDT, ETH/USDT],
`vol_regime_splits=3`.

- **pass_fraction: 0.125** (6/48)
- by_asset_class: equity 6/24, crypto **0/24** (decisive crypto fail,
  consistent with the parent strategy)
- by_vol_regime: low 0/16, **mid 6/16**, high 0/16 (mid-vol-only artifact)
- best_cell: gap_min=0.01, gap_max=0.03, SPY, mid-vol, Sharpe=1.55
- worst_cell: gap_min=0.015, gap_max=0.03, QQQ, high-vol, Sharpe=-1.77

## Single-config validators (best config: SPY, gap_min=0.01, gap_max=0.03,
full sample 2019-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.062 | 1.0 |
| Max drawdown | PASS | 0.127 | 0.25 |
| Transaction cost survival | **FAIL** | -0.213 net Sharpe | 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 (3/4 positive) | 0.75 |
| Parameter sensitivity (grid proxy) | **FAIL** | 0.125 | 0.5 |

## Decision: REJECTED

Adding an upper gap-size bound did not rescue the parent strategy's
near-zero edge. Full-sample Sharpe is still ~0 and net-of-cost Sharpe is
decisively negative (-0.21, 105 trades @ 10bps) — essentially the same
failure mode as `2026-09-03-010` (-0.20 net Sharpe). Crypto fails entirely
(0/24 cells); passes are concentrated in a single mid-vol tercile only.

**Conclusion:** the gap-down-fade family (plain-threshold and band-gated
variants alike) does not survive transaction costs at daily-OHLCV
granularity, regardless of threshold tuning. This is consistent with the
source's own framing that gap-fade edges require intraday microstructure
(pre-market volume, opening-range confirmation) not available from this
repo's daily loaders. Recommend treating this family as **saturated/closed**
— do not revisit without intraday data.

Strategy file kept in `strategies/` for reference but represents a
**rejected attempt**, not a live strategy.
