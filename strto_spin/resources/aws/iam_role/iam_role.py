from ....core.base_resource import BaseResource
import json
import logging
import botocore.exceptions

logger = logging.getLogger(__name__)

class IAMRole(BaseResource):
    resource_type = "iam_role"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["role_name", "trust_policy"],
            "optional": {
                "inline_policies": [],
                "description": ""
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            self.client.get_role(RoleName=self.properties["role_name"])
            return True
        except self.client.exceptions.NoSuchEntityException:
            return False

    def create(self):
        trust_policy = self.properties["trust_policy"]
        if isinstance(trust_policy, dict):
            trust_policy = json.dumps(trust_policy)
        response = self.client.create_role(
            RoleName=self.properties["role_name"],
            AssumeRolePolicyDocument=trust_policy,
            Description=self.properties.get("description", ""),
            Tags=[{"Key": k, "TagValue": v} for k, v in self.tags.items()]
        )
        self.self_outputs = {"arn": response["Role"]["Arn"]}
        for policy in self.properties.get("inline_policies", []):
            policy_document = policy["policy"]
            if isinstance(policy_document, dict):
                policy_document = json.dumps(self._replace_self_references(policy_document))
            self.client.put_role_policy(
                RoleName=self.properties["role_name"],
                PolicyName=policy["name"],
                PolicyDocument=policy_document
            )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        role_name = self.properties["role_name"]
        trust_policy = self.properties["trust_policy"]
        if isinstance(trust_policy, dict):
            trust_policy = json.dumps(trust_policy)
        if trust_policy != existing_properties.get("trust_policy"):
            self.client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=trust_policy
            )

        description = self.properties.get("description", "")
        if description != existing_properties.get("description", ""):
            self.client.update_role(
                RoleName=role_name,
                Description=description
            )

        existing_policies = existing_properties.get("inline_policies", {})
        for policy in self.properties.get("inline_policies", []):
            policy_name = policy["name"]
            policy_document = policy["policy"]
            if isinstance(policy_document, dict):
                policy_document = json.dumps(self._replace_self_references(policy_document))
            if policy_name not in existing_policies or policy_document != existing_policies.get(policy_name):
                self.client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name,
                    PolicyDocument=policy_document
                )

        for policy_name in existing_policies:
            if not any(p["name"] == policy_name for p in self.properties.get("inline_policies", [])):
                self.client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )

        if self.tags != existing_properties.get("tags", {}):
            existing_tags = self.client.list_role_tags(RoleName=role_name).get("Tags", [])
            if existing_tags:
                self.client.untag_role(RoleName=role_name, TagKeys=[t["Key"] for t in existing_tags])
            self.client.tag_role(RoleName=role_name, Tags=[{"Key": k, "TagValue": v} for k, v in self.tags.items()])

        self.self_outputs = {"arn": existing_properties["arn"]}
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
                "role_name": self.properties["role_name"],
                "arn": self.self_outputs.get("arn", f"arn:aws:iam::{self.client.meta.account_id}:role/{self.properties['role_name']}")
            }
        }

    def get_existing_properties(self):
        role_name = self.properties["role_name"]
        try:
            role = self.client.get_role(RoleName=role_name)["Role"]
            trust_policy = json.loads(role["AssumeRolePolicyDocument"])
            tags = self.client.list_role_tags(RoleName=role_name).get("Tags", [])
            inline_policies = {}
            for policy_name in self.client.list_role_policies(RoleName=role_name)["PolicyNames"]:
                policy_doc = self.client.get_role_policy(RoleName=role_name, PolicyName=policy_name)["PolicyDocument"]
                inline_policies[policy_name] = json.dumps(policy_doc)
            return {
                "role_name": role_name,
                "trust_policy": json.dumps(trust_policy),
                "description": role.get("Description", ""),
                "inline_policies": inline_policies,
                "tags": {t["Key"]: t["TagValue"] for t in tags},
                "arn": role["Arn"]
            }
        except self.client.exceptions.NoSuchEntityException:
            return {}
