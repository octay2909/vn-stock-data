"""
Generate synthetic 2025 data for TechWorld e-commerce dataset.
Appends rows to data/cleaned/revenue/techworld_data_sample_cleaned.xlsx
"""

import pandas as pd
import numpy as np
from datetime import date
from calendar import monthrange

np.random.seed(42)

# ── Load existing data ────────────────────────────────────────────────────────
df = pd.read_excel('data/cleaned/revenue/techworld_data_sample_cleaned.xlsx')
print(f"Loaded {len(df)} existing rows")

# Mark existing rows as non-synthetic
df['is_synthetic'] = 0

# ── Parameters ────────────────────────────────────────────────────────────────
YEAR = 2025
MONTHS = range(1, 13)

# Seasonal indices (relative to base ~$55K/month)
SEASONAL = {
    1: 1.137, 2: 0.979, 3: 0.928, 4: 0.878, 5: 0.896, 6: 0.970,
    7: 0.918, 8: 1.003, 9: 1.024, 10: 1.181, 11: 0.973, 12: 1.114
}

# ── Product weights (2022-2024 base, adjusted for 2025 trajectory) ────────────
base_weights = {
    'Laptop Air':          0.096,
    'Laptop Pro X':        0.090,
    'Smartphone Alpha':    0.090 * 0.20,  # 80% decline
    'Fast Charger':        0.089,
    'Wireless Headphones': 0.085,
    'Mechanical Keyboard': 0.081,
    '4K Monitor':          0.081,
    'SmartWatch V2':       0.080,
    'Smartphone Z':        0.079 * 1.20,  # 20% growth
    'Tablet Pro':          0.076,
    'Gaming Mouse':        0.075,
    'Bluetooth Speaker':   0.075,
}
total_w = sum(base_weights.values())
PROD_WEIGHTS = {k: v / total_w for k, v in base_weights.items()}

# Product metadata: category, unit_price, gross_contribution_rate, shipping params
PROD_META = {
    'Laptop Air':          {'category': 'Electronics', 'unit_price': 1000, 'gc_rate': 0.300, 'ship_mean': 8.74,  'ship_std': 2.0},
    'Laptop Pro X':        {'category': 'Electronics', 'unit_price': 1500, 'gc_rate': 0.333, 'ship_mean': 11.33, 'ship_std': 3.9},
    'Smartphone Alpha':    {'category': 'Electronics', 'unit_price': 700,  'gc_rate': 0.357, 'ship_mean': 5.73,  'ship_std': 0.4},
    'Fast Charger':        {'category': 'Accessories', 'unit_price': 30,   'gc_rate': 0.667, 'ship_mean': 5.26,  'ship_std': 0.2},
    'Wireless Headphones': {'category': 'Audio',       'unit_price': 200,  'gc_rate': 0.400, 'ship_mean': 6.29,  'ship_std': 0.9},
    'Mechanical Keyboard': {'category': 'Accessories', 'unit_price': 120,  'gc_rate': 0.416, 'ship_mean': 7.57,  'ship_std': 1.7},
    '4K Monitor':          {'category': 'Electronics', 'unit_price': 400,  'gc_rate': 0.375, 'ship_mean': 16.90, 'ship_std': 6.0},
    'SmartWatch V2':       {'category': 'Wearables',   'unit_price': 300,  'gc_rate': 0.400, 'ship_mean': 5.25,  'ship_std': 0.1},
    'Smartphone Z':        {'category': 'Electronics', 'unit_price': 900,  'gc_rate': 0.333, 'ship_mean': 5.72,  'ship_std': 0.3},
    'Tablet Pro':          {'category': 'Electronics', 'unit_price': 800,  'gc_rate': 0.312, 'ship_mean': 6.23,  'ship_std': 0.6},
    'Gaming Mouse':        {'category': 'Accessories', 'unit_price': 50,   'gc_rate': 0.598, 'ship_mean': 5.51,  'ship_std': 0.4},
    'Bluetooth Speaker':   {'category': 'Audio',       'unit_price': 80,   'gc_rate': 0.500, 'ship_mean': 6.96,  'ship_std': 1.1},
}

REGIONS       = ['North', 'East', 'South', 'West']
_rp = [0.259, 0.253, 0.250, 0.239]
REGION_PROBS  = [p / sum(_rp) for p in _rp]

SUPPLIERS      = ['Supplier_A', 'Supplier_B', 'Supplier_C', 'Supplier_D', 'Supplier_X']
_sp = [0.202, 0.199, 0.191, 0.214, 0.194]
SUPPLIER_PROBS = [p / sum(_sp) for p in _sp]

TRAFFIC_SOURCES = ['Email', 'Organic', 'Referral', 'Direct', 'Facebook Ads', 'Google Ads']
TRAFFIC_PROBS   = [0.170, 0.162, 0.162, 0.158, 0.155, 0.145]
TRAFFIC_PROBS   = [p / sum(TRAFFIC_PROBS) for p in TRAFFIC_PROBS]

QTY_VALS  = [1, 2, 5]
QTY_PROBS = [0.837, 0.134, 0.028]
QTY_PROBS = [p / sum(QTY_PROBS) for p in QTY_PROBS]

REVIEW_POS       = ['Good value for money.', 'Five stars!', 'Exceeded expectations.',
                    'Love it, works perfectly.', 'Great product, fast shipping!']
_rpp = [0.193, 0.189, 0.183, 0.175, 0.172]
REVIEW_POS_PROBS = [p / sum(_rpp) for p in _rpp]
REVIEW_NEG       = ["Just didn't like it.", "Shipping took forever. Arrived too late.",
                    "Waste of money. Arrived too late.", "Battery life is terrible. Arrived too late.",
                    "Customer service was rude. Arrived too late."]
_rnp = [0.40, 0.177, 0.172, 0.143, 0.108]
REVIEW_NEG_PROBS = [p / sum(_rnp) for p in _rnp]

MC_VALS  = [0.0, 2.0, 10.0, 15.0, 20.0]
_mcp = [0.43, 0.12, 0.20, 0.15, 0.10]
MC_PROBS = [p / sum(_mcp) for p in _mcp]

RETURN_RATE = 0.032

prod_list  = list(PROD_WEIGHTS.keys())
prod_probs = [PROD_WEIGHTS[p] for p in prod_list]

# ── Avoid Order_ID collisions ─────────────────────────────────────────────────
used_ids = set(df['Order_ID'].values)

# ── Generate rows ─────────────────────────────────────────────────────────────
rows = []

for month in MONTHS:
    n_orders = np.random.randint(90, 101)  # 90-100 per month
    _, n_days = monthrange(YEAR, month)
    day_choices = sorted(np.random.choice(range(1, n_days + 1), size=n_orders, replace=True))

    for day in day_choices:
        order_date = date(YEAR, month, int(day))
        product    = np.random.choice(prod_list, p=prod_probs)
        meta       = PROD_META[product]

        qty        = int(np.random.choice(QTY_VALS, p=QTY_PROBS))
        unit_price = meta['unit_price']
        sales_full = unit_price * qty

        # Return / order status
        is_returned  = int(np.random.random() < RETURN_RATE)
        order_status = 'Returned' if is_returned else 'Completed'
        return_flag  = is_returned

        # Costs
        mc     = float(np.random.choice(MC_VALS, p=MC_PROBS))
        sc_raw = np.random.normal(meta['ship_mean'], meta['ship_std'])
        sc     = round(max(meta['ship_mean'] * 0.5, sc_raw), 1)

        # Net profit
        if is_returned:
            actual_sales    = 0
            np_val          = round(-(sales_full * meta['gc_rate']) - mc - sc, 1)
            net_profit_flag = 1
        else:
            actual_sales    = sales_full
            np_val          = round(sales_full * meta['gc_rate'] - mc, 1)
            net_profit_flag = 0

        region         = np.random.choice(REGIONS, p=REGION_PROBS)
        supplier       = np.random.choice(SUPPLIERS, p=SUPPLIER_PROBS)
        traffic_source = np.random.choice(TRAFFIC_SOURCES, p=TRAFFIC_PROBS)
        delivery_days  = int(np.clip(np.random.normal(3.9, 2.1), 1, 14))

        rating_vals  = [5, 4, 3, 2, 1]
        _ratingp = [0.551, 0.280, 0.097, 0.032, 0.040]
        rating_probs = [p / sum(_ratingp) for p in _ratingp]
        review_rating = int(np.random.choice(rating_vals, p=rating_probs))
        review_text   = (np.random.choice(REVIEW_POS, p=REVIEW_POS_PROBS)
                         if review_rating >= 3
                         else np.random.choice(REVIEW_NEG, p=REVIEW_NEG_PROBS))

        cust_num    = np.random.randint(1, 10000)
        customer_id = f'CUST_{cust_num:04d}'

        # Unique Order_ID in 90000-99999
        while True:
            oid = np.random.randint(90000, 100000)
            if oid not in used_ids:
                used_ids.add(oid)
                break

        rows.append({
            'Order_ID':        oid,
            'Order_Date':      pd.Timestamp(order_date),
            'Customer_ID':     customer_id,
            'Region':          region,
            'Category':        meta['category'],
            'Product_Name':    product,
            'Quantity':        qty,
            'Unit_Price':      unit_price,
            'Sales':           actual_sales,
            'Net_Profit':      np_val,
            'Marketing_Cost':  mc,
            'Shipping_Cost':   sc,
            'Delivery_Days':   delivery_days,
            'Traffic_Source':  traffic_source,
            'Supplier':        supplier,
            'Order_Status':    order_status,
            'Return_Flag':     return_flag,
            'Review_Rating':   review_rating,
            'Review_Text':     review_text,
            'Net_Profit_Flag': net_profit_flag,
            'YearMonth':       f'{YEAR}-{month:02d}',
            'is_synthetic':    1,
        })

syn = pd.DataFrame(rows)
print(f'\nGenerated {len(syn)} synthetic rows for 2025')

# ── Monthly summary ────────────────────────────────────────────────────────────
monthly = syn.groupby('YearMonth').agg(
    orders=('Order_ID', 'count'),
    sales=('Sales', 'sum'),
).reset_index()
print('\n2025 Monthly distribution:')
print(monthly.to_string(index=False))

# ── Combine and save ───────────────────────────────────────────────────────────
combined = pd.concat([df, syn], ignore_index=True)
combined.sort_values(['Order_Date', 'Order_ID'], inplace=True)
combined.reset_index(drop=True, inplace=True)

out_path = 'data/cleaned/revenue/techworld_data_sample_cleaned.xlsx'
combined.to_excel(out_path, index=False)
print(f'\nSaved {len(combined)} total rows to {out_path}')

# ── Verify full coverage ───────────────────────────────────────────────────────
coverage = combined.groupby('YearMonth').agg(
    orders=('Order_ID', 'count'),
    sales=('Sales', 'sum'),
).reset_index()
print('\nFull coverage verification:')
print(coverage.to_string(index=False))

# ── Spot-check return rate and profit margin ───────────────────────────────────
syn_completed = syn[syn['Return_Flag'] == 0]
print(f'\nReturn rate (synthetic): {syn["Return_Flag"].mean():.3f}')
if len(syn_completed) > 0:
    syn_completed = syn_completed.copy()
    syn_completed['margin'] = syn_completed['Net_Profit'] / syn_completed['Sales']
    print(f'Avg Net Profit Margin (completed orders): {syn_completed["margin"].mean():.3f}')
print(f'Product mix (synthetic):\n{syn["Product_Name"].value_counts().to_string()}')
