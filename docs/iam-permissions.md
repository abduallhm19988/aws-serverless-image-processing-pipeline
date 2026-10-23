# IAM Permissions Outline

Use separate execution roles for each Lambda and the Step Functions state machine. This table describes intent, not ready-to-apply policy JSON.

| Principal | Minimum access (scope to specific resources) |
|---|---|
| CreateUploadUrl Lambda | Generate upload authorization for source bucket/prefix; write its CloudWatch logs |
| S3 notification | Send events to designated SQS queue; queue policy restricts source bucket ARN/account |
| QueueDispatcher Lambda | Receive/delete/change visibility for queue; start the one state machine; write logs |
| ValidateImage Lambda | Read source object; update job record; write logs |
| ResizeImage Lambda | Read source; write output prefix; update required metadata; write logs |
| ApplyWatermark Lambda | Read required object; write output prefix; write logs |
| ExtractMetadata Lambda | Read object; update metadata; write logs |
| FinalizeJob / RecordFailure | Update designated DynamoDB table; publish to designated SNS topic; write logs |
| Step Functions role | Invoke only the task Lambdas used by the workflow |
| CloudFront OAC | Read required objects from output bucket, scoped to distribution |

Avoid wildcard resources where ARNs are known. Add KMS permissions only if customer-managed keys are selected. Review policies with IAM Access Analyzer before deployment. Never place access keys in source code or sample files.