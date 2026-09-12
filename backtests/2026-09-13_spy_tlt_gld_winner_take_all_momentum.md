# 2026-09-13 SPY/TLT/GLD Winner-Take-All 6-Month Momentum Rotation — Backtest Report

**Hypothesis:** Per https://edgelabtrading.com/blog/etf-momentum-rotation
(read via browser_exec this iteration): on the last trading day of each
month, rank SPY (stocks), TLT (bonds), GLD (gold) by trailing 6-month
total return; hold the single winner 100% for the following month.
Source's own 21-year backtest (2005-2026): out-of-sample (2016-2026) CAGR
10.9%/Sharpe 0.70/MDD -33.6%; full-period CAGR 9.4%/Sharpe 0.61/MDD
-25.8% — and the source's own honest conclusion is that this
concentration does NOT clearly beat an equal-weight-all-three benchmark
(Sharpe 0.96).

Structurally distinct from already-tested/accepted Faber 3-asset
EQUAL-WEIGHT-ALL-QUALIFYING rotation (2026-09-11-078) and
already-rejected 5-asset GTAA dual-momentum (2026-09-11-037/-041): this
uses only 3 assets, concentrates 100% in the single top-ranked pick with
NO absolute-momentum/cash-fallback filter (always fully invested in
whichever of the three ranks highest, even during broad drawdowns), and
uses a fixed 6-month lookback per the source's own comparison finding
(12-month "worse on every metric").

## Single-config validators (full sample 2005-01-01 to 2026-09-01)

| Symbol | lookback_months | Sharpe | MDD | Trades | Net Sharpe (10bps/trade) |
|---|---|---|---|---|---|
| SPY | 6 | 0.596 (FAIL) | 0.225 (PASS) | 59 | 0.556 (FAIL) |
| SPY | 9 | 0.508 (FAIL) | 0.236 (PASS) | 43 | 0.480 (FAIL) |
| QQQ | 6 | 0.517 (FAIL) | 0.414 (FAIL) | 45 | 0.499 (FAIL) |
| QQQ | 9 | 0.633 (FAIL) | 0.266 (FAIL) | 39 | 0.615 (FAIL) |

Sharpe fails decisively at every tested config on both symbols. SPY passes
MDD but still fails Sharpe/TC-survival; QQQ fails MDD too. Walk-forward
and parameter-sensitivity skipped (already decisively rejected; also
`validators.check_walk_forward` errors in this environment as previously
noted in 2026-09-13-007/010's reports).

## Step 6 grid summary (lookback_months in [3,6,9,12], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3, window 2010-01-01 to 2026-09-01)

- 48 total cells, 8 passed (pass_fraction 0.167)
- **by_asset_class**: equity 8/24 (33%), crypto 0/24 (0%)
- **by_vol_regime**: low 8/16 (50%), mid 0/16, high 0/16
- Best cell: lookback_months=9, QQQ, low-vol regime, Sharpe 2.007
- Worst cell: lookback_months=3, SPY, high-vol regime, Sharpe -0.157

## Decision: REJECTED

Directly corroborates the source's own honest disclosed finding: this
winner-take-all concentration strategy has a real but modest edge
confined to calm/low-vol regimes, and full-sample risk-adjusted
performance (Sharpe 0.5-0.63 across all tested configs/symbols) falls
well short of this repo's 1.0 threshold — consistent with the source's own
stated conclusion that simple equal-weight-buy-and-hold of all three
assets (Sharpe 0.96 in their test) outperforms this active rotation on a
risk-adjusted basis. Crypto is decisively rejected across the entire grid
(0/24) — a monthly SPY/TLT/GLD-basket rotation signal has no meaningful
transferability to BTC/ETH.

## Notes for future iterations

- This strategy, the already-accepted Faber equal-weight variant
  (2026-09-11-078), and the rejected 5-asset GTAA (2026-09-11-037/-041)
  together give a fairly complete picture of this repo's exploration of
  the SPY/TLT/GLD-family cross-sectional momentum rotation space:
  absolute-trend-filter equal-weighting (accepted, QQQ) clearly
  outperforms both winner-take-all concentration (this entry, rejected)
  and larger 5-asset cross-sectional ranking (rejected) — the source's own
  finding that "diversification, not concentration, is what actually
  helped" when comparing improvements is directly corroborated by this
  repo's own three independent tests of the same underlying asset family.
- Source's own three "improvement" variants (top-2 instead of top-1,
  inverse-vol weighting) were also disclosed as improving Sharpe by
  reducing concentration toward the diversified benchmark — not by adding
  a genuinely new signal — so a follow-up top-2 or inverse-vol-weighted
  variant is unlikely to newly clear this repo's threshold beyond what
  the already-accepted equal-weight Faber variant already achieves.
