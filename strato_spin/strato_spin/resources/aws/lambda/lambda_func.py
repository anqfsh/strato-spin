from ....core.base_resource import BaseResource
from .packager import Packager
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

class LambdaFunction(BaseResource):
    resource_type = "lambda_function"
    platform = "aws"

    @classmethod
    def get_schema(cls):
        return {
            "required": ["function_name", "runtime", "handler", "role_arn"],
            "optional": {
                "timeout": 30,
                "memory_size": 128,
                "source_dir": None,
                "code_s3_bucket": None,
                "code_s3_key": None,
                "dependency_manager": "pip",
                "layers": [],
                "environment": {}
            },
            "tags": {
                "required": ["Environment", "Owner"],
                "optional": []
            }
        }

    def __init__(self, name, properties, tags, schema, client):
        super().__init__(name, properties, tags, schema, client)
        self.s3_client = client.meta.client("s3")
        self.packager = None
        if "source_dir" in properties:
            self.packager = Packager(self.s3_client, properties.get("code_s3_bucket"), self.name)

    def exists(self):
        try:
            self.client.get_function(FunctionName=self.properties["function_name"])
            return True
        except self.client.exceptions.ResourceNotFoundException:
            return False

    def delete_old_layers(self):
        try:
            response = self.client.get_function(FunctionName=self.properties["function_name"])
            existing_layers = response["Configuration"].get("Layers", [])
            for layer in existing_layers:
                layer_arn = layer["Arn"]
                layer_name = layer_arn.split(":")[6]
                try:
                    self.client.delete_layer_version(LayerName=layer_name, VersionNumber=1)
                except self.client.exceptions.ResourceNotFoundException:
                    pass
        except self.client.exceptions.ResourceNotFoundException:
            pass

    def create(self):
        layer_arns = []
        for layer in self.properties.get("layers", []):
            layer_name = layer["name"]
            source_dir = layer["source_dir"]
            dependency_manager = layer.get("dependency_manager", "pip")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                self.packager.package_layer(source_dir, temp_zip.name, dependency_manager)
                s3_key = self.packager.upload_to_s3(temp_zip.name, "layers")
                response = self.client.publish_layer_version(
                    LayerName=layer_name,
                    Content={"S3Bucket": self.properties["code_s3_bucket"], "S3Key": s3_key},
                    CompatibleRuntimes=layer.get("compatible_runtimes", []),
                    Description=f"Layer for {self.properties['function_name']}"
                )
                layer_arns.append(response["LayerVersionArn"])
            os.unlink(temp_zip.name)

        code_config = {}
        if "source_dir" in self.properties:
            dependency_manager = self.properties.get("dependency_manager", "pip")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                self.packager.package_lambda(self.properties["source_dir"], temp_zip.name, dependency_manager)
                s3_key = self.packager.upload_to_s3(temp_zip.name, "lambda")
                code_config = {"S3Bucket": self.properties["code_s3_bucket"], "S3Key": s3_key}
            os.unlink(temp_zip.name)
        else:
            code_config = {
                "S3Bucket": self.properties["code_s3_bucket"],
                "S3Key": self.properties["code_s3_key"]
            }

        self.client.create_function(
            FunctionName=self.properties["function_name"],
            Runtime=self.properties["runtime"],
            Role=self.properties["role_arn"],
            Handler=self.properties["handler"],
            Code=code_config,
            Timeout=self.properties.get("timeout", 30),
            MemorySize=self.properties.get("memory_size", 128),
            Environment={"Variables": self.properties.get("environment", {})},
            Layers=layer_arns,
            Tags=self.tags
        )
        self.outputs = self.get_outputs()

    def update(self, existing_properties):
        self.delete_old_layers()
        layer_arns = []
        for layer in self.properties.get("layers", []):
            layer_name = layer["name"]
            source_dir = layer["source_dir"]
            dependency_manager = layer.get("dependency_manager", "pip")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                self.packager.package_layer(source_dir, temp_zip.name, dependency_manager)
                s3_key = self.packager.upload_to_s3(temp_zip.name, "layers")
                response = self.client.publish_layer_version(
                    LayerName=layer_name,
                    Content={"S3Bucket": self.properties["code_s3_bucket"], "S3Key": s3_key},
                    CompatibleRuntimes=layer.get("compatible_runtimes", []),
                    Description=f"Layer for {self.properties['function_name']}"
                )
                layer_arns.append(response["LayerVersionArn"])
            os.unlink(temp_zip.name)

        code_config = {}
        if "source_dir" in self.properties:
            dependency_manager = self.properties.get("dependency_manager", "pip")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                self.packager.package_lambda(self.properties["source_dir"], temp_zip.name, dependency_manager)
                s3_key = self.packager.upload_to_s3(temp_zip.name, "lambda")
                code_config = {"S3Bucket": self.properties["code_s3_bucket"], "S3Key": s3_key}
            os.unlink(temp_zip.name)
        else:
            code_config = {
                "S3Bucket": self.properties["code_s3_bucket"],
                "S3Key": self.properties["code_s3_key"]
            }

        self.client.update_function_code(
            FunctionName=self.properties["function_name"],
            S3Bucket=code_config["S3Bucket"],
            S3Key=code_config["S3Key"]
        )
        self.client.update_function_configuration(
            FunctionName=self.properties["function_name"],
            Runtime=self.properties["runtime"],
            Role=self.properties["role_arn"],
            Handler=self.properties["handler"],
            Timeout=self.properties.get("timeout", 30),
            MemorySize=self.properties.get("memory_size", 128),
            Environment={"Variables": self.properties.get("environment", {})},
            Layers=layer_arns
        )
        if self.tags != existing_properties.get("tags", {}):
            self.client.tag_resource(
                Resource=f"arn:aws:lambda:{self.client.meta.region_name}:{self.client.meta.account_id}:function:{self.properties['function_name']}",
                Tags=self.tags
            )
        self.outputs = self.get_outputs()

    def get_outputs(self):
        return {
            "properties": {
                "function_name": self.properties["function_name"],
                "arn": f"arn:aws:lambda:{self.client.meta.region_name}:{self.client.meta.account_id}:function:{self.properties['function_name']}"
            }
        }

    def get_existing_properties(self):
        response = self.client.get_function(FunctionName=self.properties["function_name"])
        config = response["Configuration"]
        tags = self.client.list_tags(
            Resource=f"arn:aws:lambda:{self.client.meta.region_name}:{self.client.meta.account_id}:function:{self.properties['function_name']}"
        ).get("Tags", {})
        return {
            "runtime": config["Runtime"],
            "handler": config["Handler"],
            "timeout": config["Timeout"],
            "memory_size": config["MemorySize"],
            "environment": config["Environment"].get("Variables", {}),
            "tags": tags
        }
