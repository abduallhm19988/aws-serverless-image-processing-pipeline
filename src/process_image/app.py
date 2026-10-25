import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4

import boto3
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
DEST_BUCKET = os.environ["DEST_BUCKET"]
TABLE_NAME = os.environ["TABLE_NAME"]
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "800"))

table = dynamodb.Table(TABLE_NAME)

SUPPORTED_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


def validate_image_format(actual_format, declared_content_type):
    """Return the output extension and MIME type only when the decoded format matches S3 metadata."""
    details = SUPPORTED_FORMATS.get((actual_format or "").upper())
    if details is None:
        raise ValueError("Only JPEG, PNG, and WEBP images are supported")

    expected_content_type = details[1]
    supplied_content_type = (declared_content_type or "").split(";", 1)[0].strip().lower()
    if supplied_content_type != expected_content_type:
        raise ValueError(
            f"Image bytes decode as {expected_content_type}, "
            f"but S3 metadata declares {supplied_content_type or 'no Content-Type'}"
        )
    return details


def _update_status(image_id, status, **attributes):
    names = {"#status": "Status"}
    values = {
        ":status": status,
        ":updated": datetime.now(timezone.utc).isoformat(),
    }
    update_expression = "SET #status = :status, UpdatedAt = :updated"

    for index, (attribute, value) in enumerate(attributes.items()):
        name_token = f"#n{index}"
        value_token = f":v{index}"
        names[name_token] = attribute
        values[value_token] = value
        update_expression += f", {name_token} = {value_token}"

    table.update_item(
        Key={"ImageId": image_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def lambda_handler(event, context):
    # Step Functions passes {"bucket": "...", "key": "...", "imageId": "..."}.
    payload = event.get("Payload", event)
    bucket = payload.get("bucket")
    key = payload.get("key")
    image_id = payload.get("imageId") or key

    if not bucket or not key or not image_id:
        raise ValueError("Workflow input must contain bucket, key, and imageId")
    if bucket != SOURCE_BUCKET:
        raise ValueError("The event refers to an unapproved source bucket")
    if not key.startswith("incoming/"):
        raise ValueError("Only objects inside incoming/ may be processed")

    # Check metadata before download to avoid allocating /tmp for an oversized file.
    head = s3.head_object(Bucket=bucket, Key=key)
    content_length = int(head.get("ContentLength", 0))
    if content_length <= 0 or content_length > MAX_IMAGE_BYTES:
        raise ValueError(f"Image size must be between 1 and {MAX_IMAGE_BYTES} bytes")

    _update_status(image_id, "PROCESSING")

    local_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="image-", suffix=".bin", dir="/tmp", delete=False) as tmp:
            local_path = tmp.name

        s3.download_file(bucket, key, local_path)

        with Image.open(local_path) as opened:
            actual_format = (opened.format or "").upper()
            extension, content_type = validate_image_format(
                actual_format,
                head.get("ContentType", ""),
            )

            # Force decoding while the file is open. EXIF orientation is corrected
            # before the image is resized, so portrait images keep the expected direction.
            opened.load()
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

            if actual_format == "JPEG" and image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            output_path = f"/tmp/{uuid4().hex}.{extension}"
            try:
                image.save(output_path, format=actual_format)
                s3_key = f"processed/{PurePosixPath(key).stem}-processed.{extension}"
                s3.upload_file(
                    output_path,
                    DEST_BUCKET,
                    s3_key,
                    ExtraArgs={"ContentType": content_type},
                )
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)

        _update_status(
            image_id,
            "COMPLETED",
            ProcessedKey=s3_key,
            ProcessedBucket=DEST_BUCKET,
            ProcessedContentType=content_type,
        )

        return {
            "imageId": image_id,
            "status": "COMPLETED",
            "sourceBucket": bucket,
            "sourceKey": key,
            "destinationBucket": DEST_BUCKET,
            "processedKey": s3_key,
            "contentType": content_type,
        }

    except (UnidentifiedImageError, OSError) as exc:
        # Raising the error lets Step Functions run its Catch/failure branch.
        logger.exception("Unable to decode or process image %s", key)
        raise ValueError(f"Unsupported or unreadable image: {key}") from exc
    finally:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
