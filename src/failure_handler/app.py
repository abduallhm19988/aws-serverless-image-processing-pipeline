import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
NOTIFICATION_TOPIC_ARN = os.environ["NOTIFICATION_TOPIC_ARN"]
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """Mark a workflow job failed and publish a minimal failure notification."""
    image_id = event.get("imageId") or event.get("key")
    if not image_id:
        raise ValueError("Failure input must contain imageId or key")

    error = event.get("processingError") or {}
    cause = error.get("Cause", "Workflow failed")
    error_name = error.get("Error", "ProcessingError")

    table.update_item(
        Key={"ImageId": image_id},
        UpdateExpression="SET #status = :failed, UpdatedAt = :updated, ErrorCode = :error",
        ExpressionAttributeNames={"#status": "Status"},
        ExpressionAttributeValues={
            ":failed": "FAILED",
            ":updated": datetime.now(timezone.utc).isoformat(),
            ":error": str(error_name)[:200],
        },
    )

    message = {
        "imageId": image_id,
        "status": "FAILED",
        "error": str(error_name)[:200],
        "details": str(cause)[:500],
    }
    sns.publish(
        TopicArn=NOTIFICATION_TOPIC_ARN,
        Subject="Image processing failed",
        Message=json.dumps(message),
    )

    logger.warning("Image processing failed for %s (%s)", image_id, error_name)
    return {"imageId": image_id, "status": "FAILED"}
