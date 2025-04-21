from importlib import import_module
from pathlib import Path
from .base_resource import BaseResource
import logging
import sys

logger = logging.getLogger(__name__)

class PluginRegistry:
    def __init__(self, extensions_path=None):
        self.resource_types = {}
        self.schemas = {}
        self.extensions_path = extensions_path

    def register_plugins(self, plugin_path="strato_spin.resources"):
        # Register core plugins
        resources_dir = Path(__file__).parent.parent / "resources"
        for platform_dir in resources_dir.iterdir():
            if platform_dir.is_dir() and (platform_dir / "__init__.py").exists():
                platform = platform_dir.name
                self.resource_types[platform] = {}
                self.schemas[platform] = {}
                for resource_dir in platform_dir.iterdir():
                    if resource_dir.is_dir() and (resource_dir / "__init__.py").exists():
                        module_name = resource_dir.name
                        try:
                            module = import_module(f"{plugin_path}.{platform}.{module_name}.{module_name}")
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if isinstance(attr, type) and issubclass(attr, BaseResource) and attr != BaseResource:
                                    resource_type = attr.resource_type
                                    self.resource_types[platform][resource_type] = attr
                                    self.schemas[platform][resource_type] = attr.get_schema()
                                    logger.info(f"Registered core plugin: {platform}/{resource_type}")
                        except ImportError as e:
                            logger.error(f"Failed to load core plugin {platform}/{module_name}: {e}")

        # Register extension plugins
        if self.extensions_path:
            extensions_dir = Path(self.extensions_path)
            if extensions_dir.exists():
                sys.path.append(str(extensions_dir.parent))
                for ext_file in extensions_dir.glob("*.py"):
                    if ext_file.name != "__init__.py":
                        module_name = ext_file.stem
                        try:
                            module = import_module(f"extensions.{module_name}")
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if isinstance(attr, type) and issubclass(attr, BaseResource) and attr != BaseResource:
                                    resource_type = attr.resource_type
                                    platform = attr.platform
                                    if platform not in self.resource_types:
                                        self.resource_types[platform] = {}
                                        self.schemas[platform] = {}
                                    self.resource_types[platform][resource_type] = attr
                                    self.schemas[platform][resource_type] = attr.get_schema()
                                    logger.info(f"Registered extension plugin: {platform}/{resource_type}")
                        except ImportError as e:
                            logger.error(f"Failed to load extension plugin {module_name}: {e}")
                sys.path.pop()

    def get_resource_class(self, platform, resource_type):
        return self.resource_types.get(platform, {}).get(resource_type)

    def get_schema(self, platform, resource_type):
        return self.schemas.get(platform, {}).get(resource_type, {})
