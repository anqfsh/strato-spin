from ....core.base_resource import BaseResource
import json
import logging
import re

logger = logging.getLogger(__name__)

class KMSKey(BaseResource):
    resource_type = "kms_key"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["alias"],
            "optional": {
                "description": "",
                "admin_role_arn": None
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            response = self.client.list_aliases()
            for alias in response["Aliases"]:
                if alias["AliasName"] == self.properties["alias"]:
                    return True
            return False
        except self.client.exceptions.ClientError:
            return False

    def create(self):
        admin_role_arn = self.properties.get("admin_role_arn")
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::*:root"},
                    "Action": "kms:*",
                    "Resource": "*"
                }
            ]
        }
        if admin_role_arn:
            policy["Statement"].append({
                "Effect": "Allow",
                "Principal": {"AWS": admin_role_arn},
                "Action": [
                    "kms:Create*",
                    "kms:Describe*",
                    "kms:Enable*",
                    "kms:List*",
                    "kms:Put*",
                    "kms:Update*",
                    "kms:Revoke*",
                    "kms:Disable*",
                    "kms:Get*",
                    "kms:Delete*",
                    "kms:TagResource",
                    "kms:UntagResource",
                    "kms:ScheduleKeyDeletion",
                    "kms:CancelKeyDeletion"
                ],
                "Resource": "*"
            })
        response = self.client.create_key(
            Description=self.properties.get("description", ""),
            Policy=json.dumps(self._replace_self_references(policy)),
            Tags=[{"TagKey": k, "TagValue": v} for k, v in self.tags.items()]
        )
        key_id = response["KeyMetadata"]["KeyId"]
        self.self_outputs = {"arn": response["KeyMetadata"]["Arn"], "key_id": key_id}
        self.client.create_alias(
            AliasName=self.properties["alias"],
            TargetKeyId=key_id
        )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        response = self.client.list_aliases()
        key_id = None
        for alias in response["Aliases"]:
            if alias["AliasName"] == self.properties["alias"]:
                key_id = alias["TargetKeyId"]
                break
        self.self_outputs = {"arn": existing_properties["arn"], "key_id": key_id}
        if key_id:
            if self.tags != existing_properties.get("tags", {}):
                existing_tags = self.client.list_resource_tags(KeyId=key_id).get("Tags", [])
                if existing_tags:
                    self.client.untag_resource(KeyId=key_id, TagKeys=[t["TagKey"] for t in existing_tags])
                self.client.tag_resource(KeyId=key_id, Tags=[{"TagKey": k, "TagValue": v} for k, v in self.tags.items()])
            admin_role_arn = self.properties.get("admin_role_arn")
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::*:root"},
                        "Action": "kms:*",
                        "Resource": "*"
                    }
                ]
            }
            if admin_role_arn:
                policy["Statement"].append({
                    "Effect": "Allow",
                    "Principal": {"AWS": admin_role_arn},
                    "Action": [
                        "kms:Create*",
                        "kms:Describe*",
                        "kms:Enable*",
                        "kms:List*",
                        "kms:Put*",
                        "kms:Update*",
                        "kms:Revoke*",
                        "kms:Disable*",
                        "kms:Get*",
                        "kms:Delete*",
                        "kms:TagResource",
                        "kms:UntagResource",
                        "kms:ScheduleKeyDeletion",
                        "kms:CancelKeyDeletion"
                    ],
                    "Resource": "*"
                })
            policy_json = json.dumps(self._replace_self_references(policy))
            if policy_json != existing_properties.get("policy"):
                self.client.set_key_policy(
                    KeyId=key_id,
                    PolicyName="default",
                    Policy=policy_json
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
                "alias": self.properties["alias"],
                "arn": self.self_outputs.get("arn", ""),
                "key_id": self.self_outputs.get("key_id", "")
            }
        }

    def get_existing_properties(self):
        response = self.client.list_aliases()
        for alias in response["Aliases"]:
            if alias["AliasName"] == self.properties["alias"]:
                key_id = alias["TargetKeyId"]
                tags = self.client.list_resource_tags(KeyId=key_id).get("Tags", [])
                policy = self.client.get_key_policy(KeyId=key_id, PolicyName="default").get("Policy")
                policy = json.loads(policy) if policy else None
                return {
                    "alias": alias["AliasName"],
                    "tags": {t["TagKey"]: t["TagValue"] for t in tags},
                    "arn": f"arn:aws:kms:{self.client.meta.region_name}:{self.client.meta.account_id}:key/{key_id}",
                    "key_id": key_id,
                    "policy": policy
                }
        return {}
