# Cost and Test Plan

## Cost drivers
S3 storage/requests, CloudFront requests and transfer, API Gateway calls, Lambda duration/memory, SQS requests, Step Functions Standard transitions, DynamoDB reads/writes/storage, CloudWatch logs/alarms, and SNS deliveries. Do not publish a monthly total without a stated workload and Region. Use the [AWS Pricing Calculator](https://calculator.aws/).

## Cost controls
- Choose lifecycle/retention rules from business requirements.
- Set CloudWatch log retention intentionally.
- Bound image size/dimensions to avoid excessive Lambda runtime/memory.
- Tune CloudFront caching and use stable/versioned output keys.
- Consider DynamoDB on-demand capacity for unpredictable workloads.
- Measure retries and queue depth; retries can increase costs.

## Acceptance tests
1. Authorized request returns short-lived upload authorization; unauthorized request is rejected.
2. Valid image upload creates an S3 event and tracked job.
3. Corrupt, unsupported and oversized files fail safely.
4. Duplicate events do not create duplicate logical jobs or inconsistent status.
5. Transient dispatcher errors retry; repeated failures reach the DLQ.
6. Workflow task failure follows Catch, records FAILED and publishes SNS.
7. Successful processing writes expected variants and metadata.
8. CloudFront can read output while direct anonymous S3 access is denied.
9. CloudWatch alarms trigger for failed executions and a non-empty DLQ.
10. Lifecycle and TTL match the documented retention requirement.

These are proposed tests; do not describe them as passed until actually executed.