# Conditional Turnaround Tuesday — SPY

**Hypothesis source:** https://www.tradequantixnewsletter.com/p/market-effect-research-turnaround
(TradeQuantiX, "Market Effect Research: Turnaround Tuesday Effect", read via
browser_exec after web_extract's DDG-only backend failed to fetch content).

## Hypothesis

Unconditional Monday-close-to-Tuesday-close is a weak, era-unstable effect
(source's own 33-year SPY data: Tuesday +0.071% avg vs. Monday +0.055%,
Wednesday +0.062% — a thin, rotating edge). But the source's conditional
breakdown shows a much stronger, era-stable signal: Tuesday returns are
markedly higher specifically after a DOWN Monday (behaviorally: weekend
news overreaction unwinds Tuesday), and even higher when the prior Friday
was also down (source's bucket averages: Friday-up/Monday-up -0.03%,
Friday-down/Monday-up -0.03%, Friday-up/Monday-down +0.10%,
Friday-down/Monday-down +0.33%). This strategy tests the conditional rule:
long from Monday's close to Tuesday's close, entered only when Monday
itself closed down (optionally requiring the prior Friday down too).

## Step 6 — Grid summary (72 cells: 2 require_friday_down x 3 max_hold_days
x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 0.167 (12/72)
- `by_asset_class`: equity 12/36 (33.3%), crypto 0/36 (0%) — day-of-week
  effects are a US-equity-market-structure phenomenon (weekend closure +
  Monday-morning information digestion); crypto trades 24/7 with no
  analogous "weekend gap", consistent with the decisive 0% crypto pass
  rate.
- `by_vol_regime`: low 0/24, mid 3/24, high 9/24 — the effect concentrates
  in higher-volatility regimes (more weekend news volume -> larger Monday
  overreaction -> larger Tuesday snapback), consistent with the source's
  own mechanism.
- Best cell: SPY, `require_friday_down=False, max_hold_days=1`, high-vol
  tercile, Sharpe 1.64.

## Step 7 — Full-sample validators (SPY, require_friday_down=False,
max_hold_days=1, 2019-01-01..2026-09-01)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.015 | >= 1.0 | pass |
| Max drawdown | 0.042 | <= 0.25 | pass |
| Transaction cost survival (10bps/trade, 141 trades) | 0.504 | >= 0.5 | pass |
| Walk-forward (manual 4-split fallback — `check_walk_forward` broken on installed vectorbt 1.1.0) | 1.0 (4/4 splits positive) | >= 0.75 | pass |
| Parameter sensitivity (max_hold_days in {1,2,3} + require_friday_down in {T,F}) | relative_std 0.065 | <= 0.5 | pass |

QQQ (same params, out-of-scope sanity check, full sample): Sharpe 0.706 —
near-miss, does not clear the threshold. Requiring `require_friday_down=True`
was tested in the grid but scored lower than the plain Monday-down gate on
this full sample (see sensitivity grid); the plain Monday-down gate
(without also requiring Friday down) was the accepted config.

## Verdict: ACCEPTED (SPY only)

All 5 validators pass on SPY with a very thin margin on Sharpe (1.015) and
cost-survival (0.504) — right at the acceptance boundary, so this is a
narrow accept, not a robust one. Max drawdown is tiny (4.2%) and walk-forward
is perfect (4/4), which is reassuring, but the thin Sharpe/cost margins mean
this strategy should be flagged as fragile: small changes to fee
assumptions or the exact sample window could flip it to reject. Scope is
explicitly equity-only (SPY confirmed; QQQ near-miss at 0.706; crypto
decisively rejected 0/36 grid cells) — do not extend to crypto or assume
QQQ works without further tuning.
