# Serverless Image Processing Pipeline on AWS

**Course Project 2 — Event-driven serverless architecture**

This repository presents a proposed AWS solution for securely uploading images, processing them asynchronously, tracking each job, and serving processed assets through CloudFront.

> **Project status:** architecture and documentation only. The AWS resources have not been deployed or load-tested as part of this repository.

## Architecture

![Architecture overview](architecture/serverless-image-processing-pipeline.svg)

Open the [editable Draw.io diagram](architecture/serverless-image-processing-pipeline.drawio) with [diagrams.net](https://app.diagrams.net/) to inspect or change the components and flows.

## What happens

1. **Request upload permission:** a client calls API Gateway. A Lambda function validates the request and returns a short-lived, object-scoped pre-signed S3 upload authorization.
2. **Upload directly to S3:** the client uploads the image to a private source bucket. Image bytes do not pass through API Gateway or Lambda.
3. **Buffer the event:** an S3 Object Created notification sends an event to an SQS Standard queue. A redrive policy routes repeatedly failing messages to a dead-letter queue (DLQ).
4. **Start the workflow:** an SQS event source mapping invokes a Lambda dispatcher, which validates the message and starts a Step Functions Standard execution. SQS does not start Step Functions directly in this design.
5. **Process the image:** the workflow validates the file, creates a resized variant, applies a watermark, extracts metadata, and finalizes the job. Functions read/write S3 objects and pass only object keys and compact metadata through workflow state.
6. **Record and notify:** DynamoDB stores job status and metadata. SNS publishes success or failure notifications.
7. **Serve the result:** CloudFront retrieves processed assets from a private S3 output bucket using Origin Access Control (OAC). OAC protects the origin; use signed CloudFront URLs/cookies if viewer-level authorization is required.

## Why these services?

| Service | Responsibility |
|---|---|
| API Gateway + Lambda | Authorize uploads and generate pre-signed upload details |
| Amazon S3 | Store original and processed images separately |
| Amazon SQS + DLQ | Buffer bursts, retry delivery, isolate poison messages |
| AWS Lambda | Dispatch queue messages and perform individual processing tasks |
| AWS Step Functions Standard | Orchestrate steps, retries, timeouts, and failure handling |
| Amazon DynamoDB | Track job status, timestamps, dimensions, and output keys |
| Amazon SNS | Notify subscribers of completion or failure |
| Amazon CloudFront + OAC | Cache and serve output objects without public S3 access |
| Amazon CloudWatch | Logs, metrics, dashboards, and alarms |

## Design decisions worth understanding

- S3 event notifications and SQS Standard provide at-least-once delivery; duplicates and out-of-order events must be handled.
- Use an idempotency key such as bucket + key + version ID/ETag and conditional DynamoDB writes to prevent duplicate processing.
- Keep the source and output buckets separate to avoid recursive object-created events.
- Configure the source bucket and SQS queue in the same Region, and restrict the queue policy to the intended bucket.
- Keep S3 buckets private, enable Block Public Access, use least-privilege IAM roles, and scope CloudFront OAC to the intended distribution.
- Do not put image bytes in Step Functions state; pass S3 keys and small metadata only.
- Treat retention periods, file-size limits, retry counts, and TTL as requirements-driven configuration—not universal defaults.

## Documentation

- [Component guide](docs/component-guide.md)
- [Arabic end-to-end walkthrough](docs/flow-walkthrough-ar.md)
- [API contract](docs/api-contract.md)
- [Design decisions and trade-offs](docs/design-decisions.md)
- [Security and reliability](docs/security-and-reliability.md)
- [IAM permission outline](docs/iam-permissions.md)
- [Cost and test plan](docs/cost-and-test-plan.md)
- [Course requirement mapping](docs/requirement-mapping.md)
- [Sample Step Functions definition](samples/step-functions-definition.asl.json)
- [Sample DynamoDB job record](samples/dynamodb-job-record.json)
- [Sample S3 event](samples/s3-event-sample.json)
- [Sample pre-signed upload response](samples/presign-response.json)

## Validation checklist

- [ ] The API rejects unauthorized upload URL requests and applies request throttling.
- [ ] Valid images create an S3 event and a tracked processing job.
- [ ] Unsupported, corrupt, or oversized images fail safely.
- [ ] Duplicate events do not create inconsistent records or duplicate output variants.
- [ ] Transient failures retry; repeated queue delivery failures reach the DLQ.
- [ ] Step Functions failure handling updates the job and publishes a failure notification.
- [ ] Processed images are retrievable through CloudFront while anonymous direct S3 access is denied.
- [ ] CloudWatch alarms cover DLQ depth, queue age, Lambda errors/throttles, and failed workflow executions.

## Official references

- [S3 event notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html)
- [Lambda with SQS event source mappings](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [SQS/Lambda error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [Step Functions best practices](https://docs.aws.amazon.com/step-functions/latest/dg/sfn-best-practices.html)
- [CloudFront OAC for private S3 origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
