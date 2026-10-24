import hashlib
import json
import logging
import os
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

stepfunctions = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def extract_s3_objects(message_body):
    """Parse image bucket/key pairs from an S3 event sent through SQS."""
    event = json.loads(message_body)

    # S3 can send a one-off test event when notifications are configured.
    if event.get("Event") == "s3:TestEvent":
        return []

    jobs = []
    for record in event.get("Records", []):
        s3_record = record.get("s3")
        event_name = record.get("eventName", "")
        if not s3_record or not event_name.startswith("ObjectCreated:"):
            continue

        bucket = s3_record.get("bucket", {}).get("name")
        encoded_key = s3_record.get("object", {}).get("key")
        if not bucket or not encoded_key:
            raise ValueError("S3 event record is missing bucket or object key")

        key = unquote_plus(encoded_key)
        if not key.startswith("incoming/"):
            logger.info("Ignoring object outside incoming/ prefix: %s", key)
            continue

        jobs.append({"bucket": bucket, "key": key, "imageId": key})

    return jobs


def execution_name(bucket, key):
    """Generate a valid, stable Step Functions name for duplicate S3 events."""
    return hashlib.sha256(f"{bucket}/{key}".encode("utf-8")).hexdigest()[:40]


def start_job(job):
    input_json = json.dumps(job)
    name = execution_name(job["bucket"], job["key"])

    try:
        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=name,
            input=input_json,
        )
        logger.info("Started workflow execution %s for %s", response["executionArn"], job["key"])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ExecutionAlreadyExists":
            # S3/SQS can redeliver an event after a successful workflow start.
            logger.info("Execution already exists for %s; treating as duplicate", job["key"])
            return
        raise


def lambda_handler(event, context):
    failures = []

    for message in event.get("Records", []):
        message_id = message["messageId"]
        try:
            jobs = extract_s3_objects(message["body"])
            for job in jobs:
                start_job(job)
        except Exception:
            logger.exception("Failed to handle SQS message %s", message_id)
            failures.append({"itemIdentifier": message_id})

    # Works with ReportBatchItemFailures on the SQS event source mapping.
    return {"batchItemFailures": failures}
