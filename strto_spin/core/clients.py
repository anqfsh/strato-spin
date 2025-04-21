import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from google.cloud import storage
import logging

logger = logging.getLogger(__name__)

class ClientFactory:
    @staticmethod
    def get_client(platform, service, credentials=None):
        if platform == "aws":
            session = credentials or boto3.Session()
            return session.client(service)
        elif platform == "azure":
            credential = credentials or DefaultAzureCredential()
            if service == "resource_management":
                subscription_id = credentials.get("subscription_id", "your-subscription-id")
                return ResourceManagementClient(credential, subscription_id)
            else:
                raise ValueError(f"Unknown Azure service: {service}")
        elif platform == "gcp":
            if service == "storage":
                return storage.Client(credentials=credentials, project=credentials.get("project_id", "your-project-id"))
            else:
                raise ValueError(f"Unknown GCP service: {service}")
        else:
            raise ValueError(f"Unsupported platform: {platform}")
