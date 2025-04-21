from .assume_role import chain_assume_role
from .parser import Parser
from .plugin_registry import PluginRegistry
from .clients import ClientFactory
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class Deployer:
    def __init__(self, infra_file, flavour=None, extensions_path=None):
        self.plugin_registry = PluginRegistry(extensions_path)
        self.plugin_registry.register_plugins()
        self.parser = Parser(infra_file, self.plugin_registry, flavour)
        self.parser.detect_circular_dependencies()
        self.resource_outputs = {}
        self.resources = []
        self.credentials = {}

    def initialize_resources(self):
        sorted_resources = self.parser.topological_sort()
        for res in sorted_resources:
            platform = res.get("platform", "aws")
            res_type = res["type"]
            resource_class = self.plugin_registry.get_resource_class(platform, res_type)
            if not resource_class:
                raise ValueError(f"Unknown resource type: {platform}/{res_type}")
            client = self.get_client(platform, res_type)
            schema = self.parser.get_resource_schema(platform, res_type)
            self.parser.resolve_variables(self.resource_outputs)
            self.resources.append(
                resource_class(res["name"], res["properties"], res["tags"], schema, client)
            )

    def get_client(self, platform, service):
        if platform == "aws":
            role_chain = self.parser.infra.get("assume_roles", [])
            region = self.parser.infra.get("variables", {}).get("region", "ap-southeast-2")
            session = chain_assume_role(role_chain, region=region)
            return ClientFactory.get_client(platform, service, session)
        elif platform == "azure":
            credentials = self.parser.infra.get("azure_credentials", {})
            return ClientFactory.get_client(platform, service, credentials)
        elif platform == "gcp":
            credentials = self.parser.infra.get("gcp_credentials", {})
            return ClientFactory.get_client(platform, service, credentials)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def deploy_resource(self, resource):
        try:
            existing_props = resource.get_existing_properties()
            if resource.exists() and existing_props == {
                **resource.properties,
                "tags": resource.tags
            }:
                logger.info(f"Resource {resource.name} is up-to-date")
            elif resource.exists():
                resource.update(existing_props)
                logger.info(f"Updated resource {resource.name}")
            else:
                resource.create()
                logger.info(f"Created resource {resource.name}")
            self.resource_outputs[resource.name] = resource.get_outputs()
            self.parser.resolve_variables(self.resource_outputs)
            return True
        except Exception as e:
            logger.error(f"Failed to deploy resource {resource.name}: {e}")
            return False

    def deploy(self):
        self.initialize_resources()
        dependency_groups = []
        current_group = []
        processed = set()

        for resource in self.resources:
            resource_deps = set(self.parser.dependencies[resource.name])
            if not resource_deps.issubset(processed):
                if current_group:
                    dependency_groups.append(current_group)
                current_group = [resource]
            else:
                current_group.append(resource)
            processed.add(resource.name)
        if current_group:
            dependency_groups.append(current_group)

        max_workers = min(4, len(self.resources))
        for group in dependency_groups:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_resource = {
                    executor.submit(self.deploy_resource, resource): resource
                    for resource in group
                }
                for future in as_completed(future_to_resource):
                    resource = future_to_resource[future]
                    if not future.result():
                        logger.error(f"Deployment failed for {resource.name}, aborting")
                        return
        logger.info("Deployment completed successfully")
