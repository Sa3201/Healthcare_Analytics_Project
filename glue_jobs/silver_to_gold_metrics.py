"""Glue job 4: create Gold tables for the Streamlit dashboard.

Example parameters in AWS Glue:
--silver-folder s3://my-bucket/silver/
--gold-folder s3://my-bucket/gold/
"""

import argparse
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def get_arguments():
    parser = argparse.ArgumentParser(description="Silver to Gold healthcare metrics job")
    parser.add_argument("--silver-folder", required=True)
    parser.add_argument("--gold-folder", required=True)
    return parser.parse_known_args()[0]


def main():
    args = get_arguments()
    spark = SparkSession.builder.appName("silver-to-gold-healthcare-metrics").getOrCreate()
    silver = args.silver_folder.rstrip("/")
    gold = args.gold_folder.rstrip("/")

    staffing = spark.read.parquet(silver + "/silver_daily_staffing/")
    facility = spark.read.parquet(silver + "/silver_facility/")
    quality = spark.read.parquet(silver + "/silver_quality_measures/")

    # This table is one facility per day and is the main source for dashboard charts.
    daily = (
        staffing.join(facility.select("facility_ccn", "certified_beds"), "facility_ccn", "left")
        .withColumn(
            "total_nursing_hours",
            F.col("rn_hours") + F.col("lpn_hours") + F.col("cna_hours")
            + F.col("director_rn_hours") + F.col("rn_admin_hours") + F.col("lpn_admin_hours")
            + F.col("nurse_aide_training_hours") + F.col("medication_aide_hours"),
        )
        .withColumn(
            "staffing_hours_per_resident_day",
            F.when(F.col("resident_census") > 0, F.col("total_nursing_hours") / F.col("resident_census")),
        )
        .withColumn(
            "rn_hours_per_resident_day",
            F.when(F.col("resident_census") > 0, F.col("rn_hours") / F.col("resident_census")),
        )
        .withColumn(
            "occupancy_rate_proxy",
            F.when(F.col("certified_beds") > 0, F.col("resident_census") / F.col("certified_beds")),
        )
    )

    # This table makes facility and state comparisons much faster in Streamlit.
    quarterly = (
        daily.groupBy("facility_ccn", "facility_name", "state", "calendar_quarter")
        .agg(
            F.count("work_date").alias("days_reported"),
            F.avg("resident_census").alias("average_daily_census"),
            F.avg("staffing_hours_per_resident_day").alias("average_staffing_hprd"),
            F.avg("rn_hours_per_resident_day").alias("average_rn_hprd"),
            F.avg("occupancy_rate_proxy").alias("average_occupancy_rate"),
            F.sum("total_nursing_hours").alias("total_nursing_hours"),
            F.sum("employee_nursing_hours").alias("employee_nursing_hours"),
            F.sum("contract_nursing_hours").alias("contract_nursing_hours"),
        )
        .withColumn(
            "contract_hour_percentage",
            F.when(
                (F.col("employee_nursing_hours") + F.col("contract_nursing_hours")) > 0,
                F.col("contract_nursing_hours") /
                (F.col("employee_nursing_hours") + F.col("contract_nursing_hours")),
            ),
        )
    )

    # A facility may have several quality measures, so this table is one
    # facility-quarter-measure. It supports exploratory staffing/quality charts.
    staffing_quality = quarterly.join(
        quality.select("facility_ccn", "quality_source", "measure_code", "measure_name", "measure_score", "measure_period"),
        "facility_ccn",
        "left",
    )

    # Start writing the Gold tables to S3. Each table is partitioned by quarter and state for faster queries.
    logger.info("Writing Gold dashboard tables.")
    def write_gold_table(dataframe, output_path):
        (
            dataframe
            .withColumn("s3_calendar_quarter", F.col("calendar_quarter"))
            .withColumn("s3_state", F.col("state"))
            .write.mode("overwrite")
            .partitionBy("s3_calendar_quarter", "s3_state")
            .parquet(output_path)
        )

    write_gold_table(
        daily,
        gold + "/gold_facility_daily_staffing/"
    )

    write_gold_table(
        quarterly,
        gold + "/gold_facility_quarterly_summary/"
    )

    write_gold_table(
        staffing_quality,
        gold + "/gold_staffing_quality_analysis/"
    )

    logger.info("Job finished successfully.")


if __name__ == "__main__":
    main()
