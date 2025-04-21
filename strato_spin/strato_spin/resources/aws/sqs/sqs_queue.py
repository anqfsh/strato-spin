from ....core.base_resource import BaseResource
import logging

logger = logging.getLogger(__name__)

class SQSQueue(BaseResource):
    resource_type = "sqs_queue"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["queue_name"],
            "optional": {
                "delay_seconds": 0,
                "retention_period": 345600,
                "visibility_timeout": 30
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def exists(self):
        try:
            self.client.get_queue_attributes(QueueUrl=self._get_queue_url())
            return True
        except self.client.exceptions.QueueDoesNotExist:
            return False

    def create(self):
        attributes = {
            "DelaySeconds": str(self.properties.get("delay_seconds", 0)),
            "MessageRetentionPeriod": str(self.properties.get("retention_period", 345600)),
            "VisibilityTimeout": str(self.properties.get("visibility_timeout", 30))
        }
        response = self.client.create_queue(
            QueueName=self.properties["queue_name"],
            Attributes=attributes,
            tags=self.tags
        )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        queue_url = self._get_queue_url()
        attributes = {}
        if self.properties.get("delay_seconds", 0) != existing_properties.get("delay_seconds"):
            attributes["DelaySeconds"] = str(self.properties["delay_seconds"])
        if self.properties.get("retention_period", 345600) != existing_properties.get("retention_period"):
            attributes["MessageRetentionPeriod"] = str(self.properties["retention_period"])
        if self.properties.get("visibility_timeout", 30) != existing_properties.get("visibility_timeout"):
            attributes["VisibilityTimeout"] = str(self.properties["visibility_timeout"])
        if attributes:
            self.client.set_queue_attributes(QueueUrl=queue_url, Attributes=attributes)
        if self.tags != existing_properties.get("tags", {}):
            self.client.tag_queue(QueueUrl=queue_url, Tags=self.tags)
        self.outputs = self.get_outputs()

    def _get_queue_url(self):
        response = self.client.get_queue_url(QueueName=self.properties["queue_name"])
        return response["QueueUrl"]

    def get_outputs(self):
        return {
            "properties": {
                "queue_name": self.properties["queue_name"],
                "url": self._get_queue_url(),
                "arn": f"arn:aws:sqs:{self.client.meta.region_name}:{self.client.meta.account_id}:{self.properties['queue_name']}"
            }
        }

    def get_existing_properties(self):
        queue_url = self._get_queue_url()
        attributes = self.client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])["Attributes"]
        tags = self.client.list_queue_tags(QueueUrl=queue_url).get("Tags", {})
        return {
            "delay_seconds": int(attributes.get("DelaySeconds", 0)),
            "retention_period": int(attributes.get("MessageRetentionPeriod", 345600)),
            "visibility_timeout": int(attributes.get("VisibilityTimeout", 30)),
            "tags": tags
        }
