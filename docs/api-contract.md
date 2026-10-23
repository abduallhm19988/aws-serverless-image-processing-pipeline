# API Contract (proposed)

## POST /uploads/presign
**Purpose:** authorize a client to upload one image directly to the private source S3 bucket.

Request example:
```json
{"fileName":"photo.jpg","contentType":"image/jpeg","contentLength":524288}
```

Successful response example:
```json
{"jobId":"generated-job-id","uploadMethod":"POST","uploadUrl":"short-lived-presigned-url","fields":{"key":"incoming/generated-job-id/photo.jpg","Content-Type":"image/jpeg"},"expiresInSeconds":300}
```

Values are illustrative; exact pre-signed POST fields depend on implementation. Do not hard-code credentials or log the URL. Validate MIME type, enforce content-length conditions in the signed policy where supported, and validate actual file bytes again during processing.

A status-query API is an optional extension. Suggested states: `UPLOADED`, `PROCESSING`, `SUCCEEDED`, `FAILED`. Return 4xx for invalid/unauthorized requests and 429 when throttled; never expose internal exception messages.