from ....core.base_resource import BaseResource
import logging

logger = logging.getLogger(__name__)

class FunctionApp(BaseResource):
    resource_type = "function_app"
    platform = "azure"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["app_name", "resource_group"],
            "optional": {
                "location": "eastus",
                "runtime": "python"
            },
            "tags": {
                "required": ["Environment"],
                "optional": []
            }
        }

    def exists(self):
        logger.info(f"Checking existence of Azure Function App {self.properties['app_name']}")
        return False

    def create(self):
        logger.info(f"Creating Azure Function App {self.properties['app_name']}")
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        logger.info(f"Updating Azure Function App {self.properties['app_name']}")
        self.outputs = self.get_outputs()

    def get_outputs(self):
        return {
            "properties": {
                "app_name": self.properties["app_name"],
                "arn": f"azure://function-app/{self.properties['app_name']}"
            }
        }

    def get_existing_properties(self):
        return {}
