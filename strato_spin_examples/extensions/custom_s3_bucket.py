from strato_spin.resources.aws.s3_bucket.s3_bucket import S3Bucket
import logging

logger = logging.getLogger(__name__)

class CustomS3Bucket(S3Bucket):
    required_tags = ["ApplicationID", "CostCentre", "Environment", "SupportGroup"]

    @classmethod
    def get_schema(cls):
        schema = super().get_schema()
        schema["tags"]["required"] = cls.required_tags
        return schema
