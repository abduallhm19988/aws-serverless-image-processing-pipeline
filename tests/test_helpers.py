import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Dummy credentials keep boto3 from attempting to discover credentials on a developer machine.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("SOURCE_BUCKET", "example-source-bucket")
os.environ.setdefault("DEST_BUCKET", "example-destination-bucket")
os.environ.setdefault("TABLE_NAME", "ImageMetadata")
os.environ.setdefault("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:111111111111:stateMachine:test")
os.environ.setdefault("NOTIFICATION_TOPIC_ARN", "arn:aws:sns:us-east-1:111111111111:test")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


upload = load_module("upload_url_app", "src/upload_url/app.py")
queue_processor = load_module("queue_processor_app", "src/queue_processor/app.py")
image_processor = load_module("process_image_app", "src/process_image/app.py")


@pytest.mark.parametrize(
    ("content_type", "expected_extension"),
    [
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/webp", ".webp"),
    ],
)
def test_upload_request_accepts_supported_image_types(content_type, expected_extension):
    filename, normalized_type, extension = upload.validate_upload_request(
        {"original_filename": "holiday picture", "content_type": content_type}
    )
    assert filename == "holiday picture"
    assert normalized_type == content_type
    assert extension == expected_extension


def test_upload_request_rejects_unsupported_content_type():
    with pytest.raises(ValueError):
        upload.validate_upload_request(
            {"original_filename": "script.svg", "content_type": "image/svg+xml"}
        )


def test_upload_request_strips_path_from_user_filename():
    filename, _, _ = upload.validate_upload_request(
        {"original_filename": "../../private/photo.jpg", "content_type": "image/jpeg"}
    )
    assert filename == "photo.jpg"


def test_queue_parser_decodes_s3_event_key():
    body = (
        '{"Records":[{"eventName":"ObjectCreated:Put",'
        '"s3":{"bucket":{"name":"example-source-bucket"},'
        '"object":{"key":"incoming%2Fmy+photo.jpg"}}}]}'
    )
    jobs = queue_processor.extract_s3_objects(body)
    assert jobs == [
        {
            "bucket": "example-source-bucket",
            "key": "incoming/my photo.jpg",
            "imageId": "incoming/my photo.jpg",
        }
    ]


def test_queue_parser_ignores_non_incoming_objects():
    body = (
        '{"Records":[{"eventName":"ObjectCreated:Put",'
        '"s3":{"bucket":{"name":"example-source-bucket"},'
        '"object":{"key":"processed%2Fresult.jpg"}}}]}'
    )
    assert queue_processor.extract_s3_objects(body) == []


def test_execution_name_is_stable_and_safe():
    first = queue_processor.execution_name("bucket", "incoming/a.jpg")
    second = queue_processor.execution_name("bucket", "incoming/a.jpg")
    assert first == second
    assert len(first) <= 80
    assert all(char.isalnum() or char in "-_" for char in first)


@pytest.mark.parametrize(
    ("actual_format", "declared_content_type", "expected"),
    [
        ("JPEG", "image/jpeg", ("jpg", "image/jpeg")),
        ("PNG", "image/png", ("png", "image/png")),
        ("WEBP", "image/webp", ("webp", "image/webp")),
    ],
)
def test_image_format_must_match_declared_content_type(
    actual_format, declared_content_type, expected
):
    assert image_processor.validate_image_format(actual_format, declared_content_type) == expected


def test_image_format_rejects_mismatched_content_type():
    with pytest.raises(ValueError, match="metadata declares"):
        image_processor.validate_image_format("PNG", "image/jpeg")


def test_image_format_rejects_unsupported_format():
    with pytest.raises(ValueError, match="Only JPEG, PNG, and WEBP"):
        image_processor.validate_image_format("GIF", "image/gif")
