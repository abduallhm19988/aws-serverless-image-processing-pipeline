# Serverless Image Processing Pipeline on AWS

**Course Project 2 — Architecture Overview**

## Overview

This project demonstrates an event-driven serverless pipeline for uploading images, processing them asynchronously, storing the results, and making processed images available to users.

The architecture follows the course reference design. The diagram below is from the reference repository supplied for this assignment; it is shown here as the architecture overview rather than presented as an original diagram created by this repository.

![AWS Serverless Image Processing Pipeline Architecture](https://raw.githubusercontent.com/Hatem979/Serverless-Image-Processing-Pipeline-with-S3-SQS-Lambda/main/architecture/architecture-diagram.png)

[Open the reference project and diagram](https://github.com/Hatem979/Serverless-Image-Processing-Pipeline-with-S3-SQS-Lambda)

## How it works

1. **Request an upload URL:** the user calls Amazon API Gateway. AWS Lambda generates a short-lived pre-signed URL.
2. **Upload the original image:** the client uploads directly to the private source Amazon S3 bucket.
3. **Queue the event:** an S3 object-created notification sends a message to Amazon SQS. A dead-letter queue (DLQ) holds messages that repeatedly fail delivery/processing.
4. **Start processing:** a queue-processing Lambda starts an AWS Step Functions workflow.
5. **Process the image:** the workflow validates the image, resizes it, applies a watermark, stores the processed image, and updates metadata.
6. **Store status and notify:** Amazon DynamoDB stores image metadata/job status; Amazon SNS sends success/failure notifications.
7. **Deliver the result:** Amazon CloudFront serves the processed image from the destination S3 bucket.

## AWS services and their roles

| Service | Role |
|---|---|
| Amazon API Gateway | Exposes the upload URL request endpoint |
| AWS Lambda | Generates pre-signed URLs and processes queue/workflow tasks |
| Amazon S3 | Stores original and processed images |
| Amazon SQS + DLQ | Buffers work and isolates repeatedly failing messages |
| AWS Step Functions | Coordinates the image-processing steps |
| Amazon DynamoDB | Stores job status and image metadata |
| Amazon SNS | Sends completion/failure notifications |
| Amazon CloudFront | Delivers processed images to users |

## Key design points

- Keep source and destination buckets separate to avoid triggering the pipeline again on processed output.
- Keep S3 buckets private; use CloudFront Origin Access Control (OAC) for access to the output bucket.
- SQS messages and S3 events can be delivered more than once, so processing should be idempotent.
- Use least-privilege IAM roles, short-lived pre-signed URLs, input validation, and CloudWatch monitoring.
- Configure retries, DLQ redrive, lifecycle rules, and retention based on the project requirements.

## Project status

This repository documents the architecture and flow. It does **not** claim that the AWS resources have been deployed or tested.

## Reference

- [Course reference repository](https://github.com/Hatem979/Serverless-Image-Processing-Pipeline-with-S3-SQS-Lambda)
- [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
- [Amazon S3 event notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html)
- [Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [CloudFront Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
