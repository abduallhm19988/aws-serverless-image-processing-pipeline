# Course Requirement Mapping

| Requirement | Proposed component | Evidence |
|---|---|---|
| Upload images | API Gateway, presign Lambda, source S3 | README and API contract |
| Event-driven processing | S3 notification, SQS | Architecture diagram and component guide |
| Retry/failure isolation | SQS DLQ, Step Functions Retry/Catch | Security/reliability and design docs |
| Image transformation | Lambda processing tasks | Component guide and sample ASL |
| Orchestration | Step Functions Standard | Architecture diagram and sample ASL |
| Metadata/status | DynamoDB | Sample job record |
| Processed image delivery | Output S3, CloudFront OAC | README and diagram |
| Notifications | SNS | Component guide |
| Security | Least-privilege IAM, private S3, OAC | IAM and security docs |
| Monitoring | CloudWatch | README and test plan |

## Scope note
This repository provides architecture and documentation, not a deployed implementation. Lambda source code, infrastructure-as-code, live endpoints, and deployment evidence are not included.