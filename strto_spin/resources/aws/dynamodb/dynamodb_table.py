from ....core.base_resource import BaseResource
import logging

logger = logging.getLogger(__name__)

class DynamoDBTable(BaseResource):
    resource_type = "dynamodb_table"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["table_name", "attributes", "key_schema"],
            "optional": {
                "billing_mode": "PAY_PER_REQUEST"
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            self.client.describe_table(TableName=self.properties["table_name"])
            return True
        except self.client.exceptions.ResourceNotFoundException:
            return False

    def create(self):
        attribute_definitions = [
            {"AttributeName": attr["name"], "AttributeType": attr["type"]}
            for attr in self.properties["attributes"]
        ]
        key_schema = [
            {"AttributeName": key["name"], "KeyType": key["type"]}
            for key in self.properties["key_schema"]
        ]
        self.client.create_table(
            TableName=self.properties["table_name"],
            AttributeDefinitions=attribute_definitions,
            KeySchema=key_schema,
            BillingMode=self.properties.get("billing_mode", "PAY_PER_REQUEST"),
            Tags=[{"Key": k, "Value": v} for k, v in self.tags.items()]
        )
        self.client.get_waiter("table_exists").wait(TableName=self.properties["table_name"])
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        if self.tags != existing_properties.get("tags", {}):
            self.client.tag_resource(
                ResourceArn=self.get_outputs()["properties"]["arn"],
                Tags=[{"Key": k, "Value": v} for k, v in self.tags.items()]
            )
        if self.properties.get("billing_mode") != existing_properties.get("billing_mode"):
            self.client.update_table(
                TableName=self.properties["table_name"],
                BillingMode=self.properties["billing_mode"]
            )
        self.outputs = self.get_outputs()

    def get_outputs(self):
        response = self.client.describe_table(TableName=self.properties["table_name"])
        return {
            "properties": {
                "table_name": self.properties["table_name"],
                "arn": response["Table"]["TableArn"]
            }
        }

    def get_existing_properties(self):
        response = self.client.describe_table(TableName=self.properties["table_name"])
        table = response["Table"]
        tags = self.client.list_tags_of_resource(ResourceArn=table["TableArn"]).get("Tags", {})
        return {
            "billing_mode": table.get("BillingModeSummary", {}).get("BillingMode", "PAY_PER_REQUEST"),
            "tags": {t["Key"]: t["Value"] for t in tags}
        }
