# Williams %R Deep-Oversold + Trend Filter (crypto-targeted fix attempt)

**Hypothesis / source:** Google AI-overview synthesis of
https://www.quantifiedstrategies.com/williams-r-strategy/ (via browser_exec
Google SERP fallback — this iteration's web_search query for the topic
returned no usable snippet). Source's own "Crypto Backtest Considerations"
note: a 2-period Williams %R whipsaws on crypto; adding a 200-period MA
trend filter "dramatically improves win rates" by only taking long signals
in an overarching bull trend. Applied here to this repo's existing
2026-09-04-030 Williams %R oversold strategy (accepted equity, rejected
crypto) by adding `close > SMA(trend_window)` as an entry/exit gate and
loosening the exit threshold to the source's suggested "median" level
(-50 vs. original -30).

**Grid summary (scripts/run_grid_williams_trend.py, 96 cells: 2 oversold
thresholds x 2 trend windows x 2 exit thresholds x 2 asset classes x 2
symbols x 3 vol regimes):**
- pass_fraction: 0.2396 (23/96)
- by_asset_class: equity 23/48 passed; **crypto 0/48 passed** (trend filter
  did NOT fix crypto — still a categorical fail, same as ungated
  2026-09-04-030)
- by_vol_regime: low 16/32, mid 2/32, high 5/32 (mostly low-vol-tercile
  passes, as with most oversold mean-reversion strategies in this repo)
- best_cell: QQQ, oversold=-90, trend_window=100, exit=-30, low-vol, Sharpe
  2.45
- worst_cell: SPY, oversold=-95, trend_window=200, exit=-50, high-vol,
  Sharpe -0.22

**Single-config validators (QQQ, oversold_threshold=-90, trend_window=100,
exit_threshold=-30, 2017-01-01 to 2026-09-01):**

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.888 | >= 1.0 |
| Max drawdown | PASS | 0.147 | <= 0.25 |
| TC survival (10bps/trade, 101 trades) | PASS | net Sharpe 0.653 | >= 0.5 |
| Walk-forward (4 manual splits) | PASS | 0.75 pass fraction | >= 0.75 |
| Parameter sensitivity (8-cell QQQ sweep) | PASS | rel_std 0.167 | <= 0.5 |

Note: `check_walk_forward` in `validation/validators.py` calls
`vbt.utils.splitting.RangeSplitter`, which doesn't exist in the installed
vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute
'splitting'`) — worked around with an equivalent manual 4-split walk-forward
(same semantics: per-split Sharpe > 0, 0.75 pass-fraction threshold). This
appears to be a pre-existing environment/library-version issue affecting any
iteration that calls this validator as-is, not specific to this strategy.

**Verdict: REJECTED.** Sharpe is the sole failure (0.888 vs 1.0 threshold,
a near-miss) — everything else passes cleanly, including the parameter
sensitivity that the base 2026-09-04-030 strategy wasn't separately graded
on. More importantly, the source's specific crypto fix (200-period MA trend
filter) did **not** rescue the crypto asset class at all — 0/48 grid cells
passed for BTC/USDT and ETH/USDT across every parameter combination tested,
identical categorical failure to the ungated original. This is a useful
negative result: trend-filtering this particular oversold-oscillator entry
does not make it viable on crypto, at least not with a simple SMA trend
gate.
