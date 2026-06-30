"""
ERP Order-to-Cash : analysis pipeline.

Steps:
  1. Load data/erp_orders.csv into an in-memory SQLite database (table `orders`).
  2. Run error-diagnosis + process-analysis queries (see sql/analysis.sql).
  3. Export results to:
        - dashboard/data.json   (feeds the interactive D3.js dashboard)
        - reports/erp_analysis_report.xlsx  (multi-sheet Excel report)

Run:  python analyze.py   (after running data/generate_data.py)
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "data" / "erp_orders.csv"


def load_db():
    df = pd.read_csv(CSV, parse_dates=["order_date", "approval_date", "ship_date", "invoice_date"])
    con = sqlite3.connect(":memory:")
    df.to_sql("orders", con, index=False)
    return con, df


def q(con, sql):
    return pd.read_sql_query(sql, con)


def main():
    con, df = load_db()

    # ---------- ERROR DIAGNOSIS ----------
    duplicates = q(con, """
        SELECT order_id, COUNT(*) AS times_seen
        FROM orders GROUP BY order_id HAVING COUNT(*) > 1
        ORDER BY times_seen DESC;""")

    quality = q(con, """
        SELECT
          COUNT(*) AS total_rows,
          SUM(CASE WHEN region IS NULL OR region='' THEN 1 ELSE 0 END) AS missing_region,
          SUM(CASE WHEN amount <= 0 THEN 1 ELSE 0 END) AS bad_amount,
          SUM(CASE WHEN julianday(ship_date) < julianday(order_date) THEN 1 ELSE 0 END) AS bad_dates
        FROM orders;""")

    # ---------- PROCESS ANALYSIS ----------
    step_durations = q(con, """
        SELECT
          ROUND(AVG(julianday(approval_date)-julianday(order_date)),2) AS order_to_approval,
          ROUND(AVG(julianday(ship_date)-julianday(approval_date)),2)  AS approval_to_ship,
          ROUND(AVG(julianday(invoice_date)-julianday(ship_date)),2)   AS ship_to_invoice
        FROM orders WHERE julianday(ship_date) >= julianday(order_date);""")

    cycle_by_region = q(con, """
        SELECT region, COUNT(*) AS orders,
               ROUND(AVG(julianday(invoice_date)-julianday(order_date)),2) AS avg_cycle_days
        FROM orders
        WHERE region IS NOT NULL AND julianday(ship_date) >= julianday(order_date)
        GROUP BY region ORDER BY avg_cycle_days DESC;""")

    revenue_by_category = q(con, """
        SELECT LOWER(category) AS category, COUNT(*) AS orders,
               ROUND(SUM(amount),2) AS total_revenue
        FROM orders WHERE amount > 0
        GROUP BY LOWER(category) ORDER BY total_revenue DESC;""")

    # ---------- console summary ----------
    total = int(quality.loc[0, "total_rows"])
    issues = int(quality.loc[0, "missing_region"] + quality.loc[0, "bad_amount"] + quality.loc[0, "bad_dates"])
    print(f"Loaded {total} rows.")
    print(f"Data-quality issues found: {issues} "
          f"(missing region={int(quality.loc[0,'missing_region'])}, "
          f"bad amount={int(quality.loc[0,'bad_amount'])}, "
          f"bad dates={int(quality.loc[0,'bad_dates'])})")
    print(f"Duplicate order_ids: {len(duplicates)}")
    sd = step_durations.iloc[0]
    slowest = sd.idxmax()
    print(f"Slowest process step: {slowest} ({sd[slowest]} days avg) -> optimization target")

    # ---------- export JSON for the D3 dashboard ----------
    dash = {
        "kpis": {
            "total_orders": total,
            "data_quality_issues": issues,
            "duplicate_orders": int(len(duplicates)),
            "avg_cycle_days": float(q(con, """
                SELECT ROUND(AVG(julianday(invoice_date)-julianday(order_date)),2) AS d
                FROM orders WHERE julianday(ship_date) >= julianday(order_date);""").loc[0, "d"]),
        },
        "step_durations": [
            {"step": "Order → Approval", "days": float(sd["order_to_approval"])},
            {"step": "Approval → Ship",  "days": float(sd["approval_to_ship"])},
            {"step": "Ship → Invoice",   "days": float(sd["ship_to_invoice"])},
        ],
        "cycle_by_region": cycle_by_region.to_dict(orient="records"),
        "revenue_by_category": revenue_by_category.to_dict(orient="records"),
        "quality_breakdown": [
            {"issue": "Missing region", "count": int(quality.loc[0, "missing_region"])},
            {"issue": "Bad amount",     "count": int(quality.loc[0, "bad_amount"])},
            {"issue": "Bad dates",      "count": int(quality.loc[0, "bad_dates"])},
            {"issue": "Duplicate rows", "count": int(len(duplicates))},
        ],
    }
    (HERE / "dashboard" / "data.json").write_text(json.dumps(dash, indent=2))
    print("Wrote dashboard/data.json")

    # ---------- export Excel report ----------
    xlsx = HERE / "reports" / "erp_analysis_report.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xl:
        quality.to_excel(xl, sheet_name="DataQuality", index=False)
        duplicates.to_excel(xl, sheet_name="Duplicates", index=False)
        step_durations.to_excel(xl, sheet_name="ProcessSteps", index=False)
        cycle_by_region.to_excel(xl, sheet_name="CycleByRegion", index=False)
        revenue_by_category.to_excel(xl, sheet_name="RevenueByCategory", index=False)
    print(f"Wrote {xlsx}")

    con.close()


if __name__ == "__main__":
    main()
