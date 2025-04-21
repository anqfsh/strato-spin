from ....core.base_resource import BaseResource
import os
import hashlib
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Upload(BaseResource):
    resource_type = "s3_upload"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["bucket_name", "source_path"],
            "optional": {
                "destination_key": ""
            },
            "tags": {
                "required": [],
                "optional": []
            }
        }

    def exists(self):
        source_path = self.properties["source_path"]
        bucket_name = self.properties["bucket_name"]
        destination_key = self.properties.get("destination_key", "").rstrip("/")

        if os.path.isfile(source_path):
            return self._check_file(bucket_name, destination_key, source_path)
        elif os.path.isdir(source_path):
            for root, _, files in os.walk(source_path):
                for file_name in files:
                    local_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(local_path, source_path)
                    s3_key = f"{destination_key}/{relative_path}" if destination_key else relative_path
                    if not self._check_file(bucket_name, s3_key, local_path):
                        return False
            return True
        else:
            raise ValueError(f"Source path {source_path} is not a file or directory")

    def _check_file(self, bucket_name, s3_key, local_path):
        try:
            s3_obj = self.client.head_object(Bucket=bucket_name, Key=s3_key.lstrip("/"))
            s3_etag = s3_obj["ETag"].strip('"')
            local_etag = self._calculate_etag(local_path)
            return s3_etag == local_etag
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise e

    def _calculate_etag(self, file_path, chunk_size=8 * 1024 * 1024):
        md5s = []
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            if file_size <= chunk_size:
                return hashlib.md5(f.read()).hexdigest()
            else:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    md5s.append(hashlib.md5(chunk).digest())
                md5 = hashlib.md5(b"".join(md5s))
                return f"{md5.hexdigest()}-{len(md5s)}"

    def create(self):
        self._upload_files()
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        self._upload_files()
        self.outputs = self.get_outputs()

    def _upload_files(self):
        source_path = self.properties["source_path"]
        bucket_name = self.properties["bucket_name"]
        destination_key = self.properties.get("destination_key", "").rstrip("/")

        if os.path.isfile(source_path):
            s3_key = f"{destination_key}/{os.path.basename(source_path)}" if destination_key else os.path.basename(source_path)
            self.client.upload_file(source_path, bucket_name, s3_key.lstrip("/"))
            logger.info(f"Uploaded {source_path} to s3://{bucket_name}/{s3_key}")
        elif os.path.isdir(source_path):
            for root, _, files in os.walk(source_path):
                for file_name in files:
                    local_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(local_path, source_path)
                    s3_key = f"{destination_key}/{relative_path}" if destination_key else relative_path
                    self.client.upload_file(local_path, bucket_name, s3_key.lstrip("/"))
                    logger.info(f"Uploaded {local_path} to s3://{bucket_name}/{s3_key}")
        else:
            raise ValueError(f"Source path {source_path} is not a file or directory")

    def get_outputs(self):
        return {
            "properties": {
                "bucket_name": self.properties["bucket_name"],
                "destination_key": self.properties.get("destination_key", "")
            }
        }

    def get_existing_properties(self):
        return {
            "bucket_name": self.properties["bucket_name"],
            "destination_key": self.properties.get("destination_key", ""),
            "tags": {}
        }
