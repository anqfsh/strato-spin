from ....core.base_resource import BaseResource
import json
import logging
import re

logger = logging.getLogger(__name__)

class S3Bucket(BaseResource):
    resource_type = "s3_bucket"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["bucket_name", "region"],
            "optional": {
                "versioning": False,
                "encryption": {},
                "policy": None
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            self.client.head_bucket(Bucket=self.properties["bucket_name"])
            return True
        except self.client.exceptions.ClientError:
            return False

    def create(self):
        bucket_config = {"LocationConstraint": self.properties["region"]}
        self.client.create_bucket(
            Bucket=self.properties["bucket_name"],
            CreateBucketConfiguration=bucket_config
        )
        self.self_outputs = {"arn": f"arn:aws:s3:::{self.properties['bucket_name']}"}
        if self.properties.get("versioning"):
            self.client.put_bucket_versioning(
                Bucket=self.properties["bucket_name"],
                VersioningConfiguration={"Status": "Enabled"}
            )
        if self.properties.get("encryption", {}).get("kms_key_id"):
            self.client.put_bucket_encryption(
                Bucket=self.properties["bucket_name"],
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "aws:kms",
                                "KMSMasterKeyID": self.properties["encryption"]["kms_key_id"]
                            }
                        }
                    ]
                }
            )
        if self.properties.get("policy"):
            policy = self._replace_self_references(self.properties["policy"])
            if isinstance(policy, dict):
                policy = json.dumps(policy)
            self.client.put_bucket_policy(
                Bucket=self.properties["bucket_name"],
                Policy=policy
            )
        self.client.put_bucket_tagging(
            Bucket=self.properties["bucket_name"],
            Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in self.tags.items()]}
        )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        if self.properties.get("versioning") != existing_properties.get("versioning"):
            status = "Enabled" if self.properties.get("versioning") else "Suspended"
            self.client.put_bucket_versioning(
                Bucket=self.properties["bucket_name"],
                VersioningConfiguration={"Status": status}
            )
        if self.properties.get("encryption", {}).get("kms_key_id") != existing_properties.get("encryption", {}).get("kms_key_id"):
            self.client.put_bucket_encryption(
                Bucket=self.properties["bucket_name"],
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "aws:kms",
                                "KMSMasterKeyID": self.properties["encryption"]["kms_key_id"]
                            }
                        }
                    ]
                }
            )
        self.self_outputs = {"arn": existing_properties["arn"]}
        if self.properties.get("policy") != existing_properties.get("policy"):
            policy = self._replace_self_references(self.properties["policy"])
            if policy:
                if isinstance(policy, dict):
                    policy = json.dumps(policy)
                self.client.put_bucket_policy(
                    Bucket=self.properties["bucket_name"],
                    Policy=policy
                )
            else:
                self.client.delete_bucket_policy(Bucket=self.properties["bucket_name"])
        if self.tags != existing_properties.get("tags", {}):
            self.client.put_bucket_tagging(
                Bucket=self.properties["bucket_name"],
                Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in self.tags.items()]}
            )
        self.outputs = self.get_outputs()

    def _replace_self_references(self, policy):
        """Replace ${self.<field>} in policy with self_outputs"""
        def recursive_replace(obj):
            if isinstance(obj, str):
                return re.sub(r"\${self\.([^}]+)}", lambda m: self.self_outputs.get(m.group(1), m.group(0)), obj)
            elif isinstance(obj, dict):
                return {k: recursive_replace(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursive_replace(item) for item in obj]
            return obj
        return recursive_replace(policy)

    def get_outputs(self):
        return {
            "properties": {
                "bucket_name": self.properties["bucket_name"],
                "arn": self.self_outputs.get("arn", f"arn:aws:s3:::{self.properties['bucket_name']}")
            }
        }

    def get_existing_properties(self):
        versioning = self.client.get_bucket_versioning(Bucket=self.properties["bucket_name"])
        try:
            encryption = self.client.get_bucket_encryption(Bucket=self.properties["bucket_name"])
        except self.client.exceptions.ClientError:
            encryption = {}
        try:
            policy = self.client.get_bucket_policy(Bucket=self.properties["bucket_name"]).get("Policy")
            policy = json.loads(policy) if policy else None
        except self.client.exceptions.ClientError:
            policy = None
        tags = self.client.get_bucket_tagging(Bucket=self.properties["bucket_name"])
        return {
            "versioning": versioning.get("Status") == "Enabled",
            "encryption": encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [{}])[0].get("ApplyServerSideEncryptionByDefault", {}),
            "policy": policy,
            "tags": {t["Key"]: t["Value"] for t in tags.get("TagSet", [])},
            "arn": f"arn:aws:s3:::{self.properties['bucket_name']}"
        }
