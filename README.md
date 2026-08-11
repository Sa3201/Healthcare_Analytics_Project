# Healthcare Analytics Dashboard

An end-to-end data engineering and analytics project that transforms U.S. nursing-home staffing data into an interactive Streamlit dashboard. The project focuses on staffing intensity, occupancy, contractor use, and CMS quality measures.

## Business question

How do nursing-home staffing levels vary by state and facility, and how do those patterns compare with occupancy and rehospitalization/readmission measures?

## Architecture

![Final project architecture](<docs/Final Project Architecture.png>)

## Technology stack

Google Drive | AWS Glue | Amazon S3 | Snowflake | dbt | Streamlit | Python | Pandas | Plotly

| Technology | Purpose |
|---|---|
| Google Drive | Source-file delivery |
| AWS Glue | Ingestion and Spark transformations |
| Amazon S3 | Bronze, Silver, and Gold data-lake layers |
| Snowflake | Analytics warehouse for curated data |
| dbt | SQL transformation, testing, lineage, and dashboard marts |
| Streamlit | Four-page interactive dashboard |

## Data pipeline

The project uses the CMS Payroll-Based Journal (PBJ) Daily Nurse Staffing file for Q2 2024 and supporting CMS nursing-home provider and quality datasets.

1. **Ingest** — A Glue Python Shell job copies source files from Google Drive into the S3 Bronze layer.
2. **Clean** — Two Glue Spark jobs standardize PBJ staffing records and CMS supporting data in the Silver layer.
3. **Calculate** — A Glue Spark job creates Gold metrics for daily staffing, facility quarterly summaries, and staffing-quality analysis.
4. **Load** — Gold Parquet data is loaded into Snowflake `PP2_HEALTHCARE.RAW`.
5. **Model** — dbt creates tested staging models and analytics marts in `PP2_HEALTHCARE.ANALYTICS`.
6. **Visualize** — Streamlit queries only the analytics marts.

## Analytics models

| dbt mart | Purpose |
|---|---|
| `MART_STATE_STAFFING_SUMMARY` | State-level staffing HPRD, RN HPRD, occupancy proxy, and contractor use |
| `MART_LOW_STAFFING_FACILITIES` | Facilities with the lowest staffing HPRD relative to resident census |
| `MART_STAFFING_QUALITY` | Staffing metrics alongside CMS rehospitalization/readmission measures |

## Dashboard

The Streamlit app contains four pages:

- **Overview** — Staffing and occupancy KPIs with state comparisons
- **State Staffing** — Staffing mix, RN coverage, occupancy, and contractor use by state
- **Facility Watchlist** — Lowest-staffed facilities and resident-census context
- **Staffing & Quality** — Exploratory comparison of staffing and CMS quality measures

Run the dashboard locally:

```bash
streamlit run streamlit_dashboard/app.py
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add Snowflake credentials before running locally. The real secrets file is ignored by Git.

## Repository structure

```text
glue_jobs/              AWS Glue ingestion and transformation scripts
models/                 dbt sources, staging models, and marts
streamlit_dashboard/    Streamlit dashboard entry point
data_profiling/         Local data-profiling script
docs/                   Architecture and project documentation
```

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To build dbt models after configuring the Snowflake profile:

```bash
dbt debug
dbt build
```

## Metric definitions and limitations

- **HPRD**: total nursing hours per resident day
- **RN HPRD**: registered-nurse hours per resident day
- **Occupancy proxy**: resident census divided by certified beds
- **Contractor percentage**: contract nursing hours divided by employee plus contract nursing hours

This dataset represents nursing homes, not hospitals. It does not include department-level staffing, individual shifts, payroll, revenue, patient satisfaction, or length-of-stay data. Staffing and CMS quality measures have different reporting periods, so quality comparisons are exploratory and do not establish causation.

## Security and data handling

Raw source files, generated data, Snowflake credentials, Google service-account credentials, and Streamlit secrets are excluded from version control. Only code, configuration templates, and documentation are committed to GitHub.
