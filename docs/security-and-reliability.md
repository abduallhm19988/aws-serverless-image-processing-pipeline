# Security and Reliability Checklist

- Keep S3 buckets private with Block Public Access enabled.
- Scope bucket policies and CloudFront OAC to the intended distribution and objects.
- Treat pre-signed URLs as bearer credentials: short expiry, narrow object/method scope, generated keys, no URL logging.
- Protect the presign endpoint with an authorizer and throttling; configure exact CORS origins.
- Validate actual file bytes, dimensions, pixel count and formats—not just filename or Content-Type.
- Use a separate least-privilege IAM role for each Lambda task.
- Restrict SQS send permissions to the source bucket and expected account.
- Configure SQS visibility timeout relative to dispatcher timeout, redrive policy, retention and DLQ alarm.
- Enable partial batch response if the dispatcher returns per-record failures.
- Treat S3/SQS events as at-least-once; use deterministic output keys and idempotency/conditional writes.
- Use Step Functions task timeouts, bounded retries/backoff and Catch paths.
- Record sanitized failure details; never store secrets or pre-signed URLs in logs or DynamoDB.
- Alarm on DLQ depth, oldest message age, Lambda errors/throttles and failed/timed-out workflows.
- Decide retention and DynamoDB TTL from requirements; example durations are not universal.