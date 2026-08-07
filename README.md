# Healthcare Analytics Project

## Project Overview

This project is a healthcare analytics and data engineering workflow focused on staffing and operational performance data. It combines raw data ingestion, transformation, data profiling, and reporting in a structured project layout.

The goal is to turn raw healthcare source files into a more usable analytics-ready foundation for downstream reporting and exploration.

## Current Project Structure

- data/ - source data files used by the project
- data_profiling/ - Python profiling script and generated Excel output
- docs/ - architecture and project images
- glue_jobs/ - AWS Glue job scripts for ingestion and transformation

## Data Flow

The project currently includes:

- Google Drive to S3 ingestion via a Glue job
- PBJ and CMS-related bronze-to-silver transformations
- Silver-to-gold metric processing
- Data profiling scripts that generate Excel-based reports

## Local Development Setup

1. Create and activate a Python virtual environment

   - python3 -m venv .venv
   - source .venv/bin/activate
2. Install dependencies

   - pip install -r requirements.txt
3. Run the profiling script

   - python data_profiling/data_profiling.py

## Notes

- The repository includes local development files such as notes.txt, which are intentionally ignored by Git.
- The project uses Python for profiling and reporting tasks, and Glue jobs for the pipeline layer.

## Planned Direction

The project is being organized around a modern data lake and analytics workflow using:

- AWS Glue
- Amazon S3
- Snowflake
- dbt
- Streamlit
