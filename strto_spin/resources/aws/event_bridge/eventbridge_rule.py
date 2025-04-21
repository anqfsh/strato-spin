from ....core.base_resource import BaseResource
import json
import logging
import botocore.exceptions

logger = logging.getLogger(__name__)

class EventBridgeRule(BaseResource):
    resource_type = "eventbridge_rule"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["rule_name", "schedule_expression", "targets"],
            "optional": {
                "description": "",
                "state": "ENABLED"
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            self.client.describe_rule(Name=self.properties["rule_name"])
            return True
        except self.client.exceptions.ResourceNotFoundException:
            return False

    def create(self):
        self.client.put_rule(
            Name=self.properties["rule_name"],
            ScheduleExpression=self.properties["schedule_expression"],
            State=self.properties.get("state", "ENABLED"),
            Description=self.properties.get("description", "")
        )
        targets = self.properties["targets"]
        for target in targets:
            target["Id"] = f"{target['Arn'].split('/')[-1]}-{target.get('Id', '1')}"
        self.client.put_targets(
            Rule=self.properties["rule_name"],
            Targets=targets
        )
        self.client.tag_resource(
            ResourceARN=self._get_rule_arn(),
            Tags=[{"Key": k, "Value": v} for k, v in self.tags.items()]
        )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        rule_name = self.properties["rule_name"]
        if (
            self.properties["schedule_expression"] != existing_properties["schedule_expression"] or
            self.properties.get("state", "ENABLED") != existing_properties.get("state") or
            self.properties.get("description", "") != existing_properties.get("description")
        ):
            self.client.put_rule(
                Name=rule_name,
                ScheduleExpression=self.properties["schedule_expression"],
                State=self.properties.get("state", "ENABLED"),
                Description=self.properties.get("description", "")
            )

        existing_targets = {t["Id"]: t for t in existing_properties.get("targets", [])}
        new_targets = self.properties["targets"]
        for target in new_targets:
            target["Id"] = f"{target['Arn'].split('/')[-1]}-{target.get('Id', '1')}"
        new_target_ids = {t["Id"] for t in new_targets}

        # Remove outdated targets
        for target_id in existing_targets:
            if target_id not in new_target_ids:
                self.client.remove_targets(Rule=rule_name, Ids=[target_id])

        # Update or add new targets
        if new_targets:
            self.client.put_targets(Rule=rule_name, Targets=new_targets)

        if self.tags != existing_properties.get("tags", {}):
            existing_tags = self.client.list_tags_for_resource(ResourceARN=self._get_rule_arn()).get("Tags", [])
            if existing_tags:
                self.client.untag_resource(ResourceARN=self._get_rule_arn(), TagKeys=[t["Key"] for t in existing_tags])
            self.client.tag_resource(
                ResourceARN=self._get_rule_arn(),
                Tags=[{"Key": k, "Value": v} for k, v in self.tags.items()]
            )

        self.outputs = self.get_outputs()

    def _get_rule_arn(self):
        return f"arn:aws:events:{self.client.meta.region_name}:{self.client.meta.account_id}:rule/{self.properties['rule_name']}"

    def get_outputs(self):
        return {
            "properties": {
                "rule_name": self.properties["rule_name"],
                "arn": self._get_rule_arn()
            }
        }

    def get_existing_properties(self):
        try:
            rule = self.client.describe_rule(Name=self.properties["rule_name"])
            targets = self.client.list_targets_by_rule(Rule=self.properties["rule_name"]).get("Targets", [])
            tags = self.client.list_tags_for_resource(ResourceARN=self._get_rule_arn()).get("Tags", [])
            return {
                "rule_name": self.properties["rule_name"],
                "schedule_expression": rule["ScheduleExpression"],
                "state": rule.get("State", "ENABLED"),
                "description": rule.get("Description", ""),
                "targets": targets,
                "tags": {t["Key"]: t["Value"] for t in tags},
                "arn": rule["Arn"]
            }
        except self.client.exceptions.ResourceNotFoundException:
            return {}
