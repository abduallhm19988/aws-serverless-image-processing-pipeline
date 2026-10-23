# AWS Component Guide

## API Gateway + CreateUploadUrl Lambda
Expose a protected `POST /uploads/presign` endpoint. Validate caller, content type and size policy, generate a random object key, and return short-lived pre-signed upload authorization. The client uploads directly to S3; do not proxy image bytes through Lambda.

## Source S3 bucket
Keep Block Public Access enabled. Configure object-created notifications to the SQS Standard queue. Scope the queue policy to the source bucket and expected account. Keep output storage separate to avoid recursive notifications.

## SQS and DLQ
SQS buffers bursts and decouples upload rate from processing capacity. Configure visibility timeout, retention, redrive policy, and alarms. Standard queues are at-least-once and unordered, so consumers must be idempotent. Messages exceeding the receive limit go to the DLQ.

## QueueDispatcher Lambda
An SQS event source mapping invokes the dispatcher, which validates the event and starts a Step Functions execution. SQS does not directly invoke Step Functions in this design. Configure partial batch failure reporting when implemented by the handler.

## Step Functions Standard
Orchestrate validation, resize, watermark, metadata extraction, and finalization. Add task timeouts, bounded retries/backoff, and Catch paths that record sanitized failures and notify SNS. Pass object keys and compact metadata—not image bytes—through workflow state.

## Processing Lambdas
Use an image library such as Pillow packaged in a Lambda layer or container image. Validate actual file content, dimensions, pixel count and formats. Treat image metadata as untrusted input. Use deterministic output keys so retries are safe.

## DynamoDB
Store one item per job: stable job ID, status, source/output keys, dimensions, timestamps, and sanitized error summary. Use conditional writes or explicit idempotency to prevent duplicate events from creating inconsistent states.

## Output S3 + CloudFront OAC
Keep the output bucket private. Grant the specific CloudFront distribution read access through OAC. OAC secures the S3 origin; it does not provide per-user viewer authorization. Use signed CloudFront URLs/cookies if required.

## SNS + CloudWatch
Publish success/failure notifications to configured subscribers. Monitor Lambda errors/throttles, workflow failures/timeouts, queue age, and DLQ depth. Do not put secrets or pre-signed URLs in logs.