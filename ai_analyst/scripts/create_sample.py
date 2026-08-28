"""
create_sample.py — Sample techworld_data.csv for testing.
100 rows per month, stratified. Preserves all distributions.
"""
import os
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT  = os.path.join(BASE, "data/raw/techworld_data.csv")
OUTPUT = os.path.join(BASE, "data/raw/techworld_data_sample.csv")
ROWS_PER_MONTH = 100
SEED = 42

df = pd.read_csv(INPUT)
df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=False)
df["_month"] = df["Order_Date"].dt.to_period("M")

sampled = (
    df.groupby("_month", group_keys=False)
      .apply(lambda g: g.sample(n=min(ROWS_PER_MONTH, len(g)), random_state=SEED),
             include_groups=False)
)

# Restore date to original M/D/YYYY format (no leading zeros)
sampled["Order_Date"] = sampled["Order_Date"].dt.strftime("%-m/%-d/%Y")
sampled.to_csv(OUTPUT, index=False)

orig_kb = os.path.getsize(INPUT) / 1024
samp_kb = os.path.getsize(OUTPUT) / 1024
print(f"Written : {OUTPUT}")
print(f"Rows    : {len(sampled):,}  (original {len(df):,})")
print(f"Months  : {sampled['Order_Date'].apply(lambda x: x[:x.rfind('/')]).nunique()}")
print(f"Size    : {samp_kb:.0f} KB  (original {orig_kb:.0f} KB, reduction {(1-samp_kb/orig_kb)*100:.0f}%)")
