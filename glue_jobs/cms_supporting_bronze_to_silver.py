"""Glue job 3: clean CMS supporting files and write three Silver tables.

Example parameters in AWS Glue:
--bronze-folder s3://my-bucket/bronze/nursing_homes/
--silver-folder s3://my-bucket/silver/
"""

import argparse
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def get_arguments():
    parser = argparse.ArgumentParser(description="CMS supporting Bronze to Silver job")
    parser.add_argument("--bronze-folder", required=True)
    parser.add_argument("--silver-folder", required=True)
    return parser.parse_known_args()[0]


def read_csv(spark, folder, file_name):
    """Read one CMS CSV file from the Bronze folder."""
    return spark.read.option("header", True).option("encoding", "ISO-8859-1").csv(folder.rstrip("/") + "/" + file_name)


def ccn(column_name):
    return F.lpad(F.trim(F.col(column_name).cast("string")), 6, "0")


def main():
    args = get_arguments()
    spark = SparkSession.builder.appName("cms-supporting-bronze-to-silver").getOrCreate()

    provider = read_csv(spark, args.bronze_folder, "NH_ProviderInfo_Oct2024.csv")
    claims = read_csv(spark, args.bronze_folder, "NH_QualityMsr_Claims_Oct2024.csv")
    vbp = read_csv(spark, args.bronze_folder, "FY_2024_SNF_VBP_Facility_Performance.csv")
    citations = read_csv(spark, args.bronze_folder, "NH_HealthCitations_Oct2024.csv")

    facility = provider.select(
        ccn("CMS Certification Number (CCN)").alias("facility_ccn"),
        F.trim("Provider Name").alias("facility_name"),
        F.trim("State").alias("state"),
        F.col("Number of Certified Beds").cast("integer").alias("certified_beds"),
        F.col("Average Number of Residents per Day").cast("double").alias("average_residents_per_day"),
        F.col("Ownership Type").alias("ownership_type"),
        F.col("Overall Rating").cast("integer").alias("overall_rating"),
        F.col("Staffing Rating").cast("integer").alias("staffing_rating"),
        F.col("Total nursing staff turnover").cast("double").alias("nursing_staff_turnover"),
        F.col("Registered Nurse turnover").cast("double").alias("rn_turnover"),
    )

    claims_quality = claims.select(
        ccn("CMS Certification Number (CCN)").alias("facility_ccn"),
        F.trim("State").alias("state"),
        F.lit("claims_quality_measure").alias("quality_source"),
        F.col("Measure Code").alias("measure_code"),
        F.col("Measure Description").alias("measure_name"),
        F.col("Resident type").alias("resident_type"),
        F.col("Adjusted Score").cast("double").alias("measure_score"),
        F.col("Measure Period").alias("measure_period"),
    )

    # The VBP file has facility readmission rates. Change the names later if you
    # decide to include additional VBP measures.
    vbp_quality = vbp.select(
        ccn("CMS Certification Number (CCN)").alias("facility_ccn"),
        F.trim("State").alias("state"),
        F.lit("vbp_readmission_rate").alias("quality_source"),
        F.lit("FY2022_READMISSION_RATE").alias("measure_code"),
        F.lit("FY 2022 Risk-Standardized Readmission Rate").alias("measure_name"),
        F.lit(None).cast("string").alias("resident_type"),
        F.col("Performance Period: FY 2022 Risk-Standardized Readmission Rate").cast("double").alias("measure_score"),
        F.lit("FY 2022").alias("measure_period"),
    )
    quality_measures = claims_quality.unionByName(vbp_quality)

    health_citations = citations.select(
        ccn("CMS Certification Number (CCN)").alias("facility_ccn"),
        F.trim("State").alias("state"),
        F.to_date("Survey Date", "MM/dd/yyyy").alias("survey_date"),
        F.col("Survey Type").alias("survey_type"),
        F.col("Deficiency Category").alias("deficiency_category"),
        F.col("Deficiency Tag Number").alias("deficiency_tag_number"),
        F.col("Scope Severity Code").alias("scope_severity_code"),
        F.col("Complaint Deficiency").alias("complaint_deficiency"),
    )

    silver = args.silver_folder.rstrip("/")
    logger.info("Writing Silver facility, quality, and citation tables.")
    facility.write.mode("overwrite").parquet(silver + "/silver_facility/")
    quality_measures.write.mode("overwrite").partitionBy("state").parquet(silver + "/silver_quality_measures/")
    health_citations.write.mode("overwrite").partitionBy("state").parquet(silver + "/silver_health_citations/")
    logger.info("Job finished successfully.")


if __name__ == "__main__":
    main()
