"""
Generate a synthetic ERP "order-to-cash" dataset.

This simulates the kind of business data that lives in an ERP system: each row is
a sales order that moves through a process (created -> approved -> shipped -> invoiced).
We deliberately inject realistic DATA-QUALITY problems (duplicates, missing fields,
negative amounts, illogical dates) so the analysis step has real errors to diagnose.

Run:  python data/generate_data.py
Output: data/erp_orders.csv
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)          # fixed seed -> reproducible data
N_ORDERS = 5000

regions    = ["DACH", "Western Europe", "Southern Europe", "Nordics", "UK & Ireland"]
categories = ["Beverages", "Snacks", "Dairy", "Frozen", "Bakery", "Household"]
systems    = ["SAP-ECC", "SAP-ECC", "SAP-ECC", "Legacy-CRM"]  # most from SAP, some legacy


def random_dates(n):
    """Create a chain of process timestamps with realistic durations (in days)."""
    start = pd.Timestamp("2025-01-01")
    order_date    = start + pd.to_timedelta(RNG.integers(0, 300, n), unit="D")
    approve_lag   = RNG.gamma(shape=2.0, scale=1.0, size=n)            # ~2 days avg
    ship_lag      = RNG.gamma(shape=2.5, scale=1.6, size=n)            # ~4 days avg
    invoice_lag   = RNG.gamma(shape=2.0, scale=1.2, size=n)           # ~2.4 days avg
    approval_date = order_date + pd.to_timedelta(approve_lag, unit="D")
    ship_date     = approval_date + pd.to_timedelta(ship_lag, unit="D")
    invoice_date  = ship_date + pd.to_timedelta(invoice_lag, unit="D")
    return order_date, approval_date, ship_date, invoice_date


def main():
    order_date, approval_date, ship_date, invoice_date = random_dates(N_ORDERS)

    df = pd.DataFrame({
        "order_id":      [f"ORD-{100000 + i}" for i in range(N_ORDERS)],
        "customer_id":   [f"CUST-{RNG.integers(1000, 1300)}" for _ in range(N_ORDERS)],
        "category":      RNG.choice(categories, N_ORDERS),
        "region":        RNG.choice(regions, N_ORDERS),
        "source_system": RNG.choice(systems, N_ORDERS),
        "quantity":      RNG.integers(1, 500, N_ORDERS),
        "unit_price":    np.round(RNG.uniform(0.5, 40.0, N_ORDERS), 2),
        "order_date":    order_date.normalize(),
        "approval_date": approval_date.normalize(),
        "ship_date":     ship_date.normalize(),
        "invoice_date":  invoice_date.normalize(),
        "status":        "Invoiced",
    })
    df["amount"] = np.round(df["quantity"] * df["unit_price"], 2)

    # ---- Inject realistic DATA-QUALITY issues (this is what we will diagnose) ----

    # 1) Missing region on ~3% of rows
    miss_idx = RNG.choice(N_ORDERS, size=int(0.03 * N_ORDERS), replace=False)
    df.loc[miss_idx, "region"] = np.nan

    # 2) Missing/zero unit_price on ~2% -> amount becomes wrong (0)
    zero_idx = RNG.choice(N_ORDERS, size=int(0.02 * N_ORDERS), replace=False)
    df.loc[zero_idx, "unit_price"] = 0.0
    df.loc[zero_idx, "amount"] = 0.0

    # 3) Negative amounts on ~1% (data entry / sign errors)
    neg_idx = RNG.choice(N_ORDERS, size=int(0.01 * N_ORDERS), replace=False)
    df.loc[neg_idx, "amount"] = -df.loc[neg_idx, "amount"]

    # 4) Illogical dates on ~1.5% (ship before approval) -> negative cycle time
    bad_date_idx = RNG.choice(N_ORDERS, size=int(0.015 * N_ORDERS), replace=False)
    df.loc[bad_date_idx, "ship_date"] = df.loc[bad_date_idx, "order_date"] - pd.to_timedelta(1, unit="D")

    # 5) Inconsistent category spelling (same thing, different text) -> fake duplicates in reports
    typo_idx = RNG.choice(N_ORDERS, size=int(0.02 * N_ORDERS), replace=False)
    df.loc[typo_idx, "category"] = df.loc[typo_idx, "category"].str.lower()

    # 6) Exact duplicate rows (same order imported twice from two systems)
    dup_rows = df.sample(n=60, random_state=1).copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    df = df.sample(frac=1, random_state=7).reset_index(drop=True)  # shuffle
    out = "data/erp_orders.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows -> {out}")
    print(f"  injected: missing regions, zero prices, negative amounts, bad dates, "
          f"category typos, {len(dup_rows)} duplicate orders")


if __name__ == "__main__":
    main()
