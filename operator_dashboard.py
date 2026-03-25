import pandas as pd
from pathlib import Path

csv = Path("analytics/execution_diagnostics_v3.csv")

df = pd.read_csv(csv)

closed = df[df.realized_pnl.notna()].copy()

print("\n==============================")
print(" SIGNALATLAS EXECUTION REPORT ")
print("==============================\n")

print("Total trades:", len(df))
print("Closed trades:", len(closed))
print("Total PnL:", round(closed.realized_pnl.sum(),2))
print("Win rate:", round((closed.realized_pnl > 0).mean()*100,2), "%")

print("\n---- Edge Buckets ----")
bins = pd.cut(closed.total_edge,[0,0.10,0.15,0.20,0.30,1])
print(closed.groupby(bins).realized_pnl.agg(["count","mean","sum"]))

print("\n---- Microstructure ----")
bins = pd.cut(closed.microstructure_score,[0,0.05,0.10,0.20,1])
print(closed.groupby(bins).realized_pnl.agg(["count","mean","sum"]))

print("\n---- Vacuum ----")
bins = pd.cut(closed.vacuum_score,[0,0.05,0.10,0.20,1])
print(closed.groupby(bins).realized_pnl.agg(["count","mean","sum"]))

print("\n---- Strategy ----")
print(closed.groupby("strategy").realized_pnl.agg(["count","mean","sum"]))

print("\n---- Market Buckets ----")
print(closed.groupby("bucket").realized_pnl.agg(["count","mean","sum"]))

print("\n---- Holding Time ----")
print(closed.holding_minutes.describe())

print("\n==============================\n")
