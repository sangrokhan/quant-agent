# Qullamaggie Episodic Pivot (EP) gap breakout with EMA trail exit

**Hypothesis source:** Kristjan Qullamaggie's Episodic Pivot (EP) setup, per
Google AI-overview synthesis of qullamaggie.com and SnapPChart SERP
snippets (both target pages 404'd on direct load; content captured from
the SERP itself): a gap of ~10%+ on a genuine catalyst (earnings surprise,
guidance, major news) on a stock that had NOT already rallied
significantly, followed by holding with a 10/21-day EMA trail exit (source
also disclosed a partial 1/3-1/2 scale-out at day 3-5, not representable
in this repo's {0,1} position contract -- documented simplification).

## Grid test (Step 6)

`param_grid={"gap_pct_threshold": [0.03,0.05], "vol_mult": [1.2,1.5]}`
(loosened from the source's literal ~10%+ gap threshold since QQQ/SPY/BTC/
ETH essentially never gap 10%+ on a single daily bar — a lower threshold
was needed just to generate any signal at all), `symbols={"equity":
["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`.

- **Overall pass_fraction: 3/48 = 0.0625**
- By asset class: equity 3/24, crypto 0/24 (zero trades at ANY crypto grid cell)
- Signal is extremely sparse: best config (gap_pct_threshold=0.03,
  vol_mult=1.2) generated only 6-7 trades total over the full 7.7-year
  sample on QQQ/SPY

## Full-sample validator suite (Step 7), config gap_pct_threshold=0.03/vol_mult=1.2

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.124 ❌ | -0.154 ❌ |
| Max drawdown (<=0.25) | 0.096 ✅ | 0.104 ✅ |
| Tx-cost survival (net Sharpe >=0.5) | 0.106 ❌ | -0.174 ❌ |
| Walk-forward (manual 4-slice) | 0.25 ❌ (1/4) | 0.25 ❌ (1/4) |

SPY: 6 trades. QQQ: 7 trades — both statistically too sparse to draw a
reliable conclusion, and both fail decisively on the metrics available.

## Decision

**Reject.** Decisive failure on Sharpe, transaction-cost survival, and
walk-forward for both QQQ and SPY; zero signal at all in crypto across
every grid cell. The core issue is a data-granularity mismatch: EP is
fundamentally a single-name catalyst-driven setup meant for individual
stocks around earnings/news events, while this repo trades broad index
ETFs (QQQ/SPY) and major crypto pairs that essentially never gap 10%+ on
a single daily bar from a single catalyst — the diversification inherent
in an index/major-pair makes genuine "episodic" gaps vanishingly rare.
Would need single-stock data with earnings-date alignment to properly test
this hypothesis; not pursued further with this repo's current data scope.
