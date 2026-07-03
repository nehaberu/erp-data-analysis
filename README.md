# ERP Data Analysis & Process Dashboard

**SQL-based data analysis and error diagnosis on business data, with an interactive
dashboard (D3.js, Python, Excel) to identify process-optimization potential.**

This project simulates an ERP **order-to-cash** process — the journey of a sales order
from *created → approved → shipped → invoiced* — and answers two business questions:

1. **Where is the process slow?** (process / efficiency analysis)
2. **Where is the data wrong, and why?** (error diagnosis / data quality)

---

## What it does

| Stage | Tool | What happens |
|-------|------|--------------|
| 1. Generate data | Python (pandas/numpy) | Creates 5,000+ ERP orders with *deliberately injected* data-quality problems |
| 2. Analyse | SQL (SQLite) | Diagnoses errors and measures process step durations / cycle times |
| 3. Visualise | D3.js | Interactive dashboard of KPIs, bottlenecks and data-quality issues |
| 4. Report | Excel (openpyxl) | Multi-sheet report for non-technical stakeholders |

## The data-quality issues it diagnoses
- **Duplicate orders** (same order imported from two systems)
- **Missing fields** (region not filled in)
- **Impossible values** (zero / negative amounts)
- **Illogical dates** (shipped before ordered → negative cycle time)
- **Inconsistent spelling** (`Dairy` vs `dairy` → one category split into two)

## The process insight it produces
- Average duration of **each step** → which step is the bottleneck
- **Cycle time by region** → where the process is slowest
- **Revenue by category** (cleaned) → business value view
- A **data-quality scorecard** → % of records that are trustworthy

---

## How to run

```bash
pip install -r requirements.txt

python data/generate_data.py     # 1. create data/erp_orders.csv
python analyze.py                # 2. run SQL analysis -> data.json + Excel report

# 3. view the dashboard (a local server is needed so the browser can load data.json)
cd dashboard && python -m http.server 8000
# then open http://localhost:8000  in your browser
```

Outputs:
- `dashboard/data.json` + `dashboard/index.html` → interactive dashboard
- `reports/erp_analysis_report.xlsx` → Excel report

---

