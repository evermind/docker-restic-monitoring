# RESTIC_MON

Exposes restic backup status from s3 to monitoring tools.

Env vars:
* S3_URL (required): URL to S3 restic repository
* AWS_ACCESS_KEY_ID (required): Access key ID for S3
* AWS_SECRET_ACCESS_KEY (required): Access key for S3
* AWS_REGION (default us-east-1): S3 region
* WARN_AGE_HOURS (default 36): Age of backup in hours for "warning" status
* CRIT_AGE_HOURS (default 73): Age of backup in hours for "critical" status
* BUCKET_PREFIX (default: none): Check only buckets with this prefix. The prefix is on status messages removed.

Endpoints (at port 8080):

* /json: returns a JSON object with "status" (OK|WARNING|CRITICAL) and "message" with a detailed message

