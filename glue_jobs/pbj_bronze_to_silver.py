"""Glue job 2: clean the PBJ daily staffing file and write a Silver table.

Example parameters in AWS Glue:
--bronze-path s3://my-bucket/bronze/nursing_homes/PBJ_Daily_Nurse_Staffing_Q2_2024.csv
--silver-path s3://my-bucket/silver/silver_daily_staffing/
"""

import argparse
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def get_arguments():
    """Get the S3 input and output paths passed to the Glue job."""
    parser = argparse.ArgumentParser(description="PBJ Bronze to Silver job")
    parser.add_argument("--bronze-path", required=True)
    parser.add_argument("--silver-path", required=True)
    return parser.parse_known_args()[0]


def hours(column_name):
    """Turn missing hour values into zero before doing math."""
    return F.coalesce(F.col(column_name).cast("double"), F.lit(0.0))


def main():
    args = get_arguments()
    spark = SparkSession.builder.appName("pbj-bronze-to-silver").getOrCreate()

    logger.info("Reading PBJ data from %s", args.bronze_path)
    raw = spark.read.option("header", True).option("encoding", "ISO-8859-1").csv(args.bronze_path)

    staffing = raw.select(
        F.lpad(F.trim(F.col("PROVNUM").cast("string")), 6, "0").alias("facility_ccn"),
        F.to_date("WorkDate", "yyyyMMdd").alias("work_date"),
        F.col("CY_Qtr").alias("calendar_quarter"),
        F.trim("PROVNAME").alias("facility_name"),
        F.trim("STATE").alias("state"),
        F.col("MDScensus").cast("integer").alias("resident_census"),
        hours("Hrs_RN").alias("rn_hours"),
        hours("Hrs_LPN").alias("lpn_hours"),
        hours("Hrs_CNA").alias("cna_hours"),
        hours("Hrs_RNDON").alias("director_rn_hours"),
        hours("Hrs_RNadmin").alias("rn_admin_hours"),
        hours("Hrs_LPNadmin").alias("lpn_admin_hours"),
        hours("Hrs_NAtrn").alias("nurse_aide_training_hours"),
        hours("Hrs_MedAide").alias("medication_aide_hours"),
        sum(hours(column) for column in [
            "Hrs_RNDON_emp", "Hrs_RNadmin_emp", "Hrs_RN_emp", "Hrs_LPNadmin_emp",
            "Hrs_LPN_emp", "Hrs_CNA_emp", "Hrs_NAtrn_emp", "Hrs_MedAide_emp",
        ]).alias("employee_nursing_hours"),
        sum(hours(column) for column in [
            "Hrs_RNDON_ctr", "Hrs_RNadmin_ctr", "Hrs_RN_ctr", "Hrs_LPNadmin_ctr",
            "Hrs_LPN_ctr", "Hrs_CNA_ctr", "Hrs_NAtrn_ctr", "Hrs_MedAide_ctr",
        ]).alias("contract_nursing_hours"),
    )

    duplicates = staffing.groupBy("facility_ccn", "work_date").count().filter("count > 1").count()
    if duplicates:
        raise ValueError(f"Found {duplicates} duplicate facility-day records.")

    valid_rows = staffing.filter(
        F.col("facility_ccn").rlike("^[0-9]{6}$")
        & F.col("work_date").isNotNull()
        & (F.col("resident_census") >= 0)
    )

    logger.info("Writing Silver staffing table to %s", args.silver_path)
    valid_rows.write.mode("overwrite").partitionBy("state").parquet(args.silver_path)
    logger.info("Job finished successfully.")


if __name__ == "__main__":
    main()
