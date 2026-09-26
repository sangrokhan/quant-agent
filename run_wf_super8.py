import sys, json
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from loaders import load_equity
from validators import check_walk_forward
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("super8", "strategies/2026-09-26_super8_days_seasonality.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

df = load_equity("QQQ", start=datetime(2019,1,1), end=datetime(2026,9,1))
params = dict(first_n_days=2, last_n_days=3, mid_start_day=9, mid_end_day=11)
def strategy_fn(slice_df):
    return strat.generate_returns(slice_df, **params)
try:
    wf = check_walk_forward(df, strategy_fn, n_splits=4)
    print(json.dumps(wf, indent=2, default=str))
except Exception as e:
    print("WF failed:", e)
