import json

entry = {
  "id": "2026-09-18-085",
  "created_at": "2026-09-18T11:20:00Z",
  "hypothesis": "Rescue attempt for near-miss 2026-09-16-165 (Clenow regression-momentum continuous sizing dial, accepted BTC/USDT only, QQQ near-miss Sharpe 0.976/TC-survival 0.269/walk-forward 0.25). This iteration ran two parameter sweeps on the identical unmodified strategy code (strategies/2026-09-16_clenow_regression_momentum_sizing.py) against QQQ: (1) a broad sweep (mom_window in {60,90,130} x rank_threshold in {0.6,0.7,0.8} x regime_window in {150,200} x stop_window in {50,100} x leverage_cap in {1.0,1.3,1.6}, 2015-2026 sample), (2) a fine local sweep around the original near-miss defaults (mom_window in {80,90,100,110} x rank_threshold in {0.75,0.78,0.8,0.82,0.85} x regime_window in {180,200,220} x stop_window in {80,100,120}, leverage_cap=1.0).",
  "asset_class": "equity",
  "symbols": ["QQQ"],
  "timeframe": "1d",
  "strategy_file": "strategies/2026-09-16_clenow_regression_momentum_sizing.py",
  "backtest_report": None,
  "validators": {"sharpe_ratio": {"passed": False, "best_value_broad_sweep": 0.618, "best_value_fine_sweep": 0.713, "threshold": 1.0}},
  "outcome": "rejected (rescue attempt failed)",
  "rejection_reason": "Both sweeps found materially WORSE best-Sharpe results (0.618 broad, 0.713 fine local) than the original near-miss's own recorded 0.976 at mom_window=90 defaults. The 0.976 figure in 2026-09-16-165 appears to have used a different sample start date than this rescue's 2015-2026 window (grid_test.py's own default full-sample period differs from this script's explicit start=2015-01-01) -- confirms the QQQ result is sensitive to sample-start choice, not a robust near-miss worth chasing further. No config found clearing the Sharpe threshold; MDD/TC-survival not evaluated further since Sharpe already decisively fails.",
  "notes": "Diagnostic: this rescue used start=2015-01-01 for a longer QQQ history than the original grid, and got materially lower Sharpe across the board (max 0.713 vs the original's reported 0.976) -- suggests the original near-miss figure was itself sample-window-dependent (post-2018 or post-2019 start), making QQQ fragile for this strategy regardless of parameter tuning. Recommend future loops treat 2026-09-16-165's QQQ near-miss as effectively closed (not worth further rescue attempts) rather than sample-window-dependent-but-fixable. BTC/USDT acceptance (2026-09-16-165) stands unaffected."
}

with open("knowledge_base/strategies_log.jsonl", "a") as f:
    f.write(json.dumps(entry) + "\n")

index_entry = {
  "id": "2026-09-18-085",
  "created_at": "2026-09-18T11:20:00Z",
  "hypothesis": "Rescue attempt for Clenow regression-momentum QQQ near-miss (2026-09-16-165) -- failed, sample-window-sensitive, not a fixable near-miss.",
  "outcome": "rejected",
  "tags": {
    "indicator_family": ["Clenow Regression Momentum", "OLS Slope", "R-squared"],
    "technique": ["continuous_sizing_dial", "rescue_attempt_failed", "sample_window_sensitivity_diagnosis"],
    "asset_class": "equity"
  }
}
with open("knowledge_base/strategies_index.jsonl", "a") as f:
    f.write(json.dumps(index_entry) + "\n")

print("logged")
