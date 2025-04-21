import yaml
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class Parser:
    def __init__(self, infra_file, plugin_registry, flavour=None):
        with open(infra_file, "r") as f:
            self.infra = yaml.safe_load(f)
        self.variables = self.infra.get("variables", {})
        self.flavour = flavour or self.infra.get("flavour", "prod")
        self.variables["flavour"] = self.flavour
        self.resources = self.infra.get("resources", [])
        self.dependencies = defaultdict(list)
        self.resource_map = {r["name"]: r for r in self.resources}
        self.plugin_registry = plugin_registry
        self.extract_dependencies()

    def extract_dependencies(self):
        def find_dependencies(value, dependencies):
            if isinstance(value, str):
                matches = re.findall(r"\${resources\.([^.]+)\.[^}]+}", value)
                dependencies.extend(matches)
            elif isinstance(value, dict):
                for v in value.values():
                    find_dependencies(v, dependencies)
            elif isinstance(value, list):
                for v in value:
                    find_dependencies(v, dependencies)

        for resource in self.resources:
            dependencies = []
            find_dependencies(resource["properties"], dependencies)
            find_dependencies(resource["tags"], dependencies)
            if resource.get("type") == "lambda_function" and resource.get("platform", "aws") == "aws":
                for layer in resource["properties"].get("layers", []):
                    find_dependencies(layer, dependencies)
            for dep in set(dependencies):
                if dep in self.resource_map:
                    self.dependencies[resource["name"]].append(dep)

    def detect_circular_dependencies(self):
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.dependencies[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.resource_map:
            if node not in visited:
                if dfs(node):
                    raise ValueError(f"Circular dependency detected involving {node}")

    def topological_sort(self):
        visited = set()
        stack = []

        def dfs(node):
            visited.add(node)
            for neighbor in self.dependencies[node]:
                if neighbor not in visited:
                    dfs(neighbor)
            stack.append(node)

        for node in self.resource_map:
            if node not in visited:
                dfs(node)

        return [self.resource_map[name] for name in reversed(stack)]

    def resolve_variables(self, resource_outputs, self_outputs=None):
        def replace_match(match, resource_name):
            path = match.group(1).split(".")
            if path[0] == "variables":
                value = self.variables
                for part in path[1:]:
                    value = value.get(part, {})
                return str(value) if value else match.group(0)
            elif path[0] == "resources":
                resource = path[1]
                prop = ".".join(path[3:])
                if resource in resource_outputs:
                    value = resource_outputs[resource]
                    for part in path[2:]:
                        value = value.get(part, {})
                    return str(value) if value else match.group(0)
            elif path[0] == "self" and self_outputs:
                value = self_outputs
                for part in path[1:]:
                    value = value.get(part, {})
                return str(value) if value else match.group(0)
            return match.group(0)

        def recursive_replace(obj, resource_name):
            if isinstance(obj, str):
                return re.sub(r"\${([^}]+)}", lambda m: replace_match(m, resource_name), obj)
            elif isinstance(obj, dict):
                return {k: recursive_replace(v, resource_name) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursive_replace(item, resource_name) for item in obj]
            return obj

        for resource in self.resources:
            flavour_props = resource.get("flavours", {}).get(self.flavour, {})
            resource["properties"] = {**resource["properties"], **flavour_props}
            name_field = self._get_name_field(resource.get("platform", "aws"), resource["type"])
            if name_field and name_field in resource["properties"]:
                resource["properties"][name_field] = f"{resource['properties'][name_field]}-{self.flavour}"
            resource["properties"] = recursive_replace(resource["properties"], resource["name"])
            resource["tags"] = recursive_replace(resource["tags"], resource["name"])

    def _get_name_field(self, platform, resource_type):
        name_fields = {
            "aws": {
                "lambda_function": "function_name",
                "s3_bucket": "bucket_name",
                "sqs_queue": "queue_name",
                "dynamodb_table": "table_name",
                "kms_key": "alias",
                "iam_role": "role_name",
                "s3_upload": None,
                "eventbridge_rule": "rule_name"
            },
            "azure": {
                "function_app": "app_name"
            },
            "gcp": {
                "cloud_run": "service_name"
            }
        }
        return name_fields.get(platform, {}).get(resource_type)

