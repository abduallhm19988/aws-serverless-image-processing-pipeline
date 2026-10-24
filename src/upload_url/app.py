import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import PurePath

import boto3

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
TABLE_NAME = os.environ["TABLE_NAME"]
URL_EXPIRATION_SECONDS = int(os.getenv("URL_EXPIRATION_SECONDS", "300"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

table = dynamodb.Table(TABLE_NAME)

CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(payload),
    }


def _read_request_body(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, dict):
        return body
    return json.loads(body)


def validate_upload_request(payload):
    """Validate the request and return a safe filename, media type, and extension."""
    content_type = str(payload.get("content_type", "")).lower().strip()
    extension = CONTENT_TYPES.get(content_type)
    if extension is None:
        raise ValueError("content_type must be image/jpeg, image/png, or image/webp")

    original_filename = str(payload.get("original_filename", "image" + extension))
    # Do not use client input as an S3 path; retain only its basename.
    original_filename = PurePath(original_filename.replace("\\", "/")).name
    if not original_filename or original_filename in {".", ".."}:
        raise ValueError("original_filename must be a valid filename")
    if len(original_filename) > 255:
        raise ValueError("original_filename is too long")

    return original_filename, content_type, extension


def lambda_handler(event, context):
    try:
        payload = _read_request_body(event)
        original_filename, content_type, extension = validate_upload_request(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return _response(400, {"message": str(exc)})

    image_id = f"incoming/{uuid.uuid4().hex}{extension}"
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        table.put_item(
            Item={
                "ImageId": image_id,
                "OriginalFilename": original_filename,
                "ContentType": content_type,
                "Status": "UPLOAD_URL_ISSUED",
                "CreatedAt": created_at,
                "UpdatedAt": created_at,
            },
            ConditionExpression="attribute_not_exists(ImageId)",
        )

        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": SOURCE_BUCKET,
                "Key": image_id,
                "ContentType": content_type,
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )
    except Exception:
        logger.exception("Could not create an upload URL")
        # Do not expose internal exception text or account details to the caller.
        return _response(500, {"message": "Unable to create an upload URL"})

    return _response(
        200,
        {
            "image_id": image_id,
            "upload_url": upload_url,
            "method": "PUT",
            "required_headers": {"Content-Type": content_type},
            "expires_in_seconds": URL_EXPIRATION_SECONDS,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "message": "Upload the file directly to S3 using the returned URL.",
        },
    )
