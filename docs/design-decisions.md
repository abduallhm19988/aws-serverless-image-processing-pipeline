# Design Decisions and Trade-offs

- **SQS before Step Functions:** SQS buffers bursts and separates upload events from workflow-start capacity. A Lambda dispatcher consumes SQS messages and starts the state machine; the queue does not directly start Step Functions in this design.
- **Step Functions Standard:** selected for a visible multi-step workflow with execution history, retries, and catch paths. Validate costs and semantics against real throughput before choosing a workflow type.
- **Separate source/output buckets:** avoids recursive processing of the output objects.
- **SQS Standard:** S3 event notifications do not directly target SQS FIFO queues. Standard delivery can be duplicated or unordered; consumers must be idempotent.
- **DynamoDB:** stores job status and metadata by job ID; images remain in S3.
- **CloudFront OAC:** allows CloudFront to access a private S3 origin. It is not viewer-level authorization; use signed URLs/cookies if per-user privacy is required.
- **Cost/complexity:** not automatically cheaper than one Lambda for a tiny workload. The managed queue/workflow are justified when buffering, retries, observability, tracking and delivery are requirements. Estimate with the AWS Pricing Calculator.