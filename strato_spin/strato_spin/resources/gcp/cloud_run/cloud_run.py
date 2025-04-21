from ....core.base_resource import BaseResource
import logging

logger = logging.getLogger(__name__)

class CloudRun(BaseResource):
    resource_type = "cloud_run"
    platform = "gcp"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["service_name", "project_id"],
            "optional": {
                "region": "us-central1",
                "image": None
            },
            "tags": {
                "required": ["Environment"],
                "optional": []
            }
        }

    def exists(self):
        logger.info(f"Checking existence of GCP Cloud Run {self.properties['service_name']}")
        return False

    def create(self):
        logger.info(f"Creating GCP Cloud Run {self.properties['service_name']}")
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        logger.info(f"Updating GCP Cloud Run {self.properties['service_name']}")
        self.outputs = self.get_outputs()

    def get_outputs(self):
        return {
            "properties": {
                "service_name": self.properties["service_name"],
                "url": f"https://{self.properties['service_name']}.run.app"
            }
        }

    def get_existing_properties(self):
        return {}
