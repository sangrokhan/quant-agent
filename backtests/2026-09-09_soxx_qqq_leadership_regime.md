# 2026-09-09 — SOXX/QQQ Leadership Regime Filter (rejected, near-miss)

**Hypothesis** (id `2026-09-09-118`): Per MarketPhase's "SOXX/QQQ Ratio: Why
Semiconductors Lead the Whole Market"
(https://market-phase.com/guides/soxx-qqq-ratio): "chips lead the risk cycle
— a rising ratio signals risk-on appetite and a falling ratio warns that
market risk is draining." Source's own rule: "we look at the ratio's 4-week
rate of change relative to a longer-term baseline." Long QQQ/SPY when the
SOXX/QQQ ratio's `roc_window`-day rate of change is positive (semiconductors
outperforming Nasdaq-100, early-cyclical risk-on signal); flat otherwise.
Genuinely new indicator/technique combination in this repo: a WITHIN-TECH
sector-leadership ratio, distinct from the many cross-asset-class macro
proxies already tested (DXY, HYG/LQD, yield curve, gold/silver, copper/gold,
lumber/gold, IWM/SPY, XLU/SPY, Growth/Value).

Strategy file: `strategies/2026-09-09_soxx_qqq_leadership_regime.py`

## Step 6 grid summary (roc_window ∈ {10,20,40} × roc_threshold ∈ {0.0,0.02} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 72 cells)

- `pass_fraction`: 0.264 (19/72)
- `by_asset_class`: equity 19/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 2/24, high 5/24 — passes across all three
  regimes, not concentrated in a single tercile
- `best_cell`: roc_window=40, roc_threshold=0.0, SPY, low-vol regime,
  Sharpe 2.07
- `worst_cell`: roc_window=20, roc_threshold=0.0, SPY, mid-vol regime,
  Sharpe -0.42

## Single-config validators (best grid config: roc_window=40, roc_threshold=0.0), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.872 ❌ (near-miss) | 0.903 ❌ (near-miss) | ≥ 1.0 |
| Max drawdown | 0.349 ❌ | 0.271 ❌ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.671 ✅ | 0.620 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ | 0.75 ✅ | ≥ 0.75 pass fraction |
| Parameter sensitivity (roc_window 30/40/50 sweep) | 0.135 ✅ | | ≤ 0.5 relative std |
| Trades | 153 | 153 | — |

## Verdict: **reject** (both QQQ and SPY), near-miss on Sharpe, decisive on MDD

Sharpe is a moderate near-miss for both symbols (0.87-0.90 vs 1.0
threshold), but max drawdown fails more decisively (0.27-0.35 vs 0.25 cap) —
worse than the source's qualitative framing as an "early warning" signal
would suggest; the SOXX-outperformance gate apparently doesn't fully avoid
the deepest drawdowns (e.g. it may have stayed "risk-on" through parts of
2022's broad tech selloff since defensive rotation within tech doesn't
necessarily show up as SOXX underperforming QQQ during a systemic
drawdown). TC-survival, walk-forward, and parameter sensitivity all pass
comfortably, so the signal itself has some real structure — but the MDD
failure is the binding constraint here, not overfitting or turnover. A
future iteration could test adding an explicit drawdown-control overlay
(e.g. combining with a broader market trend filter like SPY>SMA200) on top
of this SOXX/QQQ leadership gate specifically to address the MDD failure
while preserving the clean TC-survival/param-sensitivity profile.
