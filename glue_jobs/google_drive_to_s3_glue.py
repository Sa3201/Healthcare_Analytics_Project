"""Copy Google Drive files to an S3 Bronze folder.

This script is designed for an AWS Glue *Python Shell* job. It is a simple
first ingestion step for this portfolio project:

Google Drive -> S3 Bronze -> Glue/Spark transformations -> Snowflake -> dbt

Before running the Glue job
---------------------------
1. Create a Google Cloud service account and enable the Google Drive API.
2. Share the Google Drive file with the service account email address.
3. Save the complete service-account JSON as an AWS Secrets Manager secret.
4. Create a Glue Python Shell job with this script.
5. In Glue job details, add this under "Python library path" / additional
   Python modules:

   google-api-python-client==2.143.0,google-auth==2.34.0

Example Glue job parameters: copy every file in a folder
---------------------------
--google-drive-folder-id  1AbCdEfExampleFolderId
--google-secret-name    healthcare/google-drive-service-account
--s3-bucket             my-healthcare-data-lake
--s3-prefix             bronze/nursing_homes/
--aws-region            us-east-1

To copy one file instead, use ``--google-drive-file-id`` and ``--s3-key``.

The secret must contain the Google service-account JSON object exactly as it
was downloaded from Google Cloud. Do not put passwords or keys in this file.
"""

import argparse
import json
import logging
import os
import tempfile

import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def get_arguments():
    """Read the values entered in the AWS Glue job parameters section."""
    parser = argparse.ArgumentParser(description="Copy one Google Drive file to S3")
    drive_source = parser.add_mutually_exclusive_group(required=True)
    drive_source.add_argument("--google-drive-file-id")
    drive_source.add_argument("--google-drive-folder-id")
    parser.add_argument("--google-secret-name", required=True)
    parser.add_argument("--s3-bucket", required=True)
    s3_destination = parser.add_mutually_exclusive_group(required=True)
    s3_destination.add_argument("--s3-key")
    s3_destination.add_argument("--s3-prefix")
    parser.add_argument("--aws-region", default=os.environ.get("AWS_REGION", "us-east-1"))
    # parse_known_args lets Glue pass its own arguments, such as --JOB_NAME.
    return parser.parse_known_args()[0]


def get_google_credentials(secret_name, region):
    """Get the service-account JSON from AWS Secrets Manager."""
    secrets_client = boto3.client("secretsmanager", region_name=region)
    response = secrets_client.get_secret_value(SecretId=secret_name)
    service_account_info = json.loads(response["SecretString"])

    return service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )


def build_drive_service(credentials):
    """Create a Google Drive client with read-only access."""
    return build("drive", "v3", credentials=credentials)


def list_google_drive_folder_files(drive_service, folder_id):
    """Return every non-folder file directly inside a Google Drive folder."""
    files = []
    page_token = None

    while True:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=page_token,
            orderBy="name",
        ).execute()
        files.extend(
            file_info
            for file_info in response.get("files", [])
            if file_info["mimeType"] != "application/vnd.google-apps.folder"
        )
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    if not files:
        raise ValueError(f"No files found in Google Drive folder {folder_id}.")

    logger.info("Found %d file(s) in Google Drive folder.", len(files))
    return files


def download_google_drive_file(drive_service, file_id, file_name=None):
    """Download a Drive file to a temporary file and return its path and name."""
    if file_name is None:
        file_info = drive_service.files().get(fileId=file_id, fields="name").execute()
        file_name = file_info["name"]
    logger.info("Downloading Google Drive file: %s", file_name)

    # /tmp is the writable temporary folder available to Glue jobs.
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir="/tmp")
    request = drive_service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(temp_file, request)

    finished = False
    while not finished:
        status, finished = downloader.next_chunk()
        if status:
            logger.info("Download progress: %d%%", int(status.progress() * 100))

    temp_file.close()
    return temp_file.name, file_name


def upload_file_to_s3(local_file_path, bucket, key, region):
    """Upload the downloaded file to the requested S3 Bronze location."""
    s3_client = boto3.client("s3", region_name=region)
    logger.info("Uploading to s3://%s/%s", bucket, key)
    s3_client.upload_file(local_file_path, bucket, key)


def make_s3_key(prefix, file_name):
    """Build an S3 key safely from a prefix and a Drive filename."""
    clean_prefix = prefix.strip("/")
    clean_name = os.path.basename(file_name)
    return f"{clean_prefix}/{clean_name}" if clean_prefix else clean_name


def main():
    args = get_arguments()
    local_file_path = None

    try:
        credentials = get_google_credentials(args.google_secret_name, args.aws_region)
        drive_service = build_drive_service(credentials)

        if args.google_drive_file_id:
            files = [{"id": args.google_drive_file_id, "name": None}]
        else:
            files = list_google_drive_folder_files(drive_service, args.google_drive_folder_id)

        for file_info in files:
            try:
                local_file_path, file_name = download_google_drive_file(
                    drive_service,
                    file_info["id"],
                    file_info["name"],
                )
                s3_key = args.s3_key or make_s3_key(args.s3_prefix, file_name)
                upload_file_to_s3(local_file_path, args.s3_bucket, s3_key, args.aws_region)
                logger.info("Success: %s is now in S3.", file_name)
            finally:
                if local_file_path and os.path.exists(local_file_path):
                    os.remove(local_file_path)
                local_file_path = None
    finally:
        # Remove the temporary copy even if the job fails during the S3 upload.
        if local_file_path and os.path.exists(local_file_path):
            os.remove(local_file_path)


if __name__ == "__main__":
    main()
