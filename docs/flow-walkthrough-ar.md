# شرح مسار المشروع بالعربي

## الفكرة
المشروع بيستقبل صورة، يعالجها في الخلفية، يخزن النسخ الناتجة، ويسجل حالة المعالجة. الهدف إن المستخدم ما يستناش معالجة الصورة داخل request طويل، وإن ضغط الرفع ما يوقفش الـprocessing.

## المسار من البداية للنهاية
1. **Client → API Gateway:** العميل يطلب رابط رفع مؤقت من `POST /uploads/presign`.
2. **API Gateway → Lambda:** Lambda تتحقق من الطلب وتجهز S3 object key ورابط رفع قصير الصلاحية.
3. **Client → Source S3:** الصورة نفسها تترفع مباشرة إلى S3؛ الـAPI مش بتمرر bytes الصورة.
4. **S3 → SQS:** حدث إنشاء object يدخل الطابور. SQS يمتص الزيادة المؤقتة ويفصل الرفع عن المعالجة.
5. **SQS → QueueDispatcher Lambda:** الـevent source mapping يشغل Lambda، وهي تبدأ Step Functions. مهم: SQS مش بيشغل Step Functions مباشرة في التصميم ده.
6. **Step Functions:** تنظم ValidateImage ثم ResizeImage ثم ApplyWatermark ثم ExtractMetadata ثم FinalizeJob.
7. **Output S3 + DynamoDB:** ملفات النتائج في S3، وحالة الـjob والـmetadata في DynamoDB.
8. **SNS:** إشعار نجاح أو فشل بعد تحديث الحالة.
9. **CloudFront + OAC:** المستخدم يجيب الصورة الناتجة من CloudFront، والـorigin في S3 يفضل private.
10. **DLQ + CloudWatch:** الرسائل اللي تفشل باستمرار تروح DLQ؛ CloudWatch ينبه المسؤول عند ارتفاع الأخطاء أو عمر الرسائل.

## 3 حاجات لازم تشرحهم كويس
- **Idempotency:** S3/SQS ممكن يوصلوا event أكتر من مرة. استخدم job key ثابت وconditional writes علشان التكرار ما يفسدش النتيجة.
- **DLQ vs Step Functions Catch:** الـDLQ بتتعامل مع فشل رسائل SQS/dispatcher بعد retries؛ أما Catch فبتتعامل مع فشل task داخل الـworkflow. مش نفس الحاجة.
- **OAC vs user authorization:** OAC بيمنع الوصول المباشر للـS3 origin وبيسمح لـCloudFront يوصل له؛ لكنه لوحده مش بيحدد مين مسموح له يشوف صورة معينة.