# Project Review: Serverless Image Processing Pipeline

## Project status

This repository is an implementation starter for a serverless image-processing workflow. The presence of source code and an AWS SAM template does not prove that the stack has been deployed or integration-tested in an AWS account. Treat deployment evidence as pending until a real test run has been completed and documented.

## Architecture at a glance

1. The client calls API Gateway to request an upload URL.
2. The Upload URL Lambda validates the requested media type, creates a unique key under `incoming/`, writes an initial DynamoDB record, and returns a short-lived S3 pre-signed PUT URL.
3. The client uploads the image directly to the private source S3 bucket. The image bytes do not pass through API Gateway or Lambda.
4. An S3 `ObjectCreated` event is delivered to SQS.
5. The Queue Processor Lambda consumes the SQS message and starts a Standard Step Functions execution.
6. The image-processing Lambda checks the source bucket, key prefix, object size, decoded image format, declared content type, and pixel dimensions. It corrects EXIF orientation, resizes the image with Pillow, writes the output to the private destination bucket, and updates DynamoDB.
7. Step Functions publishes a success notification through SNS. Its Catch path invokes the Failure Handler Lambda on processing failure.
8. CloudFront uses Origin Access Control (OAC) to read processed objects from the private destination bucket.

## What was reviewed

- `template.yaml`: resource wiring, parameters, bucket policies, SQS redrive configuration, Lambda environment variables, and IAM action scopes.
- `src/upload_url/app.py`: request validation, generated object keys, DynamoDB initialization, and pre-signed URL response.
- `src/queue_processor/app.py`: S3 event parsing, URL-decoding, stable execution names, and partial-batch failure reporting.
- `src/process_image/app.py`: source validation, size checks, Pillow decoding, image transformation, S3 output, and metadata updates.
- `src/failure_handler/app.py` and `statemachine/image-processing.asl.json`: workflow failure handling and notifications.
- `tests/test_helpers.py` and `.github/workflows/ci.yml`: helper tests and CI validation/build steps.
- `README.md`: setup, architecture, testing, security, limitations, and AWS documentation.

## Hardening changes in this review branch

### 1. Check decoded image dimensions before loading pixel data

A compressed image can be small in S3 but expand into a very large pixel buffer. The image processor now checks the decoded width × height before calling Pillow's `load()`. This adds a separate limit in addition to the uploaded-object byte limit.

Configure it with the SAM parameter `MaxImagePixels` (default: 40,000,000 pixels). The limit can be adjusted for the expected workload, while remaining bounded by the template's parameter constraints.

### 2. Make the upload response less misleading

The upload API previously returned `max_upload_bytes`, which could be read as an upload-time S3 restriction. A pre-signed PUT URL does not enforce that maximum size. The response field is now `max_image_bytes`, and its message explicitly says the size limit is checked during processing after the upload.

### 3. Add unit tests for image dimensions

The helper tests now cover accepted dimensions, an image exceeding the configured pixel limit, and invalid zero/negative dimensions.

## Important limitations to disclose

- **No authentication:** the demo API does not authenticate callers or associate uploads with user identities. Add an authorizer (for example, Amazon Cognito), throttling, and abuse controls before exposing it as a public application.
- **Upload size is not blocked at upload time:** an oversized object can reach S3 before the processor rejects it. If S3 must reject it before storage, use a pre-signed POST policy with a `content-length-range` condition or another upload-control design.
- **Pre-signed URL reuse:** a pre-signed PUT URL can be reused until expiry and can overwrite the same object key. The client should use it once and request a new URL for each upload.
- **SQS DLQ and workflow failure are different:** the DLQ handles repeated failures in the SQS consumer path. A Step Functions task failure after the message has been acknowledged follows the state machine's Catch path and Failure Handler.
- **No live deployment evidence is included by default:** run the deployment and end-to-end verification steps, then add genuine screenshots with account identifiers and sensitive details redacted.
- **Operational alarms are not provisioned:** CloudWatch logs and service metrics are available, but alarms/dashboards should be added for a real operational workload.
- **No end-to-end integration test:** the current pytest suite checks helper logic. It does not prove that the complete AWS workflow has run successfully.

## Validation checklist

Run these from the repository root in an environment with Python 3.12, Docker, and AWS SAM CLI installed:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
sam validate --lint
sam build --use-container
```

Then, only if you intend to deploy and accept the associated AWS charges:

1. Review the SAM change set and parameter values.
2. Deploy with unique source and destination bucket names.
3. Request a pre-signed URL and upload a small supported image.
4. Verify the SQS message, Step Functions execution, processed S3 object, DynamoDB status, SNS notification, and CloudFront delivery.
5. Test an unsupported image and an image exceeding the configured limits.
6. Delete the stack and test objects when finished.

A successful local unit-test run and SAM build are not substitutes for an end-to-end AWS deployment test.
